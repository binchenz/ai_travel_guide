"""Load, schema-validate, and backfill ontology data at startup.

Fails fast with a descriptive message on any inconsistency. Exposes
dicts keyed by entity id for O(1) lookup at runtime.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

import jsonschema
from pydantic import ValidationError

from . import models

ONTOLOGY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "ontology"
SCHEMAS_DIR  = ONTOLOGY_DIR / "schemas"


def _load_json(path: Path) -> list:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_schema(items: list, schema_name: str, source: Path) -> None:
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    for i, item in enumerate(items):
        errors = sorted(validator.iter_errors(item), key=lambda e: list(e.path))
        if errors:
            msgs = "\n".join(f"  - {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in errors)
            raise RuntimeError(f"Schema violation in {source.name} item #{i} (id={item.get('id','?')}):\n{msgs}")


class Ontology:
    """Loaded, validated, and indexed ontology."""

    def __init__(
        self,
        halls: Dict[str, models.Hall],
        dynasties: Dict[str, models.Dynasty],
        persons: Dict[str, models.Person],
        artifacts: Dict[str, models.Artifact],
    ) -> None:
        self.halls = halls
        self.dynasties = dynasties
        self.persons = persons
        self.artifacts = artifacts

    def artifact_ids(self) -> List[str]:
        return list(self.artifacts.keys())


def load() -> Ontology:
    """Load all four entity files, validate against schemas + Pydantic,
    ensure cross-references resolve, and backfill bidirectional relations.
    """
    pairs = [
        ("halls.json",    "hall.schema.json",    models.Hall),
        ("dynasties.json","dynasty.schema.json", models.Dynasty),
        ("persons.json",  "person.schema.json",  models.Person),
        ("artifacts.json","artifact.schema.json",models.Artifact),
    ]
    parsed: Dict[str, Dict[str, object]] = {}
    for filename, schema, model_cls in pairs:
        path = ONTOLOGY_DIR / filename
        raw = _load_json(path)
        _validate_schema(raw, schema, path)
        try:
            items = [model_cls.model_validate(item) for item in raw]
        except ValidationError as exc:
            raise RuntimeError(f"Pydantic validation failed in {filename}:\n{exc}") from exc
        parsed[filename] = {it.id: it for it in items}

    halls     = parsed["halls.json"]
    dynasties = parsed["dynasties.json"]
    persons   = parsed["persons.json"]
    artifacts = parsed["artifacts.json"]

    # Cross-reference integrity.
    for p in persons.values():
        if p.dynastyId not in dynasties:
            raise RuntimeError(f"Person {p.id} references missing dynasty {p.dynastyId}")
    for a in artifacts.values():
        if a.hallId not in halls:
            raise RuntimeError(f"Artifact {a.id} references missing hall {a.hallId}")
        if a.dynastyId not in dynasties:
            raise RuntimeError(f"Artifact {a.id} references missing dynasty {a.dynastyId}")
        for pid in a.personIds:
            if pid not in persons:
                raise RuntimeError(f"Artifact {a.id} references missing person {pid}")
        for kind, targets in a.relationships.items():
            for target in targets:
                if target not in artifacts:
                    raise RuntimeError(f"Artifact {a.id}.relationships.{kind} -> missing {target}")

    # Backfill bidirectional relationships so authors only need to write one side.
    for a in list(artifacts.values()):
        for kind, targets in list(a.relationships.items()):
            for target in targets:
                target_rel = artifacts[target].relationships.setdefault(kind, [])
                if a.id not in target_rel:
                    target_rel.append(a.id)

    return Ontology(halls=halls, dynasties=dynasties, persons=persons, artifacts=artifacts)


def load_or_exit() -> Ontology:
    """Entry point for main.py startup: print error and exit on failure."""
    try:
        return load()
    except Exception as exc:
        print(f"[ontology] FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
