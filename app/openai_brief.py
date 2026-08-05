"""OpenAI helpers for KB / entity briefs (gpt-4o-mini by default)."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings


class OpenAINotConfiguredError(RuntimeError):
    pass


async def chat_json(
    settings: Settings,
    *,
    system: str,
    user: str,
    temperature: float = 0.3,
) -> dict[str, Any]:
    if not settings.openai_configured:
        raise OpenAINotConfiguredError("OPENAI_API_KEY is not configured")

    model = settings.openai_model.strip() or "gpt-4o-mini"
    api_key = settings.openai_api_key.get_secret_value()  # type: ignore[union-attr]
    payload = {
        "model": model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()

    content = (
        (((body.get("choices") or [{}])[0]).get("message") or {}).get("content")
        or "{}"
    )
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("OpenAI returned non-object JSON")
    return parsed


async def generate_kb_brief(
    settings: Settings,
    *,
    kb_id: str,
    kb_name: str,
    entities: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    recent_previews: list[str],
) -> dict[str, Any]:
    system = (
        "You summarize a team's knowledge base for a CRM-style dashboard. "
        "Return JSON only with keys: summary (string, 3-5 sentences), "
        "core_facts (array of 5-8 short strings), "
        "key_people_orgs (array of 3 short strings), "
        "gaps (array of 3 short strings about missing/unclear knowledge), "
        "suggested_pushes (array of 3 short actionable strings). "
        "Be concrete. Do not invent facts not supported by the input. "
        "If input is thin, say so in summary and gaps."
    )
    user = json.dumps(
        {
            "kb_id": kb_id,
            "kb_name": kb_name,
            "entities": entities[:40],
            "relationships": edges[:60],
            "recent_pushes": recent_previews[:12],
        },
        ensure_ascii=True,
    )
    return await chat_json(settings, system=system, user=user)


async def generate_entity_brief(
    settings: Settings,
    *,
    kb_id: str,
    entity: dict[str, Any],
    neighbors: list[dict[str, Any]],
    source_previews: list[str],
) -> dict[str, Any]:
    system = (
        "Explain one entity inside a knowledge base for a CRM dashboard. "
        "Return JSON only with keys: "
        "headline (one sentence), "
        "why_it_matters (1-2 sentences), "
        "related (array of up to 5 short relationship phrases), "
        "open_questions (array of up to 3 short strings). "
        "Do not invent facts beyond the provided context."
    )
    user = json.dumps(
        {
            "kb_id": kb_id,
            "entity": entity,
            "neighbors": neighbors[:20],
            "source_snippets": source_previews[:8],
        },
        ensure_ascii=True,
    )
    return await chat_json(settings, system=system, user=user, temperature=0.25)
