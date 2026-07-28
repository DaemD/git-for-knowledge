from __future__ import annotations

from functools import lru_cache

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Shared NAMS workspace for the whole MVP deployment.
    memory_api_key: SecretStr
    memory_endpoint: str = "https://memory.neo4jlabs.com/v1"
    memory_workspace_id: str = Field(
        ...,
        description="Single shared NAMS workspace id used by all users",
    )

    # PostgreSQL control plane (users, graphs, sessions, memory_writes).
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/knowledge",
        description="asyncpg-compatible PostgreSQL URL",
    )

    # Auth0 with Google as the upstream identity provider.
    oauth_issuer_url: AnyHttpUrl | None = None
    oauth_audience: str = ""
    oauth_jwks_url: str | None = None
    oauth_required_scopes: str = ""
    public_base_url: AnyHttpUrl = Field(
        default=AnyHttpUrl("http://127.0.0.1:8000"),
    )

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    mcp_base_path: str = "/mcp"

    # Dev-only: accept Authorization Bearer tokens shaped as sub:<user-id>.
    auth_disabled: bool = False

    # Optional invite emails via Resend (https://resend.com).
    invite_email_enabled: bool = False
    resend_api_key: SecretStr | None = None
    email_from: str = ""
    invite_docs_url: str = ""

    @property
    def required_scopes(self) -> list[str]:
        return [scope for scope in self.oauth_required_scopes.split() if scope]

    @property
    def jwks_url(self) -> str:
        if self.oauth_jwks_url:
            return self.oauth_jwks_url
        if self.oauth_issuer_url is None:
            raise ValueError("oauth_issuer_url is required when auth is enabled")
        issuer = str(self.oauth_issuer_url).rstrip("/")
        return f"{issuer}/.well-known/jwks.json"

    @model_validator(mode="after")
    def validate_auth_settings(self) -> Settings:
        if not self.memory_workspace_id.strip():
            raise ValueError("MEMORY_WORKSPACE_ID is required")
        if self.auth_disabled:
            return self
        if self.oauth_issuer_url is None:
            raise ValueError(
                "OAUTH_ISSUER_URL is required unless AUTH_DISABLED=true"
            )
        if not self.oauth_audience:
            raise ValueError(
                "OAUTH_AUDIENCE is required unless AUTH_DISABLED=true"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
