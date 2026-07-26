from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    neo4j_uri: str
    neo4j_username: str = "neo4j"
    neo4j_password: str
    neo4j_database: str = "neo4j"

    openai_api_key: str
    openai_base_url: str | None = None
    openai_model: str = "gpt-5-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    mcp_base_path: str = "/mcp"


@lru_cache
def get_settings() -> Settings:
    return Settings()
