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

    async def get_entity(self, entity_id: str) -> dict | None:
        if entity_id != "entity-neo4j":
            return None
        return {
            "id": "entity-neo4j",
            "name": "Neo4j",
            "type": "TOOL",
            "description": "Graph database",
        }

    async def get_neighborhood(
        self,
        entity_id: str,
        depth: int,
        limit: int,
    ) -> tuple[list[dict], list[dict], bool]:
        entity = await self.get_entity(entity_id)
        return ([entity] if entity else []), [], False


async def test_push_memory_is_queued_for_nams_extraction() -> None:
    service = KnowledgeService(FakeNamsStore(), "kg_12345678")

    result = await service.push_memory(
        "kg_12345678",
        "Neo4j powers the shared graph.",
        "test",
    )

    assert result.memory_id == "msg-1"
    assert result.conversation_id == "conv-1"
    assert result.ingestion_status == "queued"
    assert result.extraction_pending


async def test_search_maps_nams_entities_relationships_and_history() -> None:
    service = KnowledgeService(FakeNamsStore(), "kg_12345678")

    result = await service.search("kg_12345678", "What database is used?")

    assert not result.insufficient_evidence
    assert result.hits[0].entity.name == "Neo4j"
    assert result.hits[0].claims[0].predicate == "USES"
    assert result.hits[0].claims[0].evidence[0].id == "msg-1"
    assert "Neo4j" in result.context


async def test_service_rejects_another_knowledge_id() -> None:
    service = KnowledgeService(FakeNamsStore(), "kg_12345678")

    with pytest.raises(ValueError, match="different NAMS workspace"):
        await service.search("kg_87654321", "anything")
