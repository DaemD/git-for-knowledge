import hashlib
import re
import unicodedata
from uuid import uuid4


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^\w\s]", " ", value)
    return " ".join(value.split())


def normalize_predicate(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return normalized or "RELATED_TO"


def stable_id(prefix: str, *parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:24]}"


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def safe_fulltext_query(value: str) -> str:
    terms = re.findall(r"\w+", normalize_text(value), flags=re.UNICODE)
    return " AND ".join(terms[:8])
