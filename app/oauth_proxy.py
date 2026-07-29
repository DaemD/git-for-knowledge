"""Root OAuth routes so Claude.ai can talk to Auth0.

Claude.ai often ignores authorization_server metadata and hits
/authorize, /token, and /register on the MCP host instead of Auth0.
Proxy those paths to the configured OAuth issuer.
"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.config import get_settings


def _issuer() -> str:
    settings = get_settings()
    if settings.oauth_issuer_url is None:
        raise RuntimeError("OAUTH_ISSUER_URL is required for OAuth proxy routes")
    return str(settings.oauth_issuer_url).rstrip("/")


async def oauth_authorize(request: Request) -> Response:
    """GET /authorize → Auth0 /authorize (Claude.ai compatibility)."""
    target = f"{_issuer()}/authorize"
    query = request.url.query
    url = f"{target}?{query}" if query else target
    return RedirectResponse(url, status_code=302)


async def oauth_token(request: Request) -> Response:
    """POST /token → Auth0 /oauth/token."""
    body = await request.body()
    content_type = request.headers.get("content-type", "application/x-www-form-urlencoded")
    async with httpx.AsyncClient(timeout=30.0) as client:
        upstream = await client.post(
            f"{_issuer()}/oauth/token",
            content=body,
            headers={"content-type": content_type},
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


async def oauth_register(request: Request) -> Response:
    """POST /register → Auth0 OIDC DCR endpoint when enabled."""
    body = await request.body()
    content_type = request.headers.get("content-type", "application/json")
    async with httpx.AsyncClient(timeout=30.0) as client:
        upstream = await client.post(
            f"{_issuer()}/oidc/register",
            content=body,
            headers={"content-type": content_type},
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


async def oauth_authorization_server_metadata(_: Request) -> JSONResponse:
    """Advertise Auth0 endpoints at the MCP host root for buggy clients."""
    issuer = _issuer()
    return JSONResponse(
        {
            "issuer": f"{issuer}/",
            "authorization_endpoint": f"{issuer}/authorize",
            "token_endpoint": f"{issuer}/oauth/token",
            "registration_endpoint": f"{issuer}/oidc/register",
            "jwks_uri": f"{issuer}/.well-known/jwks.json",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
                "none",
            ],
        }
    )


def auth0_authorize_url(query_params: dict[str, str]) -> str:
    return f"{_issuer()}/authorize?{urlencode(query_params)}"
