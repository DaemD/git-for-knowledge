import asyncio
import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from app.models import (
    ClaimView,
    EntityView,
    EvidenceView,
    ProvenanceView,
    RecallResult,
    RememberResult,
)
from app.memory_writes import MemoryWrite, MemoryWriteStore
from app.nams import NamsStore
from app.utils import stable_id


KNOWLEDGE_ID_PATTERN = re.compile(r"^kg_[A-Za-z0-9_-]{8,128}$")
MAX_PROVENANCE_VALUE_LENGTH = 256
WEB_UNATTRIBUTED_CLIENT_ID = "web-unattributed"


def validate_knowledge_id(knowledge_id: str) -> str:
    if not KNOWLEDGE_ID_PATTERN.fullmatch(knowledge_id):
        raise ValueError(
            "Invalid knowledge ID. Expected kg_ followed by 8-128 safe characters."
        )
    return knowledge_id


class KnowledgeService:
    def __init__(
        self,
        store: NamsStore,
        write_store: MemoryWriteStore,
        knowledge_id: str,
    ) -> None:
        self._store = store
        self._write_store = write_store
        self._knowledge_id = validate_knowledge_id(knowledge_id)

    async def remember(
        self,
        knowledge_id: str,
        text: str,
        client_id: str | None,
        idempotency_key: str,
    ) -> RememberResult:
        self._validate_scope(knowledge_id)
        text = text.strip()
        if not text:
            raise ValueError("Memory text cannot be empty")

        client_id = self._client_id_or_default(client_id)
        idempotency_key = self._provenance_value(
            "idempotency_key",
            idempotency_key,
        )

        accepted_at = self._utc_now()
        write_result = self._write_store.begin_write(
            idempotency_key=idempotency_key,
            workspace_id=self._knowledge_id,
            client_id=client_id,
            content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            accepted_at=accepted_at,
        )
        if not write_result.should_submit:
            if write_result.write.status == "completed":
                return RememberResult(
                    memory_id=write_result.write.nams_message_id,
                    status="already_exists",
                )
            return RememberResult(
                memory_id=write_result.write.nams_message_id,
                status="processing",
            )

        try:
            memory_id, _ = await self._store.add_memory(self._knowledge_id, text)
        except Exception:
            self._write_store.mark_failed(idempotency_key)
            raise

        self._write_store.mark_completed(
            idempotency_key,
            memory_id,
            self._utc_now(),
        )
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

        message_ids = {
            str(message_id)
            for history in history_batches
            for mention in history
            for message_id in [
                mention.get("messageId")
                or mention.get("message_id")
                or mention.get("id")
            ]
            if message_id
        }
        writes_by_message_id = self._write_store.get_by_message_ids(
            self._knowledge_id,
            message_ids,
        )

        entities = [self._entity_to_view(entity) for entity in nams_entities]
        sources_by_id: dict[str, EvidenceView] = {}
        for history in history_batches:
            for source in self._history_to_evidence(history, writes_by_message_id):
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
    def _provenance_value(name: str, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError(f"{name} cannot be empty")
        if len(value) > MAX_PROVENANCE_VALUE_LENGTH:
            raise ValueError(
                f"{name} cannot exceed {MAX_PROVENANCE_VALUE_LENGTH} characters"
            )
        return value

    @classmethod
    def _client_id_or_default(cls, client_id: str | None) -> str:
        if client_id is None or not client_id.strip():
            return WEB_UNATTRIBUTED_CLIENT_ID
        return cls._provenance_value("client_id", client_id)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

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

    @classmethod
    def _history_to_evidence(
        cls,
        history: list[dict[str, Any]],
        writes_by_message_id: dict[str, MemoryWrite],
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
                    provenance=cls._write_to_provenance(
                        writes_by_message_id.get(str(evidence_id))
                    ),
                )
            )
        return evidence

    @staticmethod
    def _write_to_provenance(
        write: MemoryWrite | None,
    ) -> ProvenanceView | None:
        if write is None:
            return None
        return ProvenanceView(
            client_id=write.client_id or WEB_UNATTRIBUTED_CLIENT_ID,
            accepted_at=write.accepted_at,
        )
