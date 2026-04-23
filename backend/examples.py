#!/usr/bin/env python3
"""
Examples management module for the Shanghai Museum AI Guide.
Handles example storage, retrieval, and automatic extraction.
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
EXAMPLES_DIR = DATA_DIR / "examples"


class ExampleManager:
    def __init__(self):
        self._ensure_directories()
        self._load_examples()

    def _ensure_directories(self):
        EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    def _load_examples(self):
        self.good_examples = self._load_json(EXAMPLES_DIR / "good.json", [])
        self.bad_examples = self._load_json(EXAMPLES_DIR / "bad.json", [])
        self.pending_examples = self._load_json(EXAMPLES_DIR / "pending.json", [])

    def _load_json(self, path: Path, default: any):
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default

    def _save_json(self, data: any, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_relevant_examples(self, question: str, exhibit_id: str, limit: int = 3) -> List[Dict]:
        examples = [ex for ex in self.good_examples if ex.get("exhibitId") == exhibit_id or exhibit_id in ex.get("exhibitId", "")]
        if not examples:
            examples = self.good_examples[:limit]
        return examples[:limit]

    def format_examples_for_prompt(self, examples: List[Dict]) -> str:
        if not examples:
            return ""
        parts = ["", "### Good Examples to Follow"]
        for ex in examples:
            parts.extend([f"Q: {ex['question']}", f"A: {ex['answer']}", ""])
        return "\n".join(parts)

    def add_pending_example(self, question: str, answer: str, exhibit_id: str) -> str:
        example_id = str(uuid.uuid4())
        example = {
            "id": example_id,
            "type": "pending",
            "question": question,
            "exhibitId": exhibit_id,
            "answer": answer,
            "rating": 0,
            "notes": "",
            "createdAt": datetime.now().isoformat(),
            "version": "v1.0"
        }
        self.pending_examples.append(example)
        self._save_json(self.pending_examples, EXAMPLES_DIR / "pending.json")
        return example_id

    def review_pending_example(self, example_id: str, approve: bool, rating: int = 0, notes: str = "") -> bool:
        example = next((ex for ex in self.pending_examples if ex["id"] == example_id), None)
        if not example:
            return False
        self.pending_examples = [ex for ex in self.pending_examples if ex["id"] != example_id]
        if approve:
            example["type"] = "good_example"
            example["rating"] = rating
            example["notes"] = notes
            self.good_examples.append(example)
            self._save_json(self.good_examples, EXAMPLES_DIR / "good.json")
        self._save_json(self.pending_examples, EXAMPLES_DIR / "pending.json")
        return True

    def get_all_pending(self) -> List[Dict]:
        return self.pending_examples

    def get_all_good(self) -> List[Dict]:
        return self.good_examples

    def get_all_bad(self) -> List[Dict]:
        return self.bad_examples


example_manager = ExampleManager()
