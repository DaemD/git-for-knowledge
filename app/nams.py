"""Workspace-aware Neo4j Agent Memory Service (NAMS) adapter.

MVP: one shared NAMS workspace for the whole deployment. Product graphs map to
NAMS conversations inside that workspace.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from neo4j_agent_memory import MemoryClient, MemorySettings, NamsConfig

from app.config import Settings


class NamsStore:
    """Single shared-workspace MemoryClient."""

    def __init__(self, settings: Settings) -> None:
        self._workspace_id = settings.memory_workspace_id
        nams = NamsConfig(
            endpoint=settings.memory_endpoint,
            api_key=settings.memory_api_key,
            workspace_id=self._workspace_id,
        )
        self._client = MemoryClient(MemorySettings(backend="nams", nams=nams))

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    async def connect(self) -> None:
        await self._client.connect()

    async def close(self) -> None:
        await self._client.close()

    async def create_conversation(
        self,
        name: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        session_id = f"graph-{uuid4().hex}"
        payload = {
            "purpose": "grphly",
            "graph_name": name,
            **(metadata or {}),
        }
        conversation = await self._client.short_term.create_conversation(
            session_id,
            metadata=payload,
        )
        return str(conversation.id or conversation.session_id or session_id)

    async def add_memory(
        self,
        conversation_id: str,
        text: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store memory text. NAMS drops message metadata, so we stamp it in content."""
        from app.memory_meta import stamp_memory_text

        content = text
        if metadata:
            content = stamp_memory_text(text, metadata)
        message = await self._client.short_term.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )
        return str(message.id)

    async def clear_conversation(self, conversation_id: str) -> None:
        """Delete a NAMS conversation (best-effort KB cleanup)."""
        await self._client.short_term.clear_session(conversation_id=conversation_id)

    async def get_context(self, conversation_id: str, query: str) -> str:
        return await self._client.short_term.get_context(
            query,
            session_id=conversation_id,
        )

    async def list_messages(
        self,
        conversation_id: str,
        *,
        limit: int = 100,
    ) -> list[Any]:
        conversation = await self._client.short_term.get_conversation(
            conversation_id=conversation_id,
        )
        messages = list(getattr(conversation, "messages", None) or [])
        if limit > 0:
            return messages[:limit]
        return messages

    async def search_entities(self, query: str, limit: int) -> list[Any]:
        return await self._client.long_term.search_entities(query, limit=limit)

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

    async def messages_mentioning_entity(
        self,
        conversation_id: str,
        entity_id: str,
        *,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        """Return Message properties in a conversation that MENTIONS an entity."""
        limit = max(1, min(limit, 50))
        rows = await self._client.query.cypher(
            """
            MATCH (c:Conversation)-[:HAS_MESSAGE]->(m:Message)-[:MENTIONS]->(e:Entity)
            WHERE (toString(c.id) = $conversation_id
                   OR toString(c.session_id) = $conversation_id)
              AND toString(e.id) = $entity_id
            RETURN properties(m) AS message
            ORDER BY coalesce(m.created_at, m.timestamp, m.ingested_at) DESC
            LIMIT $limit
            """,
            {
                "conversation_id": conversation_id,
                "entity_id": entity_id,
                "limit": limit,
            },
        )
        messages: list[dict[str, Any]] = []
        for row in rows:
            payload = row.get("message") if isinstance(row, dict) else None
            if isinstance(payload, dict):
                messages.append(payload)
        return messages

    async def entities_mentioned_by_messages(
        self,
        message_ids: list[str],
        *,
        limit: int = 300,
    ) -> list[dict[str, Any]]:
        """Return Entity properties mentioned by any of the given Message ids."""
        if not message_ids:
            return []
        limit = max(1, min(limit, 500))
        rows = await self._client.query.cypher(
            """
            MATCH (m:Message)-[:MENTIONS]->(e:Entity)
            WHERE toString(m.id) IN $message_ids
            WITH DISTINCT e
            LIMIT $limit
            RETURN properties(e) AS entity
            """,
            {"message_ids": message_ids, "limit": limit},
        )
        entities: list[dict[str, Any]] = []
        for row in rows:
            payload = row.get("entity") if isinstance(row, dict) else None
            if isinstance(payload, dict):
                entities.append(payload)
        return entities

    async def entities_for_conversation(
        self,
        conversation_id: str,
        *,
        limit: int = 300,
    ) -> list[dict[str, Any]]:
        """Return entities mentioned in a Conversation's messages."""
        limit = max(1, min(limit, 500))
        rows = await self._client.query.cypher(
            """
            MATCH (c:Conversation)-[:HAS_MESSAGE]->(m:Message)-[:MENTIONS]->(e:Entity)
            WHERE toString(c.id) = $conversation_id
               OR toString(c.session_id) = $conversation_id
            WITH DISTINCT e
            LIMIT $limit
            RETURN properties(e) AS entity
            """,
            {"conversation_id": conversation_id, "limit": limit},
        )
        entities: list[dict[str, Any]] = []
        for row in rows:
            payload = row.get("entity") if isinstance(row, dict) else None
            if isinstance(payload, dict):
                entities.append(payload)
        return entities

    async def relationships_among_entities(
        self,
        entity_ids: list[str],
        *,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Return Entity–Entity relationships where both ends are in entity_ids."""
        if not entity_ids:
            return []
        limit = max(1, min(limit, 1000))
        rows = await self._client.query.cypher(
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
                   ) AS predicate
            LIMIT $limit
            """,
            {"entity_ids": entity_ids, "limit": limit},
        )
        return [dict(row) for row in rows]
