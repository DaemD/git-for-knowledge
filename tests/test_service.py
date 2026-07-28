import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.memory_writes import MemoryWriteStore
from app.service import KnowledgeService


class FakeNamsStore:
    def __init__(self, fail_attempts: set[int] | None = None) -> None:
        self.add_calls: list[tuple[str, str]] = []
        self._fail_attempts = fail_attempts or set()

    async def add_memory(self, knowledge_id: str, text: str) -> tuple[str, str]:
        self.add_calls.append((knowledge_id, text))
        attempt = len(self.add_calls)
        if attempt in self._fail_attempts:
            raise RuntimeError("NAMS is unavailable")
        return f"msg-{attempt}", "conv-1"

    async def search_entities(self, query: str, limit: int) -> list:
        return [
            SimpleNamespace(
                id="entity-neo4j",
                name="Neo4j",
                type="TOOL",
                description="Graph database",
                aliases=[],
            )
        ]

    async def get_context(self, knowledge_id: str, query: str) -> str:
        return "## Observations\nNeo4j powers the shared graph."

    async def get_relationships(self, entity_id: str) -> list[dict]:
        return [
            {
                "source": {
                    "id": "entity-app",
                    "name": "Shared Knowledge MCP",
                    "type": "TOOL",
                },
                "target": {
                    "id": "entity-neo4j",
                    "name": "Neo4j",
                    "type": "TOOL",
                },
                "predicate": "USES",
                "relationship": {"confidence": 0.9},
            }
        ]

    async def get_entity_history(self, entity_id: str) -> list[dict]:
        return [
            {
                "messageId": "msg-1",
                "content": "Neo4j powers the shared graph.",
                "createdAt": "2026-07-27T12:00:00Z",
            }
        ]


def _service(
    tmp_path,
    store: FakeNamsStore | None = None,
) -> tuple[KnowledgeService, FakeNamsStore, MemoryWriteStore]:
    nams = store or FakeNamsStore()
    writes = MemoryWriteStore(tmp_path / "memory_writes.db")
    return KnowledgeService(nams, writes, "kg_12345678"), nams, writes


async def test_remember_creates_a_completed_write_and_calls_nams_once(tmp_path) -> None:
    service, store, writes = _service(tmp_path)

    result = await service.remember(
        "kg_12345678",
        "Neo4j powers the shared graph.",
        "swift-otter-000042",
        "5be1f3e7-c742-46a3-8e1a-e299a0cb6863",
    )

    assert result.memory_id == "msg-1"
    assert result.status == "processing"
    assert store.add_calls == [
        ("kg_12345678", "Neo4j powers the shared graph.")
    ]

    write = writes.get_by_key("5be1f3e7-c742-46a3-8e1a-e299a0cb6863")
    assert write is not None
    assert write.workspace_id == "kg_12345678"
    assert write.nams_message_id == "msg-1"
    assert write.client_id == "swift-otter-000042"
    assert write.content_hash == hashlib.sha256(
        b"Neo4j powers the shared graph."
    ).hexdigest()
    assert write.status == "completed"
    assert write.completed_at is not None
    assert datetime.fromisoformat(write.accepted_at.replace("Z", "+00:00")).tzinfo == timezone.utc


async def test_remember_returns_existing_completed_write_without_second_nams_call(tmp_path) -> None:
    service, store, _ = _service(tmp_path)

    first = await service.remember(
        "kg_12345678",
        "Neo4j powers the shared graph.",
        "swift-otter-000042",
        "retry-key",
    )
    retried = await service.remember(
        "kg_12345678",
        "Neo4j powers the shared graph.",
        "swift-otter-000042",
        "retry-key",
    )

    assert first.memory_id == "msg-1"
    assert retried.memory_id == "msg-1"
    assert retried.status == "already_exists"
    assert len(store.add_calls) == 1


async def test_remember_does_not_submit_a_pending_write_again(tmp_path) -> None:
    service, store, writes = _service(tmp_path)
    writes.begin_write(
        idempotency_key="pending-key",
        workspace_id="kg_12345678",
        client_id="swift-otter-000042",
        content_hash="hash",
        accepted_at="2026-07-28T12:00:00Z",
    )

    result = await service.remember(
        "kg_12345678",
        "Neo4j powers the shared graph.",
        "swift-otter-000042",
        "pending-key",
    )

    assert result.memory_id is None
    assert result.status == "processing"
    assert store.add_calls == []


async def test_remember_retries_a_failed_write(tmp_path) -> None:
    store = FakeNamsStore(fail_attempts={1})
    service, _, writes = _service(tmp_path, store)

    with pytest.raises(RuntimeError, match="NAMS is unavailable"):
        await service.remember(
            "kg_12345678",
            "Neo4j powers the shared graph.",
            "swift-otter-000042",
            "failed-key",
        )
    failed = writes.get_by_key("failed-key")
    assert failed is not None
    assert failed.status == "failed"

    result = await service.remember(
        "kg_12345678",
        "Neo4j powers the shared graph.",
        "swift-otter-000042",
        "failed-key",
    )

    assert result.memory_id == "msg-2"
    assert len(store.add_calls) == 2
    completed = writes.get_by_key("failed-key")
    assert completed is not None
    assert completed.status == "completed"
    assert completed.accepted_at == failed.accepted_at


async def test_remember_defaults_missing_client_id_for_web_clients(tmp_path) -> None:
    service, _, writes = _service(tmp_path)

    await service.remember(
        "kg_12345678",
        "Neo4j powers the shared graph.",
        None,
        "web-retry-key",
    )

    write = writes.get_by_key("web-retry-key")
    assert write is not None
    assert write.client_id == "web-unattributed"


async def test_recall_joins_provenance_from_sqlite_by_nams_message_id(tmp_path) -> None:
    service, _, writes = _service(tmp_path)
    writes.begin_write(
        idempotency_key="source-key",
        workspace_id="kg_12345678",
        client_id="swift-otter-000042",
        content_hash="hash",
        accepted_at="2026-07-28T12:00:00Z",
    )
    writes.mark_completed("source-key", "msg-1", "2026-07-28T12:01:00Z")

    result = await service.recall("kg_12345678", "What database is used?")

    assert result.found
    assert result.entities[0].name == "Neo4j"
    assert result.relationships[0].predicate == "USES"
    assert result.sources[0].id == "msg-1"
    assert result.sources[0].source == "nams"
    assert result.sources[0].provenance is not None
    assert result.sources[0].provenance.client_id == "swift-otter-000042"
    assert result.sources[0].provenance.accepted_at == "2026-07-28T12:00:00Z"
    assert "Neo4j" in result.context


async def test_service_rejects_another_knowledge_id(tmp_path) -> None:
    service, _, _ = _service(tmp_path)

    with pytest.raises(ValueError, match="different NAMS workspace"):
        await service.recall("kg_87654321", "anything")
