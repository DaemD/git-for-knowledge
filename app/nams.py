import asyncio
from typing import Any
from uuid import uuid4

from neo4j_agent_memory import MemoryClient, MemorySettings, NamsConfig

from app.config import Settings


class NamsStore:
    """Thin adapter around the hosted Neo4j Agent Memory Service."""

    def __init__(self, settings: Settings) -> None:
        nams = NamsConfig(
            endpoint=settings.memory_endpoint,
            api_key=settings.memory_api_key,
            workspace_id=settings.memory_workspace_id,
        )
        self._client = MemoryClient(MemorySettings(backend="nams", nams=nams))
        self._conversation_ids: dict[str, str] = {}
        self._conversation_lock = asyncio.Lock()

    async def connect(self) -> None:
        await self._client.connect()

    async def close(self) -> None:
        await self._client.close()

    async def ensure_conversation(self, knowledge_id: str) -> str:
        cached = self._conversation_ids.get(knowledge_id)
        if cached:
            return cached

        async with self._conversation_lock:
            cached = self._conversation_ids.get(knowledge_id)
            if cached:
                return cached

            conversations = await self._client.short_term.list_conversations(
                user_identifier=knowledge_id,
                limit=100,
            )
            if conversations:
                conversation_id = str(conversations[0].id)
            else:
                conversation = await self._client.short_term.create_conversation(
                    f"shared-knowledge-{uuid4().hex}",
                    user_identifier=knowledge_id,
                    metadata={"purpose": "shared-knowledge-mcp"},
                )
                conversation_id = str(conversation.id)

            self._conversation_ids[knowledge_id] = conversation_id
            return conversation_id

    async def add_memory(self, knowledge_id: str, text: str) -> tuple[str, str]:
        conversation_id = await self.ensure_conversation(knowledge_id)
        message = await self._client.short_term.add_message(
            conversation_id,
            "user",
            text,
            user_identifier=knowledge_id,
        )
        return str(message.id), conversation_id

    async def search_entities(self, query: str, limit: int) -> list[Any]:
        return await self._client.long_term.search_entities(query, limit=limit)

    async def get_context(self, knowledge_id: str, query: str) -> str:
        conversation_id = await self.ensure_conversation(knowledge_id)
        return await self._client.short_term.get_context(
            query,
            session_id=conversation_id,
        )

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        rows = await self._client.query.cypher(
            """
            MATCH (entity:Entity)
            WHERE toString(entity.id) = $entity_id
            RETURN properties(entity) AS entity
            LIMIT 1
            """,
            {"entity_id": entity_id},
        )
        if not rows:
            return None
        return dict(rows[0].get("entity") or {})

    async def get_relationships(self, entity_id: str) -> list[dict[str, Any]]:
        rows = await self._client.query.cypher(
            """
            MATCH (source:Entity)-[relationship]->(target:Entity)
            WHERE toString(source.id) = $entity_id
               OR toString(target.id) = $entity_id
            RETURN properties(source) AS source,
                   properties(target) AS target,
                   coalesce(
                       relationship.relation_type,
                       relationship.relationType,
                       type(relationship)
                   ) AS predicate,
                   properties(relationship) AS relationship
            """,
            {"entity_id": entity_id},
        )
        return [dict(row) for row in rows]

    async def get_entity_history(self, entity_id: str) -> list[dict[str, Any]]:
        return await self._client.long_term.get_entity_history(entity_id)

    async def get_neighborhood(
        self,
        entity_id: str,
        depth: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
        center = await self.get_entity(entity_id)
        if center is None:
            return [], [], False

        fetch_limit = max(1, limit)
        entity_rows = await self._client.query.cypher(
            f"""
            MATCH (center:Entity)
            WHERE toString(center.id) = $entity_id
            MATCH path = (center)-[*1..{depth}]-(neighbor:Entity)
            RETURN DISTINCT properties(neighbor) AS entity
            LIMIT $fetch_limit
            """,
            {
                "entity_id": entity_id,
                "fetch_limit": fetch_limit,
            },
        )
        neighbors = [dict(row.get("entity") or {}) for row in entity_rows]
        truncated = len(neighbors) >= limit
        neighbors = neighbors[: max(0, limit - 1)]
        entities = [center, *neighbors]
        entity_ids = [
            str(entity.get("id"))
            for entity in entities
            if entity.get("id") is not None
        ]

        relationship_rows = await self._client.query.cypher(
            """
            MATCH (source:Entity)-[relationship]->(target:Entity)
            WHERE toString(source.id) IN $entity_ids
              AND toString(target.id) IN $entity_ids
            RETURN properties(source) AS source,
                   properties(target) AS target,
                   coalesce(
                       relationship.relation_type,
                       relationship.relationType,
                       type(relationship)
                   ) AS predicate,
                   properties(relationship) AS relationship
            LIMIT $relationship_limit
            """,
            {
                "entity_ids": entity_ids,
                "relationship_limit": limit * 2,
            },
        )
        return entities, [dict(row) for row in relationship_rows], truncated
