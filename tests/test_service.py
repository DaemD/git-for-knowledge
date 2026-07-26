from app.models import (
    EntityCandidate,
    ExtractedEntity,
    ExtractionResult,
    ResolutionDecision,
)
from app.service import KnowledgeService


class FakeGraph:
    entity_created = False

    async def ensure_knowledge_base(self, knowledge_id: str) -> None:
        pass

    async def create_evidence(self, **kwargs) -> bool:
        return True

    async def find_candidates(self, *args, **kwargs) -> list[EntityCandidate]:
        return [
            EntityCandidate(
                id="ent_existing",
                name="Apple",
                kind="Company",
                summary="Technology company",
                aliases=["Apple"],
            )
        ]

    async def create_entity(self, **kwargs):
        self.entity_created = True
        raise AssertionError("Low-confidence links must not create a new entity")

    async def add_aliases(self, *args, **kwargs) -> None:
        pass


class FakeLLM:
    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2]

    async def extract(self, text: str) -> ExtractionResult:
        return ExtractionResult(
            entities=[
                ExtractedEntity(
                    temp_id="e1",
                    name="Apple",
                    kind="Unknown",
                    summary="Ambiguous Apple",
                )
            ],
            claims=[],
        )

    async def resolve(self, *args, **kwargs) -> ResolutionDecision:
        return ResolutionDecision(
            action="LINK",
            candidate_id="ent_existing",
            confidence=0.7,
            reason="Not enough context",
        )


async def test_low_confidence_link_remains_unresolved() -> None:
    graph = FakeGraph()
    service = KnowledgeService(graph, FakeLLM())

    result = await service.push_memory(
        "kg_12345678",
        "Apple is popular.",
        "test",
    )

    assert result.unresolved_entities == ["Apple"]
    assert result.created_entities == []
    assert result.reused_entities == []
    assert not graph.entity_created
