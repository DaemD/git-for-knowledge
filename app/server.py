import contextlib
from typing import Any

import uvicorn
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from app.auth import build_token_verifier, current_user_subject
from app.config import Settings, get_settings
from app.db import ControlStore, PostgresControlStore
from app.models import (
    CreateKnowledgeBaseResult,
    DeleteKnowledgeBaseResult,
    InviteToKnowledgeBaseResult,
    KnowledgeBaseListResult,
    KnowledgeBaseMembersResult,
    RecallResult,
    RememberResult,
    RevokeKnowledgeBaseAccessResult,
    UpgradeResult,
)
from app.nams import NamsStore
from app.oauth_proxy import (
    oauth_authorization_server_metadata,
    oauth_authorize,
    oauth_register,
    oauth_token,
)
from app.service import KnowledgeService
from app.stripe_billing import (
    BillingNotConfiguredError,
    construct_webhook_event,
    handle_stripe_webhook_event,
)


class Runtime:
    store: NamsStore | None = None
    control: ControlStore | None = None
    service: KnowledgeService | None = None


runtime = Runtime()


def _build_mcp(settings: Settings) -> FastMCP:
    issuer = settings.oauth_issuer_url or settings.public_base_url
    resource = AnyHttpUrl(str(settings.public_base_url).rstrip("/") + "/mcp")
    return FastMCP(
        name="grphly",
        instructions=(
            "grphly is persistent shared memory for Google-authenticated "
            "users. Logical knowledge bases are addressed by kb_id. "
            "Tools use git-style names: kb_list, kb_create, kb_push, kb_fetch, "
            "kb_invite, kb_members, kb_revoke, kb_delete, kb_upgrade. "
            "When the user says 'kb list' / 'kb push' / 'kb fetch' etc. in chat, "
            "call the matching grphly tool. Prefer kb_id from the project when omitted. "
            "New users get a 14-day trial; after that call kb_upgrade for Stripe Checkout. "
            "Identity comes from OAuth (never a client-supplied username). "
            "Entity search remains workspace-wide soft isolation."
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
async def kb_list() -> KnowledgeBaseListResult:
    """kb list — list knowledge bases you own or that are shared with you."""
    user = await _authenticated_user()
    return await _service().list_knowledge_bases(user.id)


@mcp.tool()
async def kb_create(
    kb_id: str,
    name: str | None = None,
) -> CreateKnowledgeBaseResult:
    """kb create <kb_id> [name] — create a knowledge base.

    kb_id is the stable identifier clients pass to kb_push / kb_fetch.
    """
    user = await _authenticated_user()
    return await _service().create_knowledge_base(user.id, kb_id, name)


@mcp.tool()
async def kb_delete(kb_id: str) -> DeleteKnowledgeBaseResult:
    """kb delete <kb_id> — delete a knowledge base you own."""
    user = await _authenticated_user()
    return await _service().delete_knowledge_base(user.id, kb_id)


@mcp.tool()
async def kb_push(
    kb_id: str,
    text: str,
    idempotency_key: str,
    client_id: str | None = None,
) -> RememberResult:
    """kb push <text> — store durable knowledge in a knowledge base.

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
async def kb_fetch(
    kb_id: str,
    question: str,
    limit: int = 5,
) -> RecallResult:
    """kb fetch <question> — retrieve knowledge from a knowledge base.

    Username comes from OAuth. Pass kb_id to choose which logical graph to hit.
    """
    user = await _authenticated_user()
    return await _service().recall(user.id, kb_id, question, limit)


@mcp.tool()
async def kb_invite(
    kb_id: str,
    email: str,
    role: str = "write",
) -> InviteToKnowledgeBaseResult:
    """kb invite <email> [read|write] — share a knowledge base by Google email.

    The invitee must sign in with that same email, then use the shared kb_id
    with kb_push / kb_fetch. role is 'read' or 'write'.
    """
    user = await _authenticated_user()
    return await _service().invite_to_knowledge_base(
        user.id,
        kb_id,
        email,
        role,
    )


@mcp.tool()
async def kb_members(
    kb_id: str,
) -> KnowledgeBaseMembersResult:
    """kb members — list owner, members, and pending invites for a KB."""
    user = await _authenticated_user()
    return await _service().list_knowledge_base_members(user.id, kb_id)


@mcp.tool()
async def kb_revoke(
    kb_id: str,
    email: str,
) -> RevokeKnowledgeBaseAccessResult:
    """kb revoke <email> — revoke invite or member access for a KB."""
    user = await _authenticated_user()
    return await _service().revoke_knowledge_base_access(user.id, kb_id, email)


@mcp.tool()
async def kb_upgrade() -> UpgradeResult:
    """kb upgrade — open Stripe Checkout to subscribe after the free trial.

    Always available (even when trial ended). Returns a checkout_url to open.
    """
    user = await _authenticated_user()
    return await _service().create_upgrade_checkout(user.id)


async def health(_: Any) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok" if runtime.service is not None else "starting",
            "service": "grphly",
            "backend": "nams",
            "endpoint": "/mcp",
            "auth": "oauth",
            "tenancy": "logical-kb-id",
        }
    )


async def billing_webhook(request: Request) -> Response:
    settings = get_settings()
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = construct_webhook_event(settings, payload, signature)
    except BillingNotConfiguredError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    except Exception as exc:  # noqa: BLE001 — Stripe signature errors
        return JSONResponse({"error": str(exc)}, status_code=400)

    if runtime.control is None:
        return JSONResponse({"error": "service starting"}, status_code=503)
    await handle_stripe_webhook_event(runtime.control, event)
    return JSONResponse({"received": True})


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
        Route("/authorize", oauth_authorize, methods=["GET"]),
        Route("/token", oauth_token, methods=["POST"]),
        Route("/register", oauth_register, methods=["POST"]),
        Route(
            "/.well-known/oauth-authorization-server",
            oauth_authorization_server_metadata,
            methods=["GET"],
        ),
        Route("/billing/webhook", billing_webhook, methods=["POST"]),
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
