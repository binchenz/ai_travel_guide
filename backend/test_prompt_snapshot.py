"""Prompt snapshot tests.

On first run, approves the current prompt as the baseline.
Later runs diff against it; mismatches fail.

Run:            python test_prompt_snapshot.py
Approve all:    python test_prompt_snapshot.py --update
"""
from __future__ import annotations
import difflib, sys
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).parent / "tests" / "__snapshots__"


def _check(name: str, actual: str, update: bool) -> bool:
    path = SNAPSHOT_DIR / f"{name}.txt"
    if not path.exists() or update:
        path.write_text(actual, encoding="utf-8")
        print(f"APPROVED {name}")
        return True
    expected = path.read_text(encoding="utf-8")
    if expected == actual:
        print(f"PASS     {name}")
        return True
    diff = "\n".join(difflib.unified_diff(
        expected.splitlines(), actual.splitlines(),
        fromfile=f"{name} (snapshot)", tofile=f"{name} (current)", lineterm=""
    ))
    print(f"FAIL     {name}\n{diff}")
    return False


def run(update: bool) -> int:
    from ontology.loader import load
    from ontology.resolver import expand_artifact
    from persona import persona_manager

    ont = load()
    exp = expand_artifact(ont.artifacts["artifact/da-ke-ding"], ont)

    ok = True
    for lang in ("en", "zh"):
        for level in ("entry", "deeper", "expert"):
            prompt = persona_manager.build_system_prompt(lang, level, exp)
            ok &= _check(f"da-ke-ding__{lang}__{level}", prompt, update)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run(update="--update" in sys.argv))
