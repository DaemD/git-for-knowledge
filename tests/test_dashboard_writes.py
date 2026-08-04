import pytest

from app.db import InMemoryControlStore


@pytest.mark.asyncio
async def test_list_recent_writes_orders_newest_first():
    store = InMemoryControlStore()
    await store.connect()
    user = await store.upsert_user("u1", email="a@example.com")
    graph = await store.create_graph(user.id, "kb1", "KB One", "conv-1")

    await store.begin_write(
        idempotency_key="k1",
        user_id=user.id,
        graph_id=graph.id,
        client_id="cursor",
        content_hash="h1",
        accepted_at="2026-01-01T00:00:00+00:00",
    )
    await store.mark_completed("k1", "m1", "2026-01-01T00:00:01+00:00")
    await store.begin_write(
        idempotency_key="k2",
        user_id=user.id,
        graph_id=graph.id,
        client_id="claude",
        content_hash="h2",
        accepted_at="2026-01-02T00:00:00+00:00",
    )
    await store.mark_completed("k2", "m2", "2026-01-02T00:00:01+00:00")

    recent = await store.list_recent_writes(graph.id, limit=10)
    assert [item.nams_message_id for item in recent] == ["m2", "m1"]
    assert await store.count_writes(graph.id) == 2
