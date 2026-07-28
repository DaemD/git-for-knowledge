"""Optional invite email delivery via Resend HTTP API."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailSendResult:
    sent: bool
    error: str | None = None


async def send_kb_invite_email(
    settings: Settings,
    *,
    to_email: str,
    kb_id: str,
    kb_name: str,
    role: str,
    inviter_email: str | None,
    inviter_name: str | None,
) -> EmailSendResult:
    if not settings.invite_email_enabled:
        return EmailSendResult(sent=False, error="invite email disabled")
    if not settings.resend_api_key:
        return EmailSendResult(sent=False, error="RESEND_API_KEY not set")
    if not settings.email_from:
        return EmailSendResult(sent=False, error="EMAIL_FROM not set")

    inviter = inviter_name or inviter_email or "A collaborator"
    subject = f"You're invited to knowledge base '{kb_name}'"
    text = (
        f"{inviter} invited you to the shared knowledge base "
        f"'{kb_name}' (kb_id: {kb_id}) with {role} access.\n\n"
        f"1. Sign in to Shared Knowledge MCP with this exact Google email: "
        f"{to_email}\n"
        f"2. Use the same MCP URL and Client ID as your teammate.\n"
        f"3. Call list_knowledge_bases, then recall/remember with "
        f'kb_id="{kb_id}".\n'
    )
    html = f"""
    <p><strong>{inviter}</strong> invited you to
    <strong>{kb_name}</strong> (<code>{kb_id}</code>) with
    <strong>{role}</strong> access.</p>
    <ol>
      <li>Sign in with Google as <code>{to_email}</code></li>
      <li>Connect the Shared Knowledge MCP (same URL + Client ID)</li>
      <li>Use <code>list_knowledge_bases</code>, then
          <code>recall</code>/<code>remember</code> with
          <code>kb_id="{kb_id}"</code></li>
    </ol>
    """

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": (
                        f"Bearer {settings.resend_api_key.get_secret_value()}"
                    ),
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.email_from,
                    "to": [to_email],
                    "subject": subject,
                    "text": text,
                    "html": html,
                },
            )
        if response.status_code >= 400:
            detail = response.text[:300]
            logger.warning("Invite email failed: %s %s", response.status_code, detail)
            return EmailSendResult(
                sent=False,
                error=f"provider {response.status_code}: {detail}",
            )
        return EmailSendResult(sent=True)
    except httpx.HTTPError as exc:
        logger.warning("Invite email transport error: %s", exc)
        return EmailSendResult(sent=False, error=str(exc))
