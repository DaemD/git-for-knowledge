from types import SimpleNamespace

import pytest

from app.service import KnowledgeService


class FakeNamsStore:
    async def ensure_conversation(self, knowledge_id: str) -> str:
        return "conv-1"

    async def add_memory(self, knowledge_id: str, text: str) -> tuple[str, str]:
        assert knowledge_id == "kg_12345678"
        assert text == "Neo4j powers the shared graph."
        return "msg-1", "conv-1"

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
    service = KnowledgeService(FakeNamsStore(), "kg_12345678")

    result = await service.remember(
        "kg_12345678",
        "Neo4j powers the shared graph.",
    )

    assert result.memory_id == "msg-1"
    assert result.status == "processing"


async def test_recall_maps_nams_entities_relationships_and_history() -> None:
    service = KnowledgeService(FakeNamsStore(), "kg_12345678")

    result = await service.recall("kg_12345678", "What database is used?")

    assert result.found
    assert result.entities[0].name == "Neo4j"
    assert result.relationships[0].predicate == "USES"
    assert result.sources[0].id == "msg-1"
    assert "Neo4j" in result.context


async def test_service_rejects_another_knowledge_id() -> None:
    service = KnowledgeService(FakeNamsStore(), "kg_12345678")

    with pytest.raises(ValueError, match="different NAMS workspace"):
        await service.recall("kg_87654321", "anything")
