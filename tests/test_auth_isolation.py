"""Auth rejection and ownership isolation checks."""

from unittest.mock import AsyncMock, patch

from mcp.server.auth.provider import AccessToken

from app.auth import Auth0TokenVerifier, DisabledAuthTokenVerifier, resolve_user_profile
from app.config import Settings
from app.db import InMemoryControlStore
from app.service import KnowledgeService


class FakeNamsStore:
    workspace_id = "ws-shared"

    async def create_conversation(self, name, *, metadata=None) -> str:
        return f"conv-{name}"

    async def add_memory(self, conversation_id, text) -> str:
        return "msg-1"

    async def get_context(self, conversation_id, query) -> str:
        return ""

    async def list_messages(self, conversation_id, *, limit=100):
        return []

    async def search_entities(self, query, limit):
        return []

    async def get_relationships(self, entity_id):
        return []

    async def get_entity_history(self, entity_id):
        return []


async def test_oauth_verifier_rejects_garbage_token() -> None:
    settings = Settings(
        memory_api_key="x",
        memory_workspace_id="ws-shared",
        auth_disabled=False,
        oauth_issuer_url="https://example.auth0.com/",
        oauth_audience="https://api.example",
        oauth_jwks_url="https://example.auth0.com/.well-known/jwks.json",
        public_base_url="https://app.example",
    )
    verifier = Auth0TokenVerifier(settings)
    assert await verifier.verify_token("not-a-jwt") is None


async def test_disabled_token_shapes_access_token() -> None:
    token = await DisabledAuthTokenVerifier().verify_token("sub:dev-user")
    assert isinstance(token, AccessToken)
    assert token.subject == "dev-user"


async def test_bob_cannot_hit_alice_kb_id() -> None:
    service = KnowledgeService(FakeNamsStore(), InMemoryControlStore())
    alice = await service.ensure_user("alice", {"email": "alice@example.com"})
    bob = await service.ensure_user("bob", {"email": "bob@example.com"})
    await service.create_knowledge_base(alice.id, "private")

    try:
        await service.recall(bob.id, "private", "anything")
        raised = False
    except PermissionError:
        raised = True
    assert raised


async def test_resolve_user_profile_fetches_email_from_userinfo() -> None:
    settings = Settings(
        memory_api_key="x",
        memory_workspace_id="ws-shared",
        auth_disabled=False,
        oauth_issuer_url="https://dev-xx4jrebrryos1jre.us.auth0.com/",
        oauth_audience="https://api.example",
        public_base_url="https://app.example",
    )
    with (
        patch("app.auth.get_settings", return_value=settings),
        patch("app.auth._fetch_userinfo", new_callable=AsyncMock) as fetch,
    ):
        fetch.return_value = {"email": "alice@example.com", "name": "Alice"}
        email, name = await resolve_user_profile({}, "token-123")
    assert email == "alice@example.com"
    assert name == "Alice"
    fetch.assert_awaited_once_with(
        "token-123",
        "https://dev-xx4jrebrryos1jre.us.auth0.com/",
    )
