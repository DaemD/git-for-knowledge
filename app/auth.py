"""OAuth token verification for Auth0 (Google social login)."""

from __future__ import annotations

import time
from typing import Any

import jwt
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken, TokenVerifier

from app.config import Settings


class Auth0TokenVerifier(TokenVerifier):
    """Validate Auth0-issued JWTs used by Cursor/Claude MCP clients.

    Configure Auth0 with Google as a social connection. The verified ``sub``
    claim is the durable product user identity.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._jwks = PyJWKClient(settings.jwks_url, cache_keys=True)

    async def verify_token(self, token: str) -> AccessToken | None:
        issuer = str(self._settings.oauth_issuer_url).rstrip("/")
        claims = await self._decode(token, f"{issuer}/")
        if claims is None:
            claims = await self._decode(token, issuer)
        if claims is None:
            return None

        scopes = _extract_scopes(claims)
        required = set(self._settings.required_scopes)
        if required and not required.issubset(scopes):
            return None

        subject = str(claims.get("sub") or "")
        if not subject:
            return None

        return AccessToken(
            token=token,
            client_id=str(claims.get("azp") or claims.get("client_id") or subject),
            scopes=sorted(scopes),
            expires_at=int(claims["exp"]) if claims.get("exp") else None,
            resource=str(self._settings.public_base_url),
            subject=subject,
            claims=dict(claims),
        )

    async def _decode(self, token: str, issuer: str) -> dict[str, Any] | None:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._settings.oauth_audience,
                issuer=issuer,
                options={"require": ["exp", "sub"]},
            )
        except jwt.PyJWTError:
            return None


class DisabledAuthTokenVerifier(TokenVerifier):
    """Development verifier that accepts opaque tokens shaped as ``sub:<id>``."""

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token.startswith("sub:"):
            return None
        subject = token.removeprefix("sub:").strip()
        if not subject:
            return None
        return AccessToken(
            token=token,
            client_id=subject,
            scopes=["openid", "profile", "email"],
            expires_at=int(time.time()) + 3600,
            subject=subject,
            claims={"sub": subject, "email": f"{subject}@example.com"},
        )


def build_token_verifier(settings: Settings) -> TokenVerifier:
    if settings.auth_disabled:
        return DisabledAuthTokenVerifier()
    return Auth0TokenVerifier(settings)


def current_user_subject() -> tuple[str, dict[str, Any]]:
    """Return ``(subject, claims)`` for the authenticated MCP request."""
    from mcp.server.auth.middleware.auth_context import get_access_token

    token = get_access_token()
    if token is None or not token.subject:
        raise PermissionError("Authentication required")
    return token.subject, dict(token.claims or {})


def _extract_scopes(claims: dict[str, Any]) -> set[str]:
    scopes: set[str] = set()
    scope_claim = claims.get("scope")
    if isinstance(scope_claim, str):
        scopes.update(part for part in scope_claim.split() if part)
    permissions = claims.get("permissions")
    if isinstance(permissions, list):
        scopes.update(str(item) for item in permissions)
    return scopes
