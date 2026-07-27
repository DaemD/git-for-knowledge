from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.service import KnowledgeService


class FakeNamsStore:
    def __init__(self) -> None:
        self.add_calls: list[dict[str, object]] = []
        self.existing_memory_ids: dict[str, str] = {}

    async def ensure_conversation(self, knowledge_id: str) -> str:
        return "conv-1"

    async def find_memory_by_idempotency_key(
        self,
        knowledge_id: str,
        idempotency_key: str,
    ) -> str | None:
        assert knowledge_id == "kg_12345678"
        return self.existing_memory_ids.get(idempotency_key)

    async def add_memory(
        self,
        knowledge_id: str,
        text: str,
        metadata: dict[str, str],
    ) -> tuple[str, str]:
        assert knowledge_id == "kg_12345678"
        assert text == "Neo4j powers the shared graph."
        self.add_calls.append(
            {
                "knowledge_id": knowledge_id,
                "text": text,
                "metadata": metadata,
            }
        )
        return "msg-1", "conv-1"

    async def get_message_metadata(
        self,
        knowledge_id: str,
        message_ids: set[str],
    ) -> dict[str, dict[str, str]]:
        assert knowledge_id == "kg_12345678"
        if not message_ids:
            return {}
        assert message_ids == {"msg-1"}
        return {
            "msg-1": {
                "client_id": "swift-otter-000042",
                "timestamp": "2026-07-28T12:00:00Z",
                "idempotency_key": "5be1f3e7-c742-46a3-8e1a-e299a0cb6863",
            }
        }

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

async def test_remember_is_queued_for_nams_extraction() -> None:
    store = FakeNamsStore()
    service = KnowledgeService(store, "kg_12345678")

    result = await service.remember(
        "kg_12345678",
        "Neo4j powers the shared graph.",
        "swift-otter-000042",
        "5be1f3e7-c742-46a3-8e1a-e299a0cb6863",
    )

    assert result.memory_id == "msg-1"
    assert result.status == "processing"
    metadata = store.add_calls[0]["metadata"]
    assert metadata == {
        "client_id": "swift-otter-000042",
        "timestamp": metadata["timestamp"],
        "idempotency_key": "5be1f3e7-c742-46a3-8e1a-e299a0cb6863",
    }
    timestamp = datetime.fromisoformat(metadata["timestamp"].replace("Z", "+00:00"))
    assert timestamp.tzinfo == timezone.utc


async def test_remember_skips_an_existing_idempotency_key() -> None:
    store = FakeNamsStore()
    store.existing_memory_ids["retry-key"] = "msg-existing"
    service = KnowledgeService(store, "kg_12345678")

    result = await service.remember(
        "kg_12345678",
        "Neo4j powers the shared graph.",
        "swift-otter-000042",
        "retry-key",
    )

    assert result.memory_id == "msg-existing"
    assert result.status == "already_exists"
    assert store.add_calls == []


async def test_remember_defaults_missing_client_id_for_web_clients() -> None:
    store = FakeNamsStore()
    service = KnowledgeService(store, "kg_12345678")

    await service.remember(
        "kg_12345678",
        "Neo4j powers the shared graph.",
        None,
        "web-retry-key",
    )

    metadata = store.add_calls[0]["metadata"]
    assert metadata["client_id"] == "web-unattributed"


async def test_recall_maps_nams_entities_relationships_and_history() -> None:
    service = KnowledgeService(FakeNamsStore(), "kg_12345678")

    result = await service.recall("kg_12345678", "What database is used?")

    assert result.found
    assert result.entities[0].name == "Neo4j"
    assert result.relationships[0].predicate == "USES"
    assert result.sources[0].id == "msg-1"
    assert result.sources[0].source == "nams"
    assert result.sources[0].provenance is not None
    assert result.sources[0].provenance.client_id == "swift-otter-000042"
    assert result.sources[0].provenance.timestamp == "2026-07-28T12:00:00Z"
    assert (
        result.sources[0].provenance.idempotency_key
        == "5be1f3e7-c742-46a3-8e1a-e299a0cb6863"
    )
    assert "Neo4j" in result.context


async def test_service_rejects_another_knowledge_id() -> None:
    service = KnowledgeService(FakeNamsStore(), "kg_12345678")

    with pytest.raises(ValueError, match="different NAMS workspace"):
        await service.recall("kg_87654321", "anything")
