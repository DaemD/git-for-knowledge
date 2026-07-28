import pytest
from unittest.mock import AsyncMock, patch

from app.db import InMemoryControlStore
from app.service import KnowledgeService

from tests.test_service import FakeNamsStore


@pytest.fixture
def service() -> KnowledgeService:
    return KnowledgeService(FakeNamsStore(), InMemoryControlStore())


async def test_owner_can_invite_existing_user(service: KnowledgeService) -> None:
    bob = await service.ensure_user("bob", {"email": "bob@example.com"})
    alice = await service.ensure_user("alice", {"email": "alice@example.com"})
    await service.create_knowledge_base(bob.id, "team-project", "Team Project")

    invited = await service.invite_to_knowledge_base(
        bob.id,
        "team-project",
        "alice@example.com",
        role="write",
    )
    assert invited.status == "active"
    assert invited.role == "write"

    alice_list = await service.list_knowledge_bases(alice.id)
    assert len(alice_list.knowledge_bases) == 1
    shared = alice_list.knowledge_bases[0]
    assert shared.kb_id == "team-project"
    assert shared.shared is True
    assert shared.role == "write"
    assert shared.owner_email == "bob@example.com"


async def test_invitee_can_recall_and_write_shared_kb(service: KnowledgeService) -> None:
    bob = await service.ensure_user("bob", {"email": "bob@example.com"})
    alice = await service.ensure_user("alice", {"email": "alice@example.com"})
    await service.create_knowledge_base(bob.id, "team-project")
    await service.invite_to_knowledge_base(
        bob.id,
        "team-project",
        "alice@example.com",
        role="write",
    )

    await service.remember(
        bob.id,
        "team-project",
        "Shared architecture uses Postgres.",
        idempotency_key="bob-1",
    )
    await service.remember(
        alice.id,
        "team-project",
        "Alice added a deployment note.",
        idempotency_key="alice-1",
    )

    recall = await service.recall(alice.id, "team-project", "architecture")
    assert recall.found
    assert "Postgres" in recall.context
    assert "deployment note" in recall.context


async def test_pending_invite_activates_on_first_login(service: KnowledgeService) -> None:
    bob = await service.ensure_user("bob", {"email": "bob@example.com"})
    await service.create_knowledge_base(bob.id, "team-project")
    invited = await service.invite_to_knowledge_base(
        bob.id,
        "team-project",
        "alice@example.com",
        role="read",
    )
    assert invited.status == "pending"

    alice = await service.ensure_user("alice", {"email": "alice@example.com"})
    alice_list = await service.list_knowledge_bases(alice.id)
    assert len(alice_list.knowledge_bases) == 1
    assert alice_list.knowledge_bases[0].role == "read"

    with pytest.raises(PermissionError, match="Write access required"):
        await service.remember(
            alice.id,
            "team-project",
            "Alice cannot write here",
            idempotency_key="alice-read-only",
        )


async def test_read_member_can_recall_but_not_write(service: KnowledgeService) -> None:
    bob = await service.ensure_user("bob", {"email": "bob@example.com"})
    alice = await service.ensure_user("alice", {"email": "alice@example.com"})
    await service.create_knowledge_base(bob.id, "docs")
    await service.invite_to_knowledge_base(
        bob.id,
        "docs",
        "alice@example.com",
        role="read",
    )
    await service.remember(
        bob.id,
        "docs",
        "Secret design doc",
        idempotency_key="bob-docs",
    )

    recall = await service.recall(alice.id, "docs", "design")
    assert recall.found
    assert "Secret design doc" in recall.context

    with pytest.raises(PermissionError, match="Write access required"):
        await service.remember(
            alice.id,
            "docs",
            "Alice write attempt",
            idempotency_key="alice-docs",
        )


async def test_owner_can_list_and_revoke_members(service: KnowledgeService) -> None:
    bob = await service.ensure_user("bob", {"email": "bob@example.com"})
    alice = await service.ensure_user("alice", {"email": "alice@example.com"})
    await service.create_knowledge_base(bob.id, "team-project")
    await service.invite_to_knowledge_base(
        bob.id,
        "team-project",
        "alice@example.com",
        role="write",
    )

    members = await service.list_knowledge_base_members(bob.id, "team-project")
    emails = {member.email for member in members.members}
    assert "bob@example.com" in emails
    assert "alice@example.com" in emails

    revoked = await service.revoke_knowledge_base_access(
        bob.id,
        "team-project",
        "alice@example.com",
    )
    assert revoked.revoked is True

    with pytest.raises(PermissionError, match="access denied"):
        await service.recall(alice.id, "team-project", "anything")


async def test_invite_attempts_email(service: KnowledgeService) -> None:
    bob = await service.ensure_user("bob", {"email": "bob@example.com", "name": "Bob"})
    await service.create_knowledge_base(bob.id, "team-project", "Team Project")

    with patch(
        "app.service.send_kb_invite_email",
        new_callable=AsyncMock,
    ) as send_email:
        send_email.return_value = type(
            "R",
            (),
            {"sent": True, "error": None},
        )()
        invited = await service.invite_to_knowledge_base(
            bob.id,
            "team-project",
            "alice@example.com",
            role="read",
        )
    assert invited.email_sent is True
    send_email.assert_awaited_once()


async def test_non_owner_cannot_invite(service: KnowledgeService) -> None:
    bob = await service.ensure_user("bob", {"email": "bob@example.com"})
    alice = await service.ensure_user("alice", {"email": "alice@example.com"})
    await service.create_knowledge_base(bob.id, "team-project")

    with pytest.raises(PermissionError):
        await service.invite_to_knowledge_base(
            alice.id,
            "team-project",
            "carol@example.com",
        )
