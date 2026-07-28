from app.auth import DisabledAuthTokenVerifier
from app.server import mcp


async def test_public_mcp_surface_uses_kb_id_tools() -> None:
    tools = await mcp.list_tools()
    assert [tool.name for tool in tools] == [
        "list_knowledge_bases",
        "create_knowledge_base",
        "delete_knowledge_base",
        "remember",
        "recall",
        "invite_to_knowledge_base",
        "list_knowledge_base_members",
        "revoke_knowledge_base_access",
    ]


async def test_disabled_auth_accepts_sub_tokens() -> None:
    verifier = DisabledAuthTokenVerifier()
    token = await verifier.verify_token("sub:google-user-1")
    assert token is not None
    assert token.subject == "google-user-1"
