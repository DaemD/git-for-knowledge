"""Structured memory metadata embedded in NAMS message content.

NAMS drops custom message metadata and Cypher is read-only, so we stamp
kb/owner fields into the stored text and filter on recall.
"""

from __future__ import annotations

import re
from typing import Any


META_START = "[skg_meta"
META_END = "]"
_META_LINE_RE = re.compile(
    r"\n?\s*\[skg_meta\b[^\]]*\]\s*$",
    re.IGNORECASE | re.DOTALL,
)
_META_ATTR_RE = re.compile(
    r'([a-z_]+)\s*=\s*"([^"]*)"',
    re.IGNORECASE,
)


def build_memory_metadata(
    *,
    kb_id: str,
    kb_name: str,
    owner_sub: str,
    owner_email: str | None,
    writer_sub: str,
    writer_email: str | None,
    graph_id: str,
    nams_conversation_id: str,
) -> dict[str, str]:
    return {
        "kb_id": kb_id,
        "kb_name": kb_name,
        "owner_sub": owner_sub,
        "owner_email": owner_email or "",
        "writer_sub": writer_sub,
        "writer_email": writer_email or "",
        "graph_id": graph_id,
        "nams_conversation_id": nams_conversation_id,
    }


def stamp_memory_text(text: str, metadata: dict[str, Any]) -> str:
    """Append a parseable metadata trailer to memory text."""
    body = strip_memory_meta(text).rstrip()
    attrs = " ".join(
        f'{key}="{_escape_attr(str(value))}"'
        for key, value in metadata.items()
        if value is not None and str(value) != ""
    )
    return f"{body}\n\n{META_START} {attrs}{META_END}"


def strip_memory_meta(text: str) -> str:
    """Remove the skg_meta trailer for cleaner display."""
    return _META_LINE_RE.sub("", text).rstrip()


def parse_memory_meta(text: str) -> dict[str, str]:
    match = _META_LINE_RE.search(text)
    if match is None:
        return {}
    return {
        key.lower(): value
        for key, value in _META_ATTR_RE.findall(match.group(0))
    }


def metadata_matches_kb(text: str, kb_id: str, graph_id: str | None = None) -> bool:
    meta = parse_memory_meta(text)
    if not meta:
        return False
    if meta.get("kb_id") == kb_id:
        return True
    if graph_id and meta.get("graph_id") == graph_id:
        return True
    return False


def _escape_attr(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
