from types import SimpleNamespace

from app.nams import NamsStore


class FakeShortTerm:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def add_message(self, *args: object, **kwargs: object) -> SimpleNamespace:
        self.calls.append((args, kwargs))
        return SimpleNamespace(id="msg-1")


async def test_add_memory_sends_only_content_and_role_to_nams() -> None:
    short_term = FakeShortTerm()
    store = object.__new__(NamsStore)
    store._client = SimpleNamespace(short_term=short_term)

    async def ensure_conversation(_: str) -> str:
        return "conv-1"

    store.ensure_conversation = ensure_conversation

    memory_id, conversation_id = await store.add_memory(
        "kg_12345678",
        "Neo4j powers the shared graph.",
    )

    assert (memory_id, conversation_id) == ("msg-1", "conv-1")
    assert short_term.calls == [
        (
            ("conv-1", "user", "Neo4j powers the shared graph."),
            {},
        )
    ]
