import contextlib
import secrets
from typing import Any

import uvicorn
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.auth import build_token_verifier, current_user_subject
from app.config import Settings, get_settings
from app.db import ControlStore, PostgresControlStore
from app.models import (
    CreateKnowledgeBaseResult,
    KnowledgeBaseListResult,
    RecallResult,
    RememberResult,
)
from app.nams import NamsStore
from app.service import KnowledgeService


class Runtime:
    store: NamsStore | None = None
    control: ControlStore | None = None
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


def _build_mcp(settings: Settings) -> FastMCP:
    issuer = settings.oauth_issuer_url or settings.public_base_url
    resource = AnyHttpUrl(str(settings.public_base_url).rstrip("/") + "/mcp")
    return FastMCP(
        name="Shared Knowledge Graph",
        instructions=(
            "This server is persistent shared memory for Google-authenticated "
            "users. Logical knowledge bases live in one shared NAMS workspace "
            "and are addressed by kb_id. The authenticated user identity is "
            "taken from OAuth (never trust a client-supplied username). Before "
            "answering a memory-dependent question, call recall with kb_id. "
            "When the user asks to preserve durable knowledge, call remember "
            "with kb_id. Use list_knowledge_bases / create_knowledge_base to "
            "manage KBs. Before the first remember call in a project, read "
            ".mcp-identity; if missing, call get_identity and save it. Pass "
            "that value as client_id on remember. Entity search remains "
            "workspace-wide soft isolation."
        ),
        stateless_http=True,
        json_response=True,
        streamable_http_path="/mcp",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        ),
        auth=AuthSettings(
            issuer_url=issuer,
            resource_server_url=resource,
            required_scopes=settings.required_scopes or None,
        ),
        token_verifier=build_token_verifier(settings),
    )


mcp = _build_mcp(get_settings())


def _service() -> KnowledgeService:
    if runtime.service is None:
        raise RuntimeError("Knowledge service has not finished starting")
    return runtime.service


async def _authenticated_user():
    subject, claims = current_user_subject()
    return await _service().ensure_user(subject, claims)


@mcp.tool()
async def get_identity() -> str:
    """Generate a new opaque client identifier for local install provenance.

    Before the first remember call in a project, check for .mcp-identity. If
    absent, call this tool, save the returned string, and gitignore it. Always
    pass the saved value as client_id on remember. Never regenerate when
    .mcp-identity already exists.
    """
    return _new_client_id()


@mcp.tool()
async def list_knowledge_bases() -> KnowledgeBaseListResult:
    """List knowledge bases owned by the authenticated user."""
    user = await _authenticated_user()
    return await _service().list_knowledge_bases(user.id)


@mcp.tool()
async def create_knowledge_base(
    kb_id: str,
    name: str | None = None,
) -> CreateKnowledgeBaseResult:
    """Create a logical knowledge base for the authenticated user.

    kb_id is the stable identifier clients pass to remember/recall.
    """
    user = await _authenticated_user()
    return await _service().create_knowledge_base(user.id, kb_id, name)


@mcp.tool()
async def remember(
    kb_id: str,
    text: str,
    idempotency_key: str,
    client_id: str | None = None,
) -> RememberResult:
    """Remember durable text in the authenticated user's knowledge base.

    Username comes from OAuth. Pass kb_id to choose which logical graph to hit.
    """
    user = await _authenticated_user()
    return await _service().remember(
        user.id,
        kb_id,
        text,
        idempotency_key=idempotency_key,
        client_id=client_id,
    )


@mcp.tool()
async def recall(
    kb_id: str,
    question: str,
    limit: int = 5,
) -> RecallResult:
    """Recall memory from the authenticated user's knowledge base.

    Username comes from OAuth. Pass kb_id to choose which logical graph to hit.
    """
    user = await _authenticated_user()
    return await _service().recall(user.id, kb_id, question, limit)


async def health(_: Any) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok" if runtime.service is not None else "starting",
            "service": "shared-knowledge-mcp",
            "backend": "nams",
            "endpoint": "/mcp",
            "auth": "oauth",
            "tenancy": "logical-kb-id",
        }
    )


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    settings = get_settings()
    store = NamsStore(settings)
    control = PostgresControlStore(settings.database_url)
    await store.connect()
    await control.connect()
    runtime.store = store
    runtime.control = control
    runtime.service = KnowledgeService(store, control)
    try:
        async with mcp.session_manager.run():
            yield
    finally:
        runtime.service = None
        runtime.control = None
        runtime.store = None
        await control.close()
        await store.close()


mcp_http_app = mcp.streamable_http_app()

app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Mount("/", app=mcp_http_app),
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
