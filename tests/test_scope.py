import re

from app.server import KnowledgeScopeMiddleware, get_identity, knowledge_scope, mcp


async def test_public_mcp_surface_has_identity_remember_and_recall() -> None:
    tools = await mcp.list_tools()
    assert [tool.name for tool in tools] == ["get_identity", "remember", "recall"]


async def test_get_identity_returns_a_human_readable_client_id() -> None:
    client_id = await get_identity()

    assert re.fullmatch(r"[a-z]+-[a-z]+-\d{6}", client_id)


async def test_scope_middleware_binds_knowledge_id_and_rewrites_path() -> None:
    observed: dict[str, str | None] = {}

    async def child(scope, receive, send) -> None:
        observed["knowledge_id"] = knowledge_scope.get()
        observed["path"] = scope["path"]
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    messages: list[dict] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    middleware = KnowledgeScopeMiddleware(child)
    await middleware(
        {
            "type": "http",
            "method": "POST",
            "path": "/mcp/kg_12345678",
            "raw_path": b"/mcp/kg_12345678",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 123),
            "scheme": "http",
            "http_version": "1.1",
            "root_path": "",
        },
        receive,
        send,
    )

    assert observed == {"knowledge_id": "kg_12345678", "path": "/"}
    assert messages[0]["status"] == 200
    assert knowledge_scope.get() is None


async def test_scope_middleware_rejects_invalid_knowledge_id() -> None:
    called = False

    async def child(scope, receive, send) -> None:
        nonlocal called
        called = True

    messages: list[dict] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    middleware = KnowledgeScopeMiddleware(child)
    await middleware(
        {
            "type": "http",
            "method": "POST",
            "path": "/mcp/not-valid",
            "raw_path": b"/mcp/not-valid",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 123),
            "scheme": "http",
            "http_version": "1.1",
            "root_path": "",
        },
        receive,
        send,
    )

    assert not called
    assert messages[0]["status"] == 400
