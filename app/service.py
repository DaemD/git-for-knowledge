"""Product service: auth user + kb_id logical knowledge bases."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from app.db import ControlStore, GraphRecord, MemoryWrite, UserRecord, hash_content
from app.models import (
    ClaimView,
    CreateKnowledgeBaseResult,
    EntityView,
    EvidenceView,
    KB_ID_PATTERN,
    KnowledgeBaseListResult,
    KnowledgeBaseView,
    ProvenanceView,
    RecallResult,
    RememberResult,
)
from app.nams import NamsStore
from app.utils import stable_id


MAX_PROVENANCE_VALUE_LENGTH = 256
WEB_UNATTRIBUTED_CLIENT_ID = "web-unattributed"
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class KnowledgeService:
    def __init__(self, store: NamsStore, control: ControlStore) -> None:
        self._store = store
        self._control = control

    async def ensure_user(
        self,
        subject: str,
        claims: dict[str, Any] | None = None,
    ) -> UserRecord:
        claims = claims or {}
        email = _as_optional_str(claims.get("email"))
        display_name = _as_optional_str(
            claims.get("name") or claims.get("nickname")
        )
        return await self._control.upsert_user(
            subject,
            email=email,
            display_name=display_name,
        )

    def username_for(self, user: UserRecord) -> str:
        """Stable public username derived from profile, never client-supplied."""
        for candidate in (
            user.display_name,
            (user.email or "").split("@", 1)[0] if user.email else None,
            user.id,
        ):
            if not candidate:
                continue
            cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip("-._")
            if cleaned and USERNAME_PATTERN.fullmatch(cleaned):
                return cleaned[:64]
        return re.sub(r"[^A-Za-z0-9_-]+", "-", user.id)[:64] or "user"

    async def list_knowledge_bases(self, user_id: str) -> KnowledgeBaseListResult:
        user = await self._require_user(user_id)
        graphs = await self._control.list_graphs(user_id)
        return KnowledgeBaseListResult(
            username=self.username_for(user),
            knowledge_bases=[_kb_view(graph) for graph in graphs],
        )

    async def create_knowledge_base(
        self,
        user_id: str,
        kb_id: str,
        name: str | None = None,
    ) -> CreateKnowledgeBaseResult:
        user = await self._require_user(user_id)
        kb_id = validate_kb_id(kb_id)
        label = (name or kb_id).strip()
        if not label:
            raise ValueError("Knowledge base name cannot be empty")
        if len(label) > 120:
            raise ValueError("Knowledge base name must be 120 characters or fewer")

        conversation_id = await self._store.create_conversation(
            label,
            metadata={
                "purpose": "shared-knowledge-graph",
                "kb_id": kb_id,
                "user_id": user_id,
                "username": self.username_for(user),
            },
        )
        graph = await self._control.create_graph(
            user_id,
            kb_id,
            label,
            conversation_id,
        )
        return CreateKnowledgeBaseResult(
            username=self.username_for(user),
            knowledge_base=_kb_view(graph),
        )

    async def remember(
        self,
        user_id: str,
        kb_id: str,
        text: str,
        *,
        idempotency_key: str,
        client_id: str | None = None,
    ) -> RememberResult:
        text = text.strip()
        if not text:
            raise ValueError("Memory text cannot be empty")

        user = await self._require_user(user_id)
        username = self.username_for(user)
        graph = await self._require_owned_kb(user_id, kb_id)
        client_id = self._client_id_or_default(client_id)
        idempotency_key = self._provenance_value(
            "idempotency_key",
            idempotency_key,
        )
        accepted_at = self._utc_now()
        write_result = await self._control.begin_write(
            idempotency_key=idempotency_key,
            user_id=user_id,
            graph_id=graph.id,
            client_id=client_id,
            content_hash=hash_content(text),
            accepted_at=accepted_at,
        )
        if not write_result.should_submit:
            if write_result.write.status == "completed":
                return RememberResult(
                    memory_id=write_result.write.nams_message_id,
                    status="already_exists",
                    username=username,
                    kb_id=graph.kb_id,
                )
            return RememberResult(
                memory_id=write_result.write.nams_message_id,
                status="processing",
                username=username,
                kb_id=graph.kb_id,
            )

        try:
            memory_id = await self._store.add_memory(
                graph.nams_conversation_id,
                text,
            )
        except Exception:
            await self._control.mark_failed(idempotency_key)
            raise

        await self._control.mark_completed(
            idempotency_key,
            memory_id,
            self._utc_now(),
        )
        return RememberResult(
            memory_id=memory_id,
            status="processing",
            username=username,
            kb_id=graph.kb_id,
        )

    async def recall(
        self,
        user_id: str,
        kb_id: str,
        question: str,
        limit: int = 5,
    ) -> RecallResult:
        question = question.strip()
        if not question:
            raise ValueError("Recall question cannot be empty")
        limit = max(1, min(limit, 20))

        user = await self._require_user(user_id)
        username = self.username_for(user)
        graph = await self._require_owned_kb(user_id, kb_id)
        conversation_id = graph.nams_conversation_id

        nams_entities, context, messages = await asyncio.gather(
            self._store.search_entities(question, limit),
            self._store.get_context(conversation_id, question),
            self._store.list_messages(conversation_id, limit=200),
        )
        conversation_message_ids = {
            str(getattr(message, "id", "") or "")
            for message in messages
            if getattr(message, "id", None)
        }

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
        message_ids |= conversation_message_ids
        writes_by_message_id = await self._control.get_by_message_ids(
            graph.id,
            message_ids,
        )

        entities = [self._entity_to_view(entity) for entity in nams_entities]
        sources_by_id: dict[str, EvidenceView] = {}
        for history in history_batches:
            for source in self._history_to_evidence(history, writes_by_message_id):
                if (
                    conversation_message_ids
                    and source.id not in conversation_message_ids
                    and source.source == "nams"
                ):
                    continue
                sources_by_id.setdefault(source.id, source)

        if not sources_by_id:
            for message in messages:
                text = str(getattr(message, "content", "") or "")
                if not text:
                    continue
                message_id = str(getattr(message, "id", "") or "")
                created = str(
                    getattr(message, "created_at", None)
                    or getattr(message, "timestamp", None)
                    or ""
                )
                evidence_id = message_id or stable_id("msg", text)
                sources_by_id[evidence_id] = EvidenceView(
                    id=evidence_id,
                    source="nams-conversation",
                    text=text,
                    ingested_at=created,
                    provenance=self._write_to_provenance(
                        writes_by_message_id.get(evidence_id)
                    ),
                )

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
            found=bool(entities or context or sources),
            username=username,
            kb_id=graph.kb_id,
        )

    async def _require_user(self, user_id: str) -> UserRecord:
        user = await self._control.get_user(user_id)
        if user is None:
            raise PermissionError("Authenticated user not found")
        return user

    async def _require_owned_kb(self, user_id: str, kb_id: str) -> GraphRecord:
        kb_id = validate_kb_id(kb_id)
        graph = await self._control.get_graph_by_kb(user_id, kb_id)
        if graph is None:
            raise PermissionError(
                "Knowledge base not found for this user. "
                "Call create_knowledge_base(kb_id) first."
            )
        return graph

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


def validate_kb_id(kb_id: str) -> str:
    kb_id = kb_id.strip()
    if not KB_ID_PATTERN.fullmatch(kb_id):
        raise ValueError(
            "Invalid kb_id. Use 1-64 chars: letters, numbers, _ or - "
            "(must start with a letter or number)."
        )
    return kb_id


def _kb_view(graph: GraphRecord) -> KnowledgeBaseView:
    return KnowledgeBaseView(
        kb_id=graph.kb_id,
        name=graph.name,
        nams_conversation_id=graph.nams_conversation_id,
        created_at=graph.created_at,
    )


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
