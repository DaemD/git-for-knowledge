from app.auth import DisabledAuthTokenVerifier
from app.server import mcp


async def test_public_mcp_surface_uses_kb_id_tools() -> None:
    tools = await mcp.list_tools()
    assert [tool.name for tool in tools] == [
        "kb_list",
        "kb_create",
        "kb_delete",
        "kb_push",
        "kb_fetch",
        "kb_invite",
        "kb_members",
        "kb_revoke",
    ]


async def test_disabled_auth_accepts_sub_tokens() -> None:
    verifier = DisabledAuthTokenVerifier()
    token = await verifier.verify_token("sub:google-user-1")
    assert token is not None
    assert token.subject == "google-user-1"
