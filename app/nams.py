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
            "purpose": "shared-knowledge-graph",
            "graph_name": name,
            **(metadata or {}),
        }
        conversation = await self._client.short_term.create_conversation(
            session_id,
            metadata=payload,
        )
        return str(conversation.id or conversation.session_id or session_id)

    async def add_memory(self, conversation_id: str, text: str) -> str:
        message = await self._client.short_term.add_message(
            conversation_id=conversation_id,
            role="user",
            content=text,
        )
        return str(message.id)

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
