from datetime import datetime, timezone

from app.models import KnowledgeBaseView, ProvenanceView, RememberResult


def test_remember_result_includes_username_and_kb() -> None:
    result = RememberResult(
        memory_id="msg-1",
        status="already_exists",
        username="alice",
        kb_id="project-a",
    )
    assert result.kb_id == "project-a"
    assert result.username == "alice"


def test_knowledge_base_view_round_trip() -> None:
    view = KnowledgeBaseView(
        kb_id="project-a",
        name="Alpha",
        nams_conversation_id="conv-1",
        created_at=datetime.now(timezone.utc),
    )
    assert view.kb_id == "project-a"


def test_provenance_view() -> None:
    provenance = ProvenanceView(client_id="swift-otter-1", accepted_at="t")
    assert provenance.client_id == "swift-otter-1"
