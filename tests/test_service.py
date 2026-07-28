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

    async def add_memory(
        self,
        conversation_id: str,
        text: str,
        *,
        metadata=None,
    ) -> str:
        from app.memory_meta import stamp_memory_text

        content = stamp_memory_text(text, metadata) if metadata else text
        message_id = f"msg-{len(self.messages.setdefault(conversation_id, [])) + 1}"
        self.messages[conversation_id].append(
            SimpleNamespace(
                id=message_id,
                content=content,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        return message_id

    async def get_context(self, conversation_id: str, query: str) -> str:
        from app.memory_meta import strip_memory_meta

        return "\n".join(
            strip_memory_meta(m.content)
            for m in self.messages.get(conversation_id, [])
        )

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
    assert "skg_meta" not in result.context
    assert result.sources[0].provenance.client_id == "cursor-install-1"
    stored = service._store.messages[created.knowledge_base.nams_conversation_id][0]
    assert "skg_meta" in stored.content
    assert 'kb_id="project-a"' in stored.content
    assert 'owner_email="alice@example.com"' in stored.content
    assert 'writer_sub="user-a"' in stored.content


async def test_recall_drops_entities_from_other_conversations(
    service: KnowledgeService,
) -> None:
    user = await service.ensure_user("user-a", {"email": "alice@example.com"})
    await service.create_knowledge_base(user.id, "project-a")
    await service.remember(
        user.id,
        "project-a",
        "Neo4j powers the shared graph.",
        idempotency_key="idem-1",
    )

    foreign = SimpleNamespace(
        id="ent-foreign",
        name="Secret",
        type="THING",
        description="",
        aliases=[],
    )
    owned = SimpleNamespace(
        id="ent-owned",
        name="Neo4j",
        type="DATABASE",
        description="",
        aliases=[],
    )

    async def search_entities(query: str, limit: int):
        return [foreign, owned]

    async def get_entity_history(entity_id: str):
        if entity_id == "ent-owned":
            return [
                {
                    "messageId": "msg-1",
                    "content": (
                        'Neo4j powers the shared graph.\n\n'
                        '[skg_meta kb_id="project-a"]'
                    ),
                }
            ]
        return [
            {
                "messageId": "msg-other",
                "content": 'Secret from another kb.\n\n[skg_meta kb_id="other"]',
            }
        ]

    async def empty_relationships(entity_id: str):
        return []

    service._store.search_entities = search_entities  # type: ignore[method-assign]
    service._store.get_entity_history = get_entity_history  # type: ignore[method-assign]
    service._store.get_relationships = empty_relationships  # type: ignore[method-assign]

    result = await service.recall(user.id, "project-a", "database")
    assert [entity.name for entity in result.entities] == ["Neo4j"]


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
