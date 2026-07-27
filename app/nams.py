import asyncio
from typing import Any
from uuid import uuid4

from neo4j_agent_memory import MemoryClient, MemorySettings, NamsConfig

from app.config import Settings


class NamsStore:
    """Thin adapter around the hosted Neo4j Agent Memory Service."""

    _RECENT_MESSAGE_LIMIT = 100

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

    async def find_memory_by_idempotency_key(
        self,
        knowledge_id: str,
        idempotency_key: str,
    ) -> str | None:
        """Return a recent message ID with this key in the scoped conversation."""
        conversation_id = await self.ensure_conversation(knowledge_id)
        conversation = await self._client.short_term.get_conversation(conversation_id)
        recent_messages = conversation.messages[-self._RECENT_MESSAGE_LIMIT :]
        for message in reversed(recent_messages):
            metadata = dict(getattr(message, "metadata", None) or {})
            if metadata.get("idempotency_key") == idempotency_key:
                return str(message.id)
        return None

    async def add_memory(
        self,
        knowledge_id: str,
        text: str,
        metadata: dict[str, str],
    ) -> tuple[str, str]:
        conversation_id = await self.ensure_conversation(knowledge_id)
        message = await self._client.short_term.add_message(
            conversation_id,
            "user",
            text,
            metadata=metadata,
            user_identifier=knowledge_id,
        )
        return str(message.id), conversation_id

    async def get_message_metadata(
        self,
        knowledge_id: str,
        message_ids: set[str],
    ) -> dict[str, dict[str, Any]]:
        """Read metadata for evidence messages from the scoped conversation."""
        if not message_ids:
            return {}

        conversation_id = await self.ensure_conversation(knowledge_id)
        conversation = await self._client.short_term.get_conversation(
            conversation_id,
        )
        return {
            str(message.id): dict(getattr(message, "metadata", None) or {})
            for message in conversation.messages
            if str(message.id) in message_ids
        }

    async def search_entities(self, query: str, limit: int) -> list[Any]:
        return await self._client.long_term.search_entities(query, limit=limit)

    async def get_context(self, knowledge_id: str, query: str) -> str:
        conversation_id = await self.ensure_conversation(knowledge_id)
        return await self._client.short_term.get_context(
            query,
            session_id=conversation_id,
        )

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
