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
    writer_sub: str | None = None
    writer_email: str | None = None
    kb_id: str | None = None
    owner_email: str | None = None


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
    role: str = "owner"
    shared: bool = False
    owner_email: str | None = None


class KnowledgeBaseListResult(BaseModel):
    username: str
    knowledge_bases: list[KnowledgeBaseView]


class CreateKnowledgeBaseResult(BaseModel):
    username: str
    knowledge_base: KnowledgeBaseView


class KnowledgeBaseMemberView(BaseModel):
    email: str
    role: str
    status: str
    user_id: str | None = None


class KnowledgeBaseMembersResult(BaseModel):
    kb_id: str
    members: list[KnowledgeBaseMemberView]


class InviteToKnowledgeBaseResult(BaseModel):
    kb_id: str
    email: str
    role: str
    status: str
    email_sent: bool = False
    email_error: str | None = None


class RevokeKnowledgeBaseAccessResult(BaseModel):
    kb_id: str
    email: str
    revoked: bool


class DeleteKnowledgeBaseResult(BaseModel):
    kb_id: str
    deleted: bool
    nams_cleared: bool = False


class UpgradeResult(BaseModel):
    checkout_url: str | None = None
    plan_status: str
    trial_ends_at: str | None = None
    entitled: bool
    message: str


class RecentAdditionView(BaseModel):
    memory_id: str | None = None
    preview: str
    client_id: str | None = None
    status: str
    accepted_at: str
    writer_email: str | None = None


class KnowledgeBaseDetailResult(BaseModel):
    username: str
    knowledge_base: KnowledgeBaseView
    push_count: int = 0
    recent_additions: list[RecentAdditionView] = Field(default_factory=list)
    members: list[KnowledgeBaseMemberView] = Field(default_factory=list)
    me: KnowledgeBaseMemberView | None = None


class DashboardMeResult(BaseModel):
    user_id: str
    username: str
    email: str | None = None
    display_name: str | None = None
    plan_status: str
    mcp_url: str
    oauth_client_id: str | None = None


class GraphNodeView(BaseModel):
    id: str
    label: str
    kind: str = "concept"
    summary: str = ""


class GraphEdgeView(BaseModel):
    id: str
    source: str
    target: str
    predicate: str


class KnowledgeBaseGraphResult(BaseModel):
    kb_id: str
    nodes: list[GraphNodeView] = Field(default_factory=list)
    edges: list[GraphEdgeView] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0
