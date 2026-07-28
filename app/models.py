from datetime import datetime
import re

from pydantic import BaseModel, Field


KB_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class EntityView(BaseModel):
    id: str
    name: str
    kind: str
    summary: str = ""
    aliases: list[str] = Field(default_factory=list)


class ProvenanceView(BaseModel):
    """Client provenance retained by this MCP service for a NAMS source."""

    client_id: str
    accepted_at: str


class EvidenceView(BaseModel):
    id: str
    source: str
    text: str
    ingested_at: str
    provenance: ProvenanceView | None = None


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
    memory_id: str | None
    status: str = "processing"
    username: str | None = None
    kb_id: str | None = None


class RecallResult(BaseModel):
    question: str
    context: str = ""
    entities: list[EntityView]
    relationships: list[ClaimView]
    sources: list[EvidenceView]
    found: bool
    username: str | None = None
    kb_id: str | None = None


class KnowledgeBaseView(BaseModel):
    kb_id: str
    name: str
    nams_conversation_id: str
    created_at: datetime


class KnowledgeBaseListResult(BaseModel):
    username: str
    knowledge_bases: list[KnowledgeBaseView]


class CreateKnowledgeBaseResult(BaseModel):
    username: str
    knowledge_base: KnowledgeBaseView
