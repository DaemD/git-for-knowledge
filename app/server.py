import contextlib
import json
import asyncio
import logging
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
from app.dashboard_api import apply_dashboard_cors, dashboard_routes
from app.lemon_billing import (
    BillingNotConfiguredError,
    handle_lemon_webhook_event,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)


class Runtime:
    store: NamsStore | None = None
    control: ControlStore | None = None
    service: KnowledgeService | None = None
    nams_ready: bool = False


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
            "New users get a 14-day trial; after that call kb_upgrade for Lemon Squeezy checkout. "
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
    """kb upgrade — open Lemon Squeezy checkout to subscribe after the free trial.

    Always available (even when trial ended). Returns a checkout_url to open.
    """
    user = await _authenticated_user()
    return await _service().create_upgrade_checkout(user.id)


async def health(_: Any) -> JSONResponse:
    nams_ok = runtime.nams_ready and (
        runtime.store is not None and runtime.store.is_connected
    )
    ready = runtime.service is not None and runtime.control is not None
    return JSONResponse(
        {
            "status": "ok" if ready else "starting",
            "nams": "ok" if nams_ok else "unavailable",
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
    signature = request.headers.get("x-signature", "")
    try:
        verify_webhook_signature(settings, payload, signature)
        event = json.loads(payload.decode("utf-8"))
    except BillingNotConfiguredError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=400)

    if runtime.control is None:
        return JSONResponse({"error": "service starting"}, status_code=503)
    await handle_lemon_webhook_event(runtime.control, event)
    return JSONResponse({"received": True})


async def _nams_reconnect_loop(store: NamsStore) -> None:
    """Keep trying NAMS until it comes back after a cold-start outage."""
    delay = 15.0
    while not store.is_connected:
        logger.warning("Retrying NAMS connection in background…")
        try:
            await store.ensure_connected()
            runtime.nams_ready = True
            logger.info("NAMS reconnected")
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("NAMS background reconnect error: %s", exc)
        await asyncio.sleep(delay)
        delay = min(delay * 1.2, 60.0)


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    settings = get_settings()
    store = NamsStore(settings)
    control = PostgresControlStore(settings.database_url)
    reconnect_task: asyncio.Task[None] | None = None

    # Postgres is ours — fail hard. NAMS is upstream Neo4j Labs — brief retry then degrade.
    await control.connect()
    # Keep startup short so Railway /health can bind quickly; background loop continues.
    nams_ok = await store.connect_with_retry(
        attempts=5,
        base_delay=2.0,
        max_delay=8.0,
    )
    runtime.nams_ready = nams_ok
    if not nams_ok:
        logger.error(
            "NAMS unavailable after retries (database_unavailable?). "
            "Starting API in degraded mode; memory tools will fail until NAMS recovers."
        )
        reconnect_task = asyncio.create_task(_nams_reconnect_loop(store))

    runtime.store = store
    runtime.control = control
    runtime.service = KnowledgeService(store, control)
    try:
        async with mcp.session_manager.run():
            yield
    finally:
        if reconnect_task is not None:
            reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reconnect_task
        runtime.service = None
        runtime.control = None
        runtime.store = None
        runtime.nams_ready = False
        await control.close()
        await store.close()


mcp_http_app = mcp.streamable_http_app()

_settings = get_settings()
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
        *dashboard_routes(),
        Mount("/", app=mcp_http_app),
    ],
    lifespan=lifespan,
)
app = apply_dashboard_cors(app, _settings)


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
