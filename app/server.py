import contextlib
import secrets
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
from app.memory_writes import MemoryWriteStore
from app.models import RecallResult, RememberResult
from app.nams import NamsStore
from app.service import KnowledgeService, validate_knowledge_id


knowledge_scope: ContextVar[str | None] = ContextVar(
    "knowledge_scope",
    default=None,
)


class Runtime:
    store: NamsStore | None = None
    write_store: MemoryWriteStore | None = None
    service: KnowledgeService | None = None


runtime = Runtime()

_IDENTITY_ADJECTIVES = (
    "agile",
    "amber",
    "brisk",
    "bright",
    "calm",
    "clever",
    "cosmic",
    "curious",
    "daring",
    "dapper",
    "eager",
    "fuzzy",
    "gentle",
    "golden",
    "happy",
    "jolly",
    "keen",
    "lively",
    "lucky",
    "mighty",
    "nimble",
    "plucky",
    "quiet",
    "rapid",
    "roaming",
    "rosy",
    "shiny",
    "silver",
    "sleepy",
    "swift",
    "tidy",
    "vivid",
    "warm",
    "witty",
    "zesty",
)
_IDENTITY_NOUNS = (
    "badger",
    "beaver",
    "bison",
    "capybara",
    "chameleon",
    "corgi",
    "dolphin",
    "dragon",
    "falcon",
    "ferret",
    "gecko",
    "hedgehog",
    "heron",
    "jaguar",
    "koala",
    "lemur",
    "llama",
    "lynx",
    "manatee",
    "marmot",
    "narwhal",
    "otter",
    "panda",
    "puffin",
    "raven",
    "seahorse",
    "sloth",
    "sparrow",
    "tiger",
    "tortoise",
    "toucan",
    "walrus",
    "wombat",
    "yak",
)


def _new_client_id() -> str:
    """Generate a human-readable opaque installation identifier."""
    adjective = secrets.choice(_IDENTITY_ADJECTIVES)
    noun = secrets.choice(_IDENTITY_NOUNS)
    number = secrets.randbelow(1_000_000)
    return f"{adjective}-{noun}-{number:06d}"

mcp = FastMCP(
    name="Shared Knowledge Graph",
    instructions=(
        "This server is persistent shared memory. Before answering a question "
        "that may depend on stored knowledge, call recall. When the user asks "
        "to preserve durable knowledge, call remember. Use the context and "
        "sources returned by recall, and do not invent missing facts. Before "
        "the first remember call in a project, read .mcp-identity from the "
        "project root. If it is missing, call get_identity, save its returned "
        "value in .mcp-identity, then ensure .gitignore excludes it: append "
        ".mcp-identity if .gitignore exists without that line, otherwise create "
        ".gitignore containing only .mcp-identity. Use the saved value as "
        "client_id for every remember call. Never replace an existing "
        ".mcp-identity value. Clients without project-file access may omit "
        "client_id; it will be recorded as web-unattributed."
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
async def get_identity() -> str:
    """Generate a new opaque client identifier.

    Before the first remember call in a project or session, check for
    .mcp-identity in the project root. If it is absent, call this tool, save the
    returned string in .mcp-identity, then ensure .gitignore excludes it:
    append .mcp-identity if .gitignore exists without that line, otherwise
    create .gitignore containing only .mcp-identity. Always read .mcp-identity
    when present and pass its content as client_id on every remember call.
    Never regenerate an identity when .mcp-identity exists.
    """
    return _new_client_id()


@mcp.tool()
async def remember(
    text: str,
    idempotency_key: str,
    client_id: str | None = None,
) -> RememberResult:
    """Remember durable natural-language knowledge for other AI clients.

    Use this only when the user asks to preserve stable facts, decisions,
    architecture, terminology, rationale, or changes. NAMS stores the message
    and asynchronously updates the shared graph. Before the first remember
    call in a project or session, check for .mcp-identity in the project root.
    If it is absent, call get_identity, save the returned string in
    .mcp-identity, then ensure .gitignore excludes it: append .mcp-identity if
    .gitignore exists without that line, otherwise create .gitignore containing
    only .mcp-identity. Always read .mcp-identity when present and pass its
    content as client_id on every remember call. Never regenerate an identity
    when .mcp-identity exists.
    Clients without project-file access may omit client_id; those messages are
    recorded as web-unattributed.
    Also provide a stable, client-generated idempotency_key (normally a UUID)
    that is reused on retries. The server records the UTC timestamp; do not
    provide one.
    """
    return await _service().remember(
        _knowledge_id(),
        text,
        client_id,
        idempotency_key,
    )


@mcp.tool()
async def recall(
    question: str,
    limit: int = 5,
) -> RecallResult:
    """Recall relevant shared memory for answering a question.

    This returns context, entities, relationships, and sources. Use those
    memories to formulate the answer. If found is false, say that shared memory
    does not contain enough information rather than guessing. Before the first
    remember call in a project or session, check for .mcp-identity in the
    project root. If it is absent, call get_identity, save the returned string
    in .mcp-identity, then ensure .gitignore excludes it: append .mcp-identity
    if .gitignore exists without that line, otherwise create .gitignore
    containing only .mcp-identity. Always read .mcp-identity when present and
    pass its content as client_id on every remember call. Never regenerate an
    identity when .mcp-identity exists.
    Clients without project-file access may omit client_id; those messages are
    recorded as web-unattributed.
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
    write_store = MemoryWriteStore()
    runtime.store = store
    runtime.write_store = write_store
    runtime.service = KnowledgeService(
        store,
        write_store,
        settings.effective_knowledge_id,
    )
    try:
        async with mcp.session_manager.run():
            yield
    finally:
        runtime.service = None
        runtime.write_store = None
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
