import hashlib
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    memory_api_key: SecretStr
    memory_endpoint: str = "https://memory.neo4jlabs.com/v1"
    memory_workspace_id: str | None = None
    knowledge_id: str | None = None

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    mcp_base_path: str = "/mcp"

    @property
    def effective_knowledge_id(self) -> str:
        if self.knowledge_id:
            return self.knowledge_id
        key = self.memory_api_key.get_secret_value().encode("utf-8")
        digest = hashlib.sha256(key).hexdigest()[:32]
        return f"kg_{digest}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
