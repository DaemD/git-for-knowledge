import contextlib
from contextvars import ContextVar
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings
from app.graph import GraphRepository
from app.llm import KnowledgeLLM
from app.models import (
    EntityResult,
    NeighborhoodResult,
    PushMemoryResult,
    SearchResult,
)
from app.service import KnowledgeService, validate_knowledge_id


knowledge_scope: ContextVar[str | None] = ContextVar(
    "knowledge_scope",
    default=None,
)


class Runtime:
    graph: GraphRepository | None = None
    service: KnowledgeService | None = None


runtime = Runtime()

mcp = FastMCP(
    name="Shared Knowledge Graph",
    instructions=(
        "This server is the persistent memory for the knowledge base in its URL. "
        "Before answering questions about the project, call "
        "get_relevant_context. When the user states durable project knowledge, "
        "call push_memory. Base answers on returned claims and evidence; do not "
        "invent missing facts."
    ),
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
)


def _service() -> KnowledgeService:
    if runtime.service is None:
        raise RuntimeError("Knowledge service has not finished starting")
    return runtime.service


def _knowledge_id(*, allow_bootstrap: bool = False) -> str:
    knowledge_id = knowledge_scope.get()
    if knowledge_id is None:
        raise ValueError("Missing knowledge ID in the MCP URL")
    if allow_bootstrap and knowledge_id == "bootstrap":
        return knowledge_id
    return validate_knowledge_id(knowledge_id)


@mcp.tool()
async def create_knowledge_base() -> dict[str, str]:
    """Create an unguessable knowledge ID from the /mcp/bootstrap endpoint."""
    if _knowledge_id(allow_bootstrap=True) != "bootstrap":
        raise ValueError("Connect to /mcp/bootstrap to create a knowledge base")
    knowledge_id = await _service().create_knowledge_base()
    return {
        "knowledge_id": knowledge_id,
        "mcp_path": f"/mcp/{knowledge_id}",
    }


@mcp.tool()
async def push_memory(
    text: str,
    source: str = "user",
    idempotency_key: str | None = None,
) -> PushMemoryResult:
    """Store durable natural-language knowledge in this URL's knowledge base.

    Use this when the user states stable facts, decisions, architecture,
    terminology, rationale, or changes that should be available to other AIs.
    The server extracts and resolves entities while retaining the original text
    as evidence.
    """
    return await _service().push_memory(
        _knowledge_id(),
        text,
        source,
        idempotency_key,
    )


@mcp.tool()
async def get_relevant_context(
    query: str,
    limit: int = 5,
) -> SearchResult:
    """Retrieve evidence-backed context before answering a project question.

    Call this for every question that may depend on shared project knowledge.
    If insufficient_evidence is true, say that the graph does not contain enough
    evidence rather than guessing.
    """
    return await _service().search(_knowledge_id(), query, limit)


@mcp.tool()
async def search_knowledge(query: str, limit: int = 5) -> SearchResult:
    """Search this knowledge graph for entities, claims, and source evidence."""
    return await _service().search(_knowledge_id(), query, limit)


@mcp.tool()
async def get_entity(entity_id: str) -> EntityResult:
    """Retrieve one entity with its aliases, claims, and supporting evidence."""
    return await _service().get_entity(_knowledge_id(), entity_id)


@mcp.tool()
async def get_neighborhood(
    entity_id: str,
    depth: int = 1,
    limit: int = 50,
) -> NeighborhoodResult:
    """Traverse one or two bounded claim hops around an entity."""
    return await _service().get_neighborhood(
        _knowledge_id(),
        entity_id,
        depth,
        limit,
    )


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
        if knowledge_id != "bootstrap":
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
        }
    )


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    settings = get_settings()
    graph = GraphRepository(settings)
    llm = KnowledgeLLM(settings)
    await graph.initialize()
    runtime.graph = graph
    runtime.service = KnowledgeService(graph, llm)
    try:
        async with mcp.session_manager.run():
            yield
    finally:
        runtime.service = None
        runtime.graph = None
        await graph.close()


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
