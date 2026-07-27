import asyncio
import re
from typing import Any

from app.models import (
    ClaimView,
    EntityView,
    EvidenceView,
    RecallResult,
    RememberResult,
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

    async def remember(self, knowledge_id: str, text: str) -> RememberResult:
        self._validate_scope(knowledge_id)
        text = text.strip()
        if not text:
            raise ValueError("Memory text cannot be empty")

        memory_id, _ = await self._store.add_memory(self._knowledge_id, text)
        return RememberResult(memory_id=memory_id)

    async def recall(
        self,
        knowledge_id: str,
        question: str,
        limit: int = 5,
    ) -> RecallResult:
        self._validate_scope(knowledge_id)
        question = question.strip()
        if not question:
            raise ValueError("Recall question cannot be empty")
        limit = max(1, min(limit, 20))

        nams_entities, context = await asyncio.gather(
            self._store.search_entities(question, limit),
            self._store.get_context(self._knowledge_id, question),
        )
        relationship_batches = await asyncio.gather(
            *(
                self._store.get_relationships(str(entity.id))
                for entity in nams_entities
            )
        )
        history_batches = await asyncio.gather(
            *(
                self._store.get_entity_history(str(entity.id))
                for entity in nams_entities
            )
        )

        entities = [self._entity_to_view(entity) for entity in nams_entities]
        sources_by_id: dict[str, EvidenceView] = {}
        for history in history_batches:
            for source in self._history_to_evidence(history):
                sources_by_id.setdefault(source.id, source)

        relationships_by_id: dict[str, ClaimView] = {}
        sources = list(sources_by_id.values())
        for rows in relationship_batches:
            for row in rows:
                relationship = self._relationship_to_claim(row, sources)
                relationships_by_id.setdefault(relationship.id, relationship)

        return RecallResult(
            question=question,
            context=context,
            entities=entities,
            relationships=list(relationships_by_id.values()),
            sources=sources,
            found=bool(entities or context),
        )

    def _validate_scope(self, knowledge_id: str) -> None:
        validate_knowledge_id(knowledge_id)
        if knowledge_id != self._knowledge_id:
            raise ValueError(
                "This MCP service is bound to a different NAMS workspace."
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
