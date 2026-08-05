"""HTTP API for the grphly dashboard (Bearer Auth0 / dev tokens)."""

from __future__ import annotations

import json
from typing import Any, Callable, Coroutine

from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from app.auth import build_token_verifier
from app.config import Settings, get_settings


AsyncEndpoint = Callable[[Request], Coroutine[Any, Any, Response]]


def _json(payload: Any, status: int = 200) -> JSONResponse:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    return JSONResponse(payload, status_code=status)


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


async def _bearer_user(request: Request):
    from app.server import runtime

    if runtime.service is None:
        raise RuntimeError("service starting")

    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise PermissionError("Missing Bearer token")
    token = auth.split(" ", 1)[1].strip()
    if not token:
        raise PermissionError("Missing Bearer token")

    settings = get_settings()
    verifier = build_token_verifier(settings)
    access = await verifier.verify_token(token)
    if access is None or not access.subject:
        raise PermissionError("Invalid or expired token")

    return await runtime.service.ensure_user(
        access.subject,
        dict(access.claims or {}),
    )


def _with_auth(handler: AsyncEndpoint) -> AsyncEndpoint:
    async def wrapped(request: Request) -> Response:
        try:
            user = await _bearer_user(request)
            request.state.user = user
            return await handler(request)
        except PermissionError as exc:
            message = str(exc)
            status = (
                401
                if "token" in message.lower()
                or "authentication" in message.lower()
                or "bearer" in message.lower()
                else 403
            )
            return _error(message, status)
        except ValueError as exc:
            return _error(str(exc), 400)
        except RuntimeError as exc:
            return _error(str(exc), 503)
        except Exception as exc:  # noqa: BLE001
            return _error(str(exc), 500)

    return wrapped


async def api_me(request: Request) -> Response:
    from app.server import runtime

    assert runtime.service is not None
    result = await runtime.service.dashboard_me(request.state.user.id)
    return _json(result)


async def api_list_kbs(request: Request) -> Response:
    from app.server import runtime

    assert runtime.service is not None
    result = await runtime.service.list_knowledge_bases(request.state.user.id)
    return _json(result)


async def api_create_kb(request: Request) -> Response:
    from app.server import runtime

    assert runtime.service is not None
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _error("Invalid JSON body", 400)
    if not isinstance(body, dict):
        return _error("Expected JSON object", 400)
    kb_id = str(body.get("kb_id") or "").strip()
    name = body.get("name")
    name_str = str(name).strip() if name is not None else None
    result = await runtime.service.create_knowledge_base(
        request.state.user.id,
        kb_id,
        name_str,
    )
    return _json(result, status=201)


async def api_kb_detail(request: Request) -> Response:
    from app.server import runtime

    assert runtime.service is not None
    kb_id = request.path_params["kb_id"]
    result = await runtime.service.get_knowledge_base_detail(
        request.state.user.id,
        kb_id,
    )
    return _json(result)


async def api_kb_graph(request: Request) -> Response:
    from app.server import runtime

    assert runtime.service is not None
    kb_id = request.path_params["kb_id"]
    try:
        limit = int(request.query_params.get("limit") or "300")
    except ValueError:
        return _error("limit must be an integer", 400)
    result = await runtime.service.get_knowledge_base_graph(
        request.state.user.id,
        kb_id,
        limit=limit,
    )
    return _json(result)


async def api_kb_overview(request: Request) -> Response:
    from app.server import runtime

    assert runtime.service is not None
    kb_id = request.path_params["kb_id"]
    refresh = request.query_params.get("refresh", "").lower() in {
        "1",
        "true",
        "yes",
    }
    result = await runtime.service.get_knowledge_base_overview(
        request.state.user.id,
        kb_id,
        refresh=refresh,
    )
    return _json(result)


async def api_kb_entities(request: Request) -> Response:
    from app.server import runtime

    assert runtime.service is not None
    kb_id = request.path_params["kb_id"]
    q = request.query_params.get("q")
    try:
        limit = int(request.query_params.get("limit") or "200")
    except ValueError:
        return _error("limit must be an integer", 400)
    result = await runtime.service.list_knowledge_base_entities(
        request.state.user.id,
        kb_id,
        q=q,
        limit=limit,
    )
    return _json(result)


async def api_kb_entity(request: Request) -> Response:
    from app.server import runtime

    assert runtime.service is not None
    kb_id = request.path_params["kb_id"]
    entity_id = request.path_params["entity_id"]
    refresh = request.query_params.get("refresh", "").lower() in {
        "1",
        "true",
        "yes",
    }
    result = await runtime.service.get_knowledge_base_entity(
        request.state.user.id,
        kb_id,
        entity_id,
        refresh=refresh,
    )
    return _json(result)


async def api_invite(request: Request) -> Response:
    from app.server import runtime

    assert runtime.service is not None
    kb_id = request.path_params["kb_id"]
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _error("Invalid JSON body", 400)
    if not isinstance(body, dict):
        return _error("Expected JSON object", 400)
    email = str(body.get("email") or "").strip()
    role = str(body.get("role") or "write").strip()
    result = await runtime.service.invite_to_knowledge_base(
        request.state.user.id,
        kb_id,
        email,
        role,
    )
    return _json(result)


def dashboard_routes() -> list[Route]:
    return [
        Route("/api/v1/me", _with_auth(api_me), methods=["GET"]),
        Route("/api/v1/kbs", _with_auth(api_list_kbs), methods=["GET"]),
        Route("/api/v1/kbs", _with_auth(api_create_kb), methods=["POST"]),
        Route("/api/v1/kbs/{kb_id}", _with_auth(api_kb_detail), methods=["GET"]),
        Route(
            "/api/v1/kbs/{kb_id}/overview",
            _with_auth(api_kb_overview),
            methods=["GET"],
        ),
        Route(
            "/api/v1/kbs/{kb_id}/entities",
            _with_auth(api_kb_entities),
            methods=["GET"],
        ),
        Route(
            "/api/v1/kbs/{kb_id}/entities/{entity_id}",
            _with_auth(api_kb_entity),
            methods=["GET"],
        ),
        Route(
            "/api/v1/kbs/{kb_id}/graph",
            _with_auth(api_kb_graph),
            methods=["GET"],
        ),
        Route(
            "/api/v1/kbs/{kb_id}/invites",
            _with_auth(api_invite),
            methods=["POST"],
        ),
    ]


def apply_dashboard_cors(app: Any, settings: Settings) -> Any:
    origins = [
        origin.strip()
        for origin in (settings.dashboard_cors_origins or "").split(",")
        if origin.strip()
    ]
    if not origins:
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    return CORSMiddleware(
        app,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
