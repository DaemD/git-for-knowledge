from pydantic import BaseModel, Field


class EntityView(BaseModel):
    id: str
    name: str
    kind: str
    summary: str = ""
    aliases: list[str] = Field(default_factory=list)


class EvidenceView(BaseModel):
    id: str
    source: str
    text: str
    ingested_at: str


class ClaimView(BaseModel):
    id: str
    subject: EntityView
    predicate: str
    object: EntityView | str
    polarity: str
    status: str
    confidence: float
    valid_from: str | None = None
    valid_to: str | None = None
    evidence: list[EvidenceView] = Field(default_factory=list)


class RememberResult(BaseModel):
    memory_id: str
    status: str = "processing"


class RecallResult(BaseModel):
    question: str
    context: str = ""
    entities: list[EntityView]
    relationships: list[ClaimView]
    sources: list[EvidenceView]
    found: bool
