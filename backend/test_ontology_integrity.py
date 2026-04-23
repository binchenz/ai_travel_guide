"""Ontology data integrity tests.

Run: python test_ontology_integrity.py
"""
from __future__ import annotations

import sys


def test_loads_without_errors():
    from ontology.loader import load
    ont = load()
    assert len(ont.halls) >= 2
    assert len(ont.dynasties) >= 4
    assert len(ont.persons) >= 3
    assert len(ont.artifacts) >= 5
    print(f"PASS load: halls={len(ont.halls)} dynasties={len(ont.dynasties)} persons={len(ont.persons)} artifacts={len(ont.artifacts)}")


def test_narrative_points_non_empty():
    from ontology.loader import load
    ont = load()
    for a in ont.artifacts.values():
        if a.narrativePoints is None:
            continue
        for depth in ("entry", "deeper", "expert"):
            points = getattr(a.narrativePoints, depth)
            assert len(points) >= 2, f"{a.id}.narrativePoints.{depth} has {len(points)} items, need >=2"
    print("PASS narrative_points non-empty")


def test_bilingual_fields_complete():
    from ontology.loader import load
    ont = load()
    for a in ont.artifacts.values():
        assert a.name.en and a.name.zh, f"{a.id}.name missing translation"
        if a.quickQuestions:
            assert a.quickQuestions.en and a.quickQuestions.zh, f"{a.id}.quickQuestions missing translation"
    for d in ont.dynasties.values():
        assert d.name.en and d.name.zh, f"{d.id}.name missing translation"
    print("PASS bilingual fields")


def test_bidirectional_relationships_symmetric():
    from ontology.loader import load
    ont = load()
    for a in ont.artifacts.values():
        for kind, targets in a.relationships.items():
            for target in targets:
                other = ont.artifacts[target].relationships.get(kind, [])
                assert a.id in other, f"{target}.relationships.{kind} missing back-ref to {a.id}"
    print("PASS bidirectional backfill")


if __name__ == "__main__":
    failures = 0
    for t in (test_loads_without_errors, test_narrative_points_non_empty,
              test_bilingual_fields_complete, test_bidirectional_relationships_symmetric):
        try:
            t()
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failures += 1
        except Exception as e:
            print(f"ERROR {t.__name__}: {e}")
            failures += 1
    print(f"=== {failures} failures ===")
    sys.exit(1 if failures else 0)
