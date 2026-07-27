import pytest

from app.service import validate_knowledge_id
from app.utils import normalize_predicate, normalize_text, stable_id


def test_normalize_text_preserves_words_and_folds_case() -> None:
    assert normalize_text("  Cursor.AI  ") == "cursor ai"
    assert normalize_text("NÉO4J") == "néo4j"


def test_normalize_predicate_is_dynamic_but_safe() -> None:
    assert normalize_predicate("works with") == "WORKS_WITH"
    assert normalize_predicate(" inspired-by ") == "INSPIRED_BY"


def test_stable_id_is_deterministic_and_namespaced() -> None:
    first = stable_id("clm", "kg_a", "Neo4j", "USES")
    assert first == stable_id("clm", "kg_a", "Neo4j", "USES")
    assert first != stable_id("clm", "kg_b", "Neo4j", "USES")


def test_knowledge_id_validation() -> None:
    assert validate_knowledge_id("kg_12345678") == "kg_12345678"
    with pytest.raises(ValueError):
        validate_knowledge_id("../other")
