"""Smoke-check kb_id ownership against a running MCP service.

Requires AUTH_DISABLED=true on the target (dev only).

Usage:
  python scripts/verify_dev_isolation.py https://dev-host.example
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any
from uuid import uuid4

import httpx


async def _mcp_call(
    client: httpx.AsyncClient,
    base: str,
    token: str,
    name: str,
    arguments: dict[str, Any],
) -> Any:
    response = await client.post(
        f"{base.rstrip('/')}/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload.get("result")


async def main(base_url: str) -> None:
    async with httpx.AsyncClient() as client:
        health = await client.get(f"{base_url.rstrip('/')}/health")
        health.raise_for_status()
        print("health:", health.json())

        alice = "sub:verify-alice"
        bob = "sub:verify-bob"
        kb_id = f"alice-kb-{uuid4().hex[:8]}"

        created = await _mcp_call(
            client,
            base_url,
            alice,
            "kb_create",
            {"kb_id": kb_id, "name": "Alice Private"},
        )
        print("alice create:", json.dumps(created)[:300])

        bob_list = await _mcp_call(
            client,
            base_url,
            bob,
            "kb_list",
            {},
        )
        print("bob list:", bob_list)
        print("PASS if bob cannot see alice kb_id")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    asyncio.run(main(sys.argv[1]))
