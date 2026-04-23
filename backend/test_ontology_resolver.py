"""Resolver behavior tests. Run: python test_ontology_resolver.py"""
from __future__ import annotations
import sys


def test_expand_drops_id_fields():
    from ontology.loader import load
    from ontology.resolver import expand_artifact
    ont = load()
    out = expand_artifact(ont.artifacts["artifact/da-ke-ding"], ont)
    assert "hallId" not in out
    assert "dynastyId" not in out
    assert "personIds" not in out
    assert out["hall"]["id"] == "hall/bronze-gallery"
    assert out["dynasty"]["id"] == "dynasty/western-zhou"
    assert [p["id"] for p in out["persons"]] == ["person/king-li-of-zhou"]
    print("PASS expand drops ids, adds resolved objects")


def test_expand_no_recursion():
    """Person objects in the expansion should not themselves be expanded."""
    from ontology.loader import load
    from ontology.resolver import expand_artifact
    ont = load()
    out = expand_artifact(ont.artifacts["artifact/da-ke-ding"], ont)
    person = out["persons"][0]
    assert "dynastyId" in person, "Person should keep its dynastyId string (no recursion)"
    assert "dynasty" not in person, "Person must not be further expanded"
    print("PASS expansion stops at one level")


if __name__ == "__main__":
    failures = 0
    for t in (test_expand_drops_id_fields, test_expand_no_recursion):
        try:
            t()
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failures += 1
    print(f"=== {failures} failures ===")
    sys.exit(1 if failures else 0)
