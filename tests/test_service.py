from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.db import InMemoryControlStore
from app.service import KnowledgeService


class FakeNamsStore:
    def __init__(self) -> None:
        self.workspace_id = "ws-shared-test"
        self.messages: dict[str, list[SimpleNamespace]] = {}

    async def create_conversation(self, name: str, *, metadata=None) -> str:
        conversation_id = f"conv-{len(self.messages) + 1}"
        self.messages[conversation_id] = []
        return conversation_id

    async def add_memory(self, conversation_id: str, text: str) -> str:
        message_id = f"msg-{len(self.messages.setdefault(conversation_id, [])) + 1}"
        self.messages[conversation_id].append(
            SimpleNamespace(
                id=message_id,
                content=text,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        return message_id

    async def get_context(self, conversation_id: str, query: str) -> str:
        return "\n".join(m.content for m in self.messages.get(conversation_id, []))

    async def list_messages(self, conversation_id: str, *, limit: int = 100):
        return self.messages.get(conversation_id, [])[:limit]

    async def search_entities(self, query: str, limit: int) -> list:
        return []

    async def get_relationships(self, entity_id: str) -> list[dict]:
        return []

    async def get_entity_history(self, entity_id: str) -> list[dict]:
        return []


@pytest.fixture
def service() -> KnowledgeService:
    return KnowledgeService(FakeNamsStore(), InMemoryControlStore())


async def test_remember_and_recall_use_kb_id_payload(service: KnowledgeService) -> None:
    user = await service.ensure_user("user-a", {"email": "alice@example.com"})
    created = await service.create_knowledge_base(user.id, "project-a", "Alpha")
    assert created.knowledge_base.kb_id == "project-a"
    assert created.username == "alice"

    remembered = await service.remember(
        user.id,
        "project-a",
        "Neo4j powers the shared graph.",
        idempotency_key="idem-1",
        client_id="cursor-install-1",
    )
    assert remembered.memory_id == "msg-1"
    assert remembered.status == "processing"
    assert remembered.kb_id == "project-a"
    assert remembered.username == "alice"

    again = await service.remember(
        user.id,
        "project-a",
        "Neo4j powers the shared graph.",
        idempotency_key="idem-1",
        client_id="cursor-install-1",
    )
    assert again.status == "already_exists"

    result = await service.recall(user.id, "project-a", "What database is used?")
    assert result.found
    assert result.kb_id == "project-a"
    assert "Neo4j" in result.context
    assert result.sources[0].provenance.client_id == "cursor-install-1"


async def test_kb_ids_are_isolated_per_user(service: KnowledgeService) -> None:
    alice = await service.ensure_user("alice", {"email": "alice@example.com"})
    bob = await service.ensure_user("bob", {"email": "bob@example.com"})
    await service.create_knowledge_base(alice.id, "notes")

    with pytest.raises(PermissionError, match="Knowledge base not found"):
        await service.remember(
            bob.id,
            "notes",
            "Bob trying Alice kb",
            idempotency_key="idem-x",
        )

    bob_list = await service.list_knowledge_bases(bob.id)
    assert bob_list.knowledge_bases == []


async def test_same_user_multiple_kbs_do_not_mix_context(
    service: KnowledgeService,
) -> None:
    user = await service.ensure_user("multi", {"nickname": "multi"})
    await service.create_knowledge_base(user.id, "a")
    await service.create_knowledge_base(user.id, "b")

    await service.remember(user.id, "a", "secret-for-A", idempotency_key="idem-a")
    await service.remember(user.id, "b", "secret-for-B", idempotency_key="idem-b")

    recall_a = await service.recall(user.id, "a", "secret")
    assert "secret-for-A" in recall_a.context
    assert "secret-for-B" not in recall_a.context


async def test_invalid_kb_id_rejected(service: KnowledgeService) -> None:
    user = await service.ensure_user("user-x")
    with pytest.raises(ValueError, match="Invalid kb_id"):
        await service.create_knowledge_base(user.id, "bad id!")
