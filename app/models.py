from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ExtractedEntity(BaseModel):
    temp_id: str = Field(description="Identifier used only within this extraction")
    name: str
    kind: str = Field(description="A concise, dynamically chosen entity kind")
    summary: str = Field(description="Context-specific description for disambiguation")
    aliases: list[str] = Field(default_factory=list)


class ExtractedClaim(BaseModel):
    subject_temp_id: str
    predicate: str = Field(description="UPPER_SNAKE_CASE semantic predicate")
    object_temp_id: str | None = None
    object_literal: str | None = None
    polarity: Literal["positive", "negative"] = "positive"
    confidence: float = Field(ge=0, le=1)
    evidence_quote: str
    valid_from: str | None = None
    valid_to: str | None = None
    supersedes_existing: bool = Field(
        default=False,
        description="True only when the text explicitly replaces an older fact",
    )

    @model_validator(mode="after")
    def require_one_object(self) -> "ExtractedClaim":
        if (self.object_temp_id is None) == (self.object_literal is None):
            raise ValueError("Exactly one claim object must be supplied")
        return self


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity]
    claims: list[ExtractedClaim]


class ResolutionDecision(BaseModel):
    action: Literal["LINK", "NEW", "UNRESOLVED"]
    candidate_id: str | None = None
    confidence: float = Field(ge=0, le=1)
    reason: str


class EntityCandidate(BaseModel):
    id: str
    name: str
    kind: str
    summary: str
    aliases: list[str] = Field(default_factory=list)


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


class PushMemoryResult(BaseModel):
    knowledge_id: str
    memory_id: str
    created_entities: list[EntityView]
    reused_entities: list[EntityView]
    created_claim_ids: list[str]
    reused_claim_ids: list[str]
    unresolved_entities: list[str]


class SearchHit(BaseModel):
    entity: EntityView
    score: float
    claims: list[ClaimView] = Field(default_factory=list)


class SearchResult(BaseModel):
    query: str
    hits: list[SearchHit]
    insufficient_evidence: bool = False


class EntityResult(BaseModel):
    entity: EntityView
    claims: list[ClaimView]


class NeighborhoodResult(BaseModel):
    center: EntityView
    entities: list[EntityView]
    claims: list[ClaimView]
    truncated: bool = False
