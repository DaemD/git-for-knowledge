"""Product service: auth user + kb_id logical knowledge bases."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from app.db import ControlStore, GraphRecord, MemoryWrite, UserRecord, hash_content
from app.auth import current_access_token, resolve_user_profile
from app.billing import evaluate_entitlement, require_entitlement
from app.config import get_settings
from app.email_service import send_kb_invite_email
from app.memory_meta import (
    build_memory_metadata,
    metadata_matches_kb,
    parse_memory_meta,
    strip_memory_meta,
)
from app.models import (
    ClaimView,
    CreateKnowledgeBaseResult,
    DashboardMeResult,
    DeleteKnowledgeBaseResult,
    EntityView,
    EvidenceView,
    InviteToKnowledgeBaseResult,
    KB_ID_PATTERN,
    KnowledgeBaseDetailResult,
    KnowledgeBaseListResult,
    KnowledgeBaseMemberView,
    KnowledgeBaseMembersResult,
    KnowledgeBaseView,
    ProvenanceView,
    RecallResult,
    RecentAdditionView,
    RememberResult,
    RevokeKnowledgeBaseAccessResult,
    UpgradeResult,
)
from app.nams import NamsStore
from app.lemon_billing import (
    BillingNotConfiguredError,
    create_checkout_session,
)
from app.utils import stable_id


MAX_PROVENANCE_VALUE_LENGTH = 256
WEB_UNATTRIBUTED_CLIENT_ID = "web-unattributed"
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
KB_MEMBER_ROLES = frozenset({"read", "write"})


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
        email, display_name = await resolve_user_profile(
            claims,
            current_access_token(),
        )
        user = await self._control.upsert_user(
            subject,
            email=email,
            display_name=display_name,
        )
        if email:
            await self._control.accept_pending_invites(user.id, email)
        return user

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
        user = await self._require_entitled_user(user_id)
        graphs = await self._control.list_accessible_graphs(user_id)
        return KnowledgeBaseListResult(
            username=self.username_for(user),
            knowledge_bases=[
                _kb_view(item.graph, item.role, item.owner_email)
                for item in graphs
            ],
        )

    async def create_knowledge_base(
        self,
        user_id: str,
        kb_id: str,
        name: str | None = None,
    ) -> CreateKnowledgeBaseResult:
        user = await self._require_entitled_user(user_id)
        kb_id = validate_kb_id(kb_id)
        label = (name or kb_id).strip()
        if not label:
            raise ValueError("Knowledge base name cannot be empty")
        if len(label) > 120:
            raise ValueError("Knowledge base name must be 120 characters or fewer")

        conversation_id = await self._store.create_conversation(
            label,
            metadata={
                "purpose": "grphly",
                "kb_id": kb_id,
                "kb_name": label,
                "owner_sub": user_id,
                "owner_email": user.email or "",
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
            knowledge_base=_kb_view(graph, role="owner"),
        )

    async def invite_to_knowledge_base(
        self,
        user_id: str,
        kb_id: str,
        email: str,
        role: str = "write",
    ) -> InviteToKnowledgeBaseResult:
        await self._require_entitled_user(user_id)
        graph = await self._require_owned_kb(user_id, kb_id)
        invitee_email = validate_email(email)
        member_role = validate_member_role(role)
        owner = await self._require_user(user_id)
        if owner.email and invitee_email == owner.email.strip().lower():
            raise ValueError("You cannot invite yourself to your own knowledge base")

        await self._control.upsert_kb_invite(
            graph_id=graph.id,
            invitee_email=invitee_email,
            role=member_role,
            invited_by=user_id,
        )

        invitee = await self._control.find_user_by_email(invitee_email)
        status = "pending"
        if invitee is not None:
            await self._control.upsert_graph_member(
                graph_id=graph.id,
                user_id=invitee.id,
                role=member_role,
            )
            await self._control.accept_pending_invites(invitee.id, invitee_email)
            status = "active"

        email_result = await send_kb_invite_email(
            get_settings(),
            to_email=invitee_email,
            kb_id=graph.kb_id,
            kb_name=graph.name,
            role=member_role,
            inviter_email=owner.email,
            inviter_name=owner.display_name,
        )
        return InviteToKnowledgeBaseResult(
            kb_id=graph.kb_id,
            email=invitee_email,
            role=member_role,
            status=status,
            email_sent=email_result.sent,
            email_error=email_result.error,
        )

    async def delete_knowledge_base(
        self,
        user_id: str,
        kb_id: str,
    ) -> DeleteKnowledgeBaseResult:
        await self._require_entitled_user(user_id)
        graph = await self._require_owned_kb(user_id, kb_id)
        nams_cleared = False
        try:
            await self._store.clear_conversation(graph.nams_conversation_id)
            nams_cleared = True
        except Exception:
            # Still remove control-plane row so the KB stops being usable.
            nams_cleared = False

        deleted = await self._control.delete_graph(user_id, graph.kb_id)
        if deleted is None:
            raise PermissionError("Knowledge base could not be deleted")
        return DeleteKnowledgeBaseResult(
            kb_id=graph.kb_id,
            deleted=True,
            nams_cleared=nams_cleared,
        )

    async def list_knowledge_base_members(
        self,
        user_id: str,
        kb_id: str,
    ) -> KnowledgeBaseMembersResult:
        await self._require_entitled_user(user_id)
        graph = await self._require_kb_access(user_id, kb_id, need_write=False)
        members = await self._members_for_graph(graph)
        return KnowledgeBaseMembersResult(kb_id=graph.kb_id, members=members)

    async def dashboard_me(self, user_id: str) -> DashboardMeResult:
        user = await self._require_entitled_user(user_id)
        settings = get_settings()
        mcp_url = str(settings.public_base_url).rstrip("/") + "/mcp"
        client_id = settings.dashboard_oauth_client_id.strip() or None
        return DashboardMeResult(
            user_id=user.id,
            username=self.username_for(user),
            email=user.email,
            display_name=user.display_name,
            plan_status=user.plan_status,
            mcp_url=mcp_url,
            oauth_client_id=client_id,
        )

    async def get_knowledge_base_detail(
        self,
        user_id: str,
        kb_id: str,
        *,
        recent_limit: int = 30,
    ) -> KnowledgeBaseDetailResult:
        user = await self._require_entitled_user(user_id)
        graph = await self._require_kb_access(user_id, kb_id, need_write=False)

        accessible = await self._control.list_accessible_graphs(user_id)
        match = next(
            (item for item in accessible if item.graph.id == graph.id),
            None,
        )
        role = match.role if match else ("owner" if graph.user_id == user_id else "read")
        owner_email = match.owner_email if match else None
        if owner_email is None:
            owner = await self._control.get_user(graph.user_id)
            owner_email = owner.email if owner else None

        members = await self._members_for_graph(graph)
        me = next(
            (
                member
                for member in members
                if member.user_id == user_id
                or (
                    member.email
                    and user.email
                    and member.email.lower() == user.email.lower()
                )
            ),
            KnowledgeBaseMemberView(
                email=user.email or user_id,
                role=role,
                status="active",
                user_id=user_id,
            ),
        )

        push_count = await self._control.count_writes(graph.id)
        writes = await self._control.list_recent_writes(
            graph.id,
            limit=recent_limit,
        )

        message_text: dict[str, str] = {}
        try:
            messages = await self._store.list_messages(
                graph.nams_conversation_id,
                limit=max(recent_limit * 2, 50),
            )
            for message in messages:
                mid = str(getattr(message, "id", "") or "")
                content = str(getattr(message, "content", "") or "")
                if mid and content:
                    message_text[mid] = strip_memory_meta(content)
        except Exception:
            message_text = {}

        writer_cache: dict[str, str | None] = {}
        recent: list[RecentAdditionView] = []
        for write in writes:
            if write.user_id not in writer_cache:
                writer = await self._control.get_user(write.user_id)
                writer_cache[write.user_id] = writer.email if writer else None
            preview = (
                message_text.get(write.nams_message_id or "", "")
                or f"(stored · {write.content_hash[:12]})"
            )
            recent.append(
                RecentAdditionView(
                    memory_id=write.nams_message_id,
                    preview=_preview_text(preview),
                    client_id=write.client_id,
                    status=write.status,
                    accepted_at=write.accepted_at,
                    writer_email=writer_cache[write.user_id],
                )
            )

        return KnowledgeBaseDetailResult(
            username=self.username_for(user),
            knowledge_base=_kb_view(graph, role=role, owner_email=owner_email),
            push_count=push_count,
            recent_additions=recent,
            members=members,
            me=me,
        )

    async def _members_for_graph(
        self,
        graph: GraphRecord,
    ) -> list[KnowledgeBaseMemberView]:
        owner = await self._require_user(graph.user_id)
        members = [
            KnowledgeBaseMemberView(
                email=owner.email or graph.user_id,
                role="owner",
                status="active",
                user_id=owner.id,
            )
        ]
        for member in await self._control.list_kb_members(graph.id):
            members.append(
                KnowledgeBaseMemberView(
                    email=member.email or member.user_id,
                    role=member.role,
                    status="active",
                    user_id=member.user_id,
                )
            )
        for invite in await self._control.list_pending_invites(graph.id):
            members.append(
                KnowledgeBaseMemberView(
                    email=invite.invitee_email,
                    role=invite.role,
                    status="pending",
                    user_id=None,
                )
            )
        return members

    async def revoke_knowledge_base_access(
        self,
        user_id: str,
        kb_id: str,
        email: str,
    ) -> RevokeKnowledgeBaseAccessResult:
        await self._require_entitled_user(user_id)
        graph = await self._require_owned_kb(user_id, kb_id)
        invitee_email = validate_email(email)
        revoked = await self._control.revoke_kb_access(graph.id, invitee_email)
        return RevokeKnowledgeBaseAccessResult(
            kb_id=graph.kb_id,
            email=invitee_email,
            revoked=revoked,
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

        user = await self._require_entitled_user(user_id)
        username = self.username_for(user)
        graph = await self._require_kb_access(user_id, kb_id, need_write=True)
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
            owner = await self._require_user(graph.user_id)
            memory_meta = build_memory_metadata(
                kb_id=graph.kb_id,
                kb_name=graph.name,
                owner_sub=graph.user_id,
                owner_email=owner.email,
                writer_sub=user.id,
                writer_email=user.email,
                graph_id=graph.id,
                nams_conversation_id=graph.nams_conversation_id,
            )
            memory_id = await self._store.add_memory(
                graph.nams_conversation_id,
                text,
                metadata=memory_meta,
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

        user = await self._require_entitled_user(user_id)
        username = self.username_for(user)
        graph = await self._require_kb_access(user_id, kb_id, need_write=False)
        conversation_id = graph.nams_conversation_id

        nams_entities, context, messages = await asyncio.gather(
            self._store.search_entities(question, limit),
            self._store.get_context(conversation_id, question),
            self._store.list_messages(conversation_id, limit=200),
        )
        context = strip_memory_meta(context) if context else context
        conversation_message_ids = {
            str(getattr(message, "id", "") or "")
            for message in messages
            if getattr(message, "id", None)
        }

        history_batches = await asyncio.gather(
            *(
                self._store.get_entity_history(str(entity.id))
                for entity in nams_entities
            )
        )

        scoped_entities: list[Any] = []
        scoped_histories: list[list[dict[str, Any]]] = []
        for entity, history in zip(nams_entities, history_batches, strict=True):
            if self._entity_belongs_to_kb(
                history,
                conversation_message_ids,
                kb_id=graph.kb_id,
                graph_id=graph.id,
            ):
                scoped_entities.append(entity)
                scoped_histories.append(history)

        relationship_batches = await asyncio.gather(
            *(
                self._store.get_relationships(str(entity.id))
                for entity in scoped_entities
            )
        ) if scoped_entities else []

        message_ids = {
            str(message_id)
            for history in scoped_histories
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

        entities = [self._entity_to_view(entity) for entity in scoped_entities]
        sources_by_id: dict[str, EvidenceView] = {}
        for history in scoped_histories:
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
                sources_by_id[evidence_id] = self._evidence_from_text(
                    evidence_id=evidence_id,
                    source_label="nams-conversation",
                    text=text,
                    ingested_at=created,
                    write=writes_by_message_id.get(evidence_id),
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

    async def create_upgrade_checkout(self, user_id: str) -> UpgradeResult:
        """Create Lemon Squeezy Checkout for the authenticated user."""
        user = await self._require_user(user_id)
        settings = get_settings()
        entitlement = evaluate_entitlement(user, settings)
        trial_ends = (
            entitlement.trial_ends_at.isoformat()
            if entitlement.trial_ends_at
            else None
        )
        if entitlement.allowed and user.plan_status == "active":
            return UpgradeResult(
                checkout_url=None,
                plan_status=user.plan_status,
                trial_ends_at=trial_ends,
                entitled=True,
                message="Subscription already active.",
            )
        try:
            url = await create_checkout_session(settings, user)
        except BillingNotConfiguredError as exc:
            return UpgradeResult(
                checkout_url=None,
                plan_status=user.plan_status,
                trial_ends_at=trial_ends,
                entitled=entitlement.allowed,
                message=(
                    f"{exc} Visit {settings.billing_upgrade_url} for pricing."
                ),
            )
        return UpgradeResult(
            checkout_url=url,
            plan_status=user.plan_status,
            trial_ends_at=trial_ends,
            entitled=entitlement.allowed,
            message="Open this Lemon Squeezy checkout URL to subscribe.",
        )

    async def _require_user(self, user_id: str) -> UserRecord:
        user = await self._control.get_user(user_id)
        if user is None:
            raise PermissionError("Authenticated user not found")
        return user

    async def _require_entitled_user(self, user_id: str) -> UserRecord:
        user = await self._require_user(user_id)
        require_entitlement(user, get_settings())
        return user

    @staticmethod
    def _entity_belongs_to_kb(
        history: list[dict[str, Any]],
        conversation_message_ids: set[str],
        *,
        kb_id: str,
        graph_id: str,
    ) -> bool:
        """Keep entities only if provenance ties them to this KB conversation."""
        if not conversation_message_ids and not history:
            return False
        for mention in history:
            message_id = str(
                mention.get("messageId")
                or mention.get("message_id")
                or mention.get("id")
                or ""
            )
            if message_id and message_id in conversation_message_ids:
                return True
            text = str(
                mention.get("content")
                or mention.get("text")
                or mention.get("quote")
                or mention.get("messageContent")
                or mention.get("message_content")
                or ""
            )
            if text and metadata_matches_kb(text, kb_id, graph_id):
                return True
        return False

    async def _require_owned_kb(self, user_id: str, kb_id: str) -> GraphRecord:
        kb_id = validate_kb_id(kb_id)
        graph = await self._control.get_graph_by_kb(user_id, kb_id)
        if graph is None:
            raise PermissionError(
                "Knowledge base not found for this user. "
                "Call kb_create(kb_id) first."
            )
        return graph

    async def _require_kb_access(
        self,
        user_id: str,
        kb_id: str,
        *,
        need_write: bool,
    ) -> GraphRecord:
        kb_id = validate_kb_id(kb_id)
        owned = await self._control.get_graph_by_kb(user_id, kb_id)
        if owned is not None:
            return owned

        shared = await self._control.list_member_graphs_by_kb(user_id, kb_id)
        if len(shared) > 1:
            raise PermissionError(
                "Multiple shared knowledge bases use this kb_id. "
                "Ask the owner to rename one of them."
            )
        if len(shared) == 1:
            graph, role = shared[0]
            if need_write and role != "write":
                raise PermissionError(
                    "Write access required for this knowledge base."
                )
            return graph

        raise PermissionError(
            "Knowledge base not found or access denied. "
            "Create it or ask the owner for an invite."
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
            source = cls._evidence_from_text(
                evidence_id=str(evidence_id),
                source_label="nams",
                text=str(text),
                ingested_at=str(ingested_at),
                write=writes_by_message_id.get(str(evidence_id)),
            )
            evidence.append(source)
        return evidence

    @classmethod
    def _evidence_from_text(
        cls,
        *,
        evidence_id: str,
        source_label: str,
        text: str,
        ingested_at: str,
        write: MemoryWrite | None,
    ) -> EvidenceView:
        meta = parse_memory_meta(text)
        base = cls._write_to_provenance(write)
        return EvidenceView(
            id=evidence_id,
            source=source_label,
            text=strip_memory_meta(text),
            ingested_at=ingested_at,
            provenance=ProvenanceView(
                client_id=(
                    base.client_id if base else WEB_UNATTRIBUTED_CLIENT_ID
                ),
                accepted_at=base.accepted_at if base else ingested_at,
                writer_sub=meta.get("writer_sub") or None,
                writer_email=meta.get("writer_email") or None,
                kb_id=meta.get("kb_id") or None,
                owner_email=meta.get("owner_email") or None,
            ),
        )

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


def _preview_text(text: str, limit: int = 280) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _kb_view(
    graph: GraphRecord,
    role: str = "owner",
    owner_email: str | None = None,
) -> KnowledgeBaseView:
    return KnowledgeBaseView(
        kb_id=graph.kb_id,
        name=graph.name,
        nams_conversation_id=graph.nams_conversation_id,
        created_at=graph.created_at,
        role=role,
        shared=role != "owner",
        owner_email=owner_email if role != "owner" else None,
    )


def validate_email(email: str) -> str:
    normalized = email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Invalid email address")
    return normalized


def validate_member_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in KB_MEMBER_ROLES:
        raise ValueError("role must be 'read' or 'write'")
    return normalized


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
