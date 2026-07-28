"""Auth rejection and ownership isolation checks."""

from mcp.server.auth.provider import AccessToken

from app.auth import Auth0TokenVerifier, DisabledAuthTokenVerifier
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
