from typing import Literal

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


class PushMemoryResult(BaseModel):
    knowledge_id: str
    memory_id: str
    conversation_id: str
    ingestion_status: Literal["queued"] = "queued"
    extraction_pending: bool = True
    created_entities: list[EntityView] = Field(default_factory=list)
    reused_entities: list[EntityView] = Field(default_factory=list)
    created_claim_ids: list[str] = Field(default_factory=list)
    reused_claim_ids: list[str] = Field(default_factory=list)
    unresolved_entities: list[str] = Field(default_factory=list)


class SearchHit(BaseModel):
    entity: EntityView
    score: float
    claims: list[ClaimView] = Field(default_factory=list)


class SearchResult(BaseModel):
    query: str
    hits: list[SearchHit]
    context: str = ""
    insufficient_evidence: bool = False


class EntityResult(BaseModel):
    entity: EntityView
    claims: list[ClaimView]


class NeighborhoodResult(BaseModel):
    center: EntityView
    entities: list[EntityView]
    claims: list[ClaimView]
    truncated: bool = False
