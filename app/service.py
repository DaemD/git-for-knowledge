import asyncio
import re
from typing import Any

from app.models import (
    ClaimView,
    EntityResult,
    EntityView,
    EvidenceView,
    NeighborhoodResult,
    PushMemoryResult,
    SearchHit,
    SearchResult,
)
from app.nams import NamsStore
from app.utils import stable_id


KNOWLEDGE_ID_PATTERN = re.compile(r"^kg_[A-Za-z0-9_-]{8,128}$")


def validate_knowledge_id(knowledge_id: str) -> str:
    if not KNOWLEDGE_ID_PATTERN.fullmatch(knowledge_id):
        raise ValueError(
            "Invalid knowledge ID. Expected kg_ followed by 8-128 safe characters."
        )
    return knowledge_id


class KnowledgeService:
    def __init__(self, store: NamsStore, knowledge_id: str) -> None:
        self._store = store
        self._knowledge_id = validate_knowledge_id(knowledge_id)

    async def create_knowledge_base(self) -> str:
        await self._store.ensure_conversation(self._knowledge_id)
        return self._knowledge_id

    async def push_memory(
        self,
        knowledge_id: str,
        text: str,
        source: str,
        idempotency_key: str | None = None,
    ) -> PushMemoryResult:
        self._validate_scope(knowledge_id)
        # NAMS currently deduplicates extracted entities but does not expose
        # durable message idempotency or arbitrary source metadata.
        del source, idempotency_key
        text = text.strip()
        if not text:
            raise ValueError("Memory text cannot be empty")

        memory_id, conversation_id = await self._store.add_memory(
            self._knowledge_id,
            text,
        )
        return PushMemoryResult(
            knowledge_id=self._knowledge_id,
            memory_id=memory_id,
            conversation_id=conversation_id,
        )

    async def search(
        self,
        knowledge_id: str,
        query: str,
        limit: int = 5,
    ) -> SearchResult:
        self._validate_scope(knowledge_id)
        query = query.strip()
        if not query:
            raise ValueError("Search query cannot be empty")
        limit = max(1, min(limit, 20))

        entities, context = await asyncio.gather(
            self._store.search_entities(query, limit),
            self._store.get_context(self._knowledge_id, query),
        )
        relationship_batches = await asyncio.gather(
            *(
                self._store.get_relationships(str(entity.id))
                for entity in entities
            )
        )
        history_batches = await asyncio.gather(
            *(
                self._store.get_entity_history(str(entity.id))
                for entity in entities
            )
        )

        hits: list[SearchHit] = []
        for rank, (entity, relationship_rows, history) in enumerate(
            zip(entities, relationship_batches, history_batches, strict=True)
        ):
            evidence = self._history_to_evidence(history)
            hits.append(
                SearchHit(
                    entity=self._entity_to_view(entity),
                    score=1.0 / (rank + 1),
                    claims=[
                        self._relationship_to_claim(row, evidence)
                        for row in relationship_rows
                    ],
                )
            )

        return SearchResult(
            query=query,
            hits=hits,
            context=context,
            insufficient_evidence=not hits,
        )

    async def get_entity(
        self,
        knowledge_id: str,
        entity_id: str,
    ) -> EntityResult:
        self._validate_scope(knowledge_id)
        entity = await self._store.get_entity(entity_id)
        if entity is None:
            raise ValueError("Entity not found in this NAMS workspace")
        relationships, history = await asyncio.gather(
            self._store.get_relationships(entity_id),
            self._store.get_entity_history(entity_id),
        )
        evidence = self._history_to_evidence(history)
        return EntityResult(
            entity=self._entity_to_view(entity),
            claims=[
                self._relationship_to_claim(row, evidence)
                for row in relationships
            ],
        )

    async def get_neighborhood(
        self,
        knowledge_id: str,
        entity_id: str,
        depth: int = 1,
        limit: int = 50,
    ) -> NeighborhoodResult:
        self._validate_scope(knowledge_id)
        depth = max(1, min(depth, 2))
        limit = max(1, min(limit, 100))
        entity_rows, relationship_rows, truncated = (
            await self._store.get_neighborhood(entity_id, depth, limit)
        )
        if not entity_rows:
            raise ValueError("Entity not found in this NAMS workspace")

        entities = [self._entity_to_view(row) for row in entity_rows]
        return NeighborhoodResult(
            center=entities[0],
            entities=entities,
            claims=[
                self._relationship_to_claim(row, [])
                for row in relationship_rows
            ],
            truncated=truncated,
        )

    def _validate_scope(self, knowledge_id: str) -> None:
        validate_knowledge_id(knowledge_id)
        if knowledge_id != self._knowledge_id:
            raise ValueError(
                "This MCP service is bound to a different NAMS workspace. "
                "Use /mcp/bootstrap to retrieve its knowledge ID."
            )

    @staticmethod
    def _entity_to_view(entity: Any) -> EntityView:
        if isinstance(entity, dict):
            data = entity
        else:
            data = {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "description": entity.description,
                "aliases": entity.aliases,
            }
        return EntityView(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or "Unnamed entity"),
            kind=str(data.get("type") or "CUSTOM"),
            summary=str(data.get("description") or ""),
            aliases=[str(alias) for alias in (data.get("aliases") or [])],
        )

    @classmethod
    def _relationship_to_claim(
        cls,
        row: dict[str, Any],
        evidence: list[EvidenceView],
    ) -> ClaimView:
        source = cls._entity_to_view(dict(row.get("source") or {}))
        target = cls._entity_to_view(dict(row.get("target") or {}))
        relationship = dict(row.get("relationship") or {})
        predicate = str(row.get("predicate") or "RELATED_TO")
        confidence = relationship.get("confidence", 1.0)
        return ClaimView(
            id=stable_id("nams-rel", source.id, predicate, target.id),
            subject=source,
            predicate=predicate,
            object=target,
            polarity="positive",
            status=str(relationship.get("status") or "active"),
            confidence=float(confidence),
            valid_from=relationship.get("valid_from"),
            valid_to=relationship.get("valid_to"),
            evidence=evidence,
        )

    @staticmethod
    def _history_to_evidence(
        history: list[dict[str, Any]],
    ) -> list[EvidenceView]:
        evidence: list[EvidenceView] = []
        for index, mention in enumerate(history):
            text = (
                mention.get("content")
                or mention.get("text")
                or mention.get("quote")
                or mention.get("messageContent")
                or mention.get("message_content")
            )
            if not text:
                continue
            evidence_id = (
                mention.get("messageId")
                or mention.get("message_id")
                or mention.get("id")
                or stable_id("nams-evidence", str(index), str(text))
            )
            ingested_at = (
                mention.get("createdAt")
                or mention.get("created_at")
                or mention.get("timestamp")
                or ""
            )
            evidence.append(
                EvidenceView(
                    id=str(evidence_id),
                    source="nams",
                    text=str(text),
                    ingested_at=str(ingested_at),
                )
            )
        return evidence
