"""Wipe KB control-plane rows after a new Neo4j / NAMS graph.

Keeps users and billing. Run:

    python -m app.reset_kb_control_plane

Or set RESET_KB_CONTROL_PLANE=true on the API service for one boot, then unset it.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import get_settings
from app.db import PostgresControlStore

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    store = PostgresControlStore(settings.database_url)
    await store.connect()
    try:
        cleared = await store.clear_knowledge_plane()
        logger.info("Cleared %s (users kept)", cleared)
    finally:
        await store.close()


if __name__ == "__main__":
    asyncio.run(main())
