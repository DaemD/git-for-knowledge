import contextlib
from contextvars import ContextVar
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings
from app.models import RecallResult, RememberResult
from app.nams import NamsStore
from app.service import KnowledgeService, validate_knowledge_id


knowledge_scope: ContextVar[str | None] = ContextVar(
    "knowledge_scope",
    default=None,
)


class Runtime:
    store: NamsStore | None = None
    service: KnowledgeService | None = None


runtime = Runtime()

mcp = FastMCP(
    name="Shared Knowledge Graph",
    instructions=(
        "This server is persistent shared memory. Before answering a question "
        "that may depend on stored knowledge, call recall. When the user asks "
        "to preserve durable knowledge, call remember. Use the context and "
        "sources returned by recall, and do not invent missing facts."
    ),
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    # Railway terminates TLS and validates the public host at its edge. The MCP
    # SDK's localhost-oriented default otherwise rejects Railway's forwarded Host
    # header with HTTP 421 before a tool request reaches this application.
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


def _service() -> KnowledgeService:
    if runtime.service is None:
        raise RuntimeError("Knowledge service has not finished starting")
    return runtime.service


def _knowledge_id() -> str:
    knowledge_id = knowledge_scope.get()
    if knowledge_id is None:
        raise ValueError("Missing knowledge ID in the MCP URL")
    return validate_knowledge_id(knowledge_id)


@mcp.tool()
async def remember(text: str) -> RememberResult:
    """Remember durable natural-language knowledge for other AI clients.

    Use this only when the user asks to preserve stable facts, decisions,
    architecture, terminology, rationale, or changes. NAMS stores the message
    and asynchronously updates the shared graph.
    """
    return await _service().remember(_knowledge_id(), text)


@mcp.tool()
async def recall(
    question: str,
    limit: int = 5,
) -> RecallResult:
    """Recall relevant shared memory for answering a question.

    This returns context, entities, relationships, and sources. Use those
    memories to formulate the answer. If found is false, say that shared memory
    does not contain enough information rather than guessing.
    """
    return await _service().recall(_knowledge_id(), question, limit)


class KnowledgeScopeMiddleware:
    """Bind /mcp/{knowledge_id} to the current stateless MCP request."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        parts = [part for part in path.split("/") if part]
        if len(parts) != 2 or parts[0] != "mcp":
            response = JSONResponse({"error": "Not found"}, status_code=404)
            await response(scope, receive, send)
            return

        knowledge_id = parts[1]
        try:
            validate_knowledge_id(knowledge_id)
        except ValueError as exc:
            response = JSONResponse({"error": str(exc)}, status_code=400)
            await response(scope, receive, send)
            return

        token = knowledge_scope.set(knowledge_id)
        child_scope: dict[str, Any] = dict(scope)
        child_scope["path"] = "/"
        child_scope["raw_path"] = b"/"
        child_scope["root_path"] = path
        try:
            await self._app(child_scope, receive, send)
        finally:
            knowledge_scope.reset(token)


async def health(_: Any) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok" if runtime.service is not None else "starting",
            "service": "shared-knowledge-mcp",
            "backend": "nams",
        }
    )


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    settings = get_settings()
    store = NamsStore(settings)
    await store.connect()
    runtime.store = store
    runtime.service = KnowledgeService(store, settings.effective_knowledge_id)
    try:
        async with mcp.session_manager.run():
            yield
    finally:
        runtime.service = None
        runtime.store = None
        await store.close()


scoped_mcp_app = KnowledgeScopeMiddleware(mcp.streamable_http_app())

app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Mount("/", app=scoped_mcp_app),
    ],
    lifespan=lifespan,
)


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.server:app",
        host=settings.host,
        port=settings.port,
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
