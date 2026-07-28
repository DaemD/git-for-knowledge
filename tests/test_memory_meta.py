from app.memory_meta import (
    build_memory_metadata,
    metadata_matches_kb,
    parse_memory_meta,
    stamp_memory_text,
    strip_memory_meta,
)


def test_stamp_and_parse_round_trip() -> None:
    meta = build_memory_metadata(
        kb_id="project-a",
        kb_name="Alpha",
        owner_sub="alice",
        owner_email="alice@example.com",
        writer_sub="bob",
        writer_email="bob@example.com",
        graph_id="graph_1",
        nams_conversation_id="conv_1",
    )
    stamped = stamp_memory_text("Neo4j powers the graph.", meta)
    assert "Neo4j powers the graph." in stamped
    assert 'kb_id="project-a"' in stamped
    parsed = parse_memory_meta(stamped)
    assert parsed["kb_id"] == "project-a"
    assert parsed["owner_email"] == "alice@example.com"
    assert parsed["writer_sub"] == "bob"
    assert strip_memory_meta(stamped) == "Neo4j powers the graph."
    assert metadata_matches_kb(stamped, "project-a", "graph_1")
    assert not metadata_matches_kb(stamped, "other", None)
