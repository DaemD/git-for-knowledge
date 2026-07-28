from unittest.mock import AsyncMock, patch

from app.config import Settings
from app.email_service import send_kb_invite_email


def _settings(**overrides) -> Settings:
    values = {
        "memory_api_key": "x",
        "memory_workspace_id": "ws",
        "auth_disabled": True,
        "public_base_url": "https://app.example",
        "invite_email_enabled": True,
        "resend_api_key": "re_test",
        "email_from": "Shared <noreply@example.com>",
        "invite_docs_url": "https://docs.example/setup",
    }
    values.update(overrides)
    return Settings(**values)


async def test_invite_email_disabled_by_default() -> None:
    settings = _settings(invite_email_enabled=False)
    result = await send_kb_invite_email(
        settings,
        to_email="alice@example.com",
        kb_id="team",
        kb_name="Team",
        role="write",
        inviter_email="bob@example.com",
        inviter_name="Bob",
    )
    assert result.sent is False
    assert result.error == "invite email disabled"


async def test_invite_email_sends_via_resend() -> None:
    settings = _settings()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "ok"

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_response

    with patch("app.email_service.httpx.AsyncClient", return_value=mock_client):
        result = await send_kb_invite_email(
            settings,
            to_email="alice@example.com",
            kb_id="team",
            kb_name="Team",
            role="write",
            inviter_email="bob@example.com",
            inviter_name="Bob",
        )
    assert result.sent is True
    assert result.error is None
    mock_client.post.assert_awaited_once()
    payload = mock_client.post.await_args.kwargs["json"]
    assert payload["to"] == ["alice@example.com"]
    assert "team" in payload["text"]
