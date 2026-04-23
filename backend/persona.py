#!/usr/bin/env python3
"""
Persona management module for the Shanghai Museum AI Guide.
Handles persona loading, version management, and prompt generation.
"""

import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
PERSONA_DIR = DATA_DIR / "persona"
CURRENT_PERSONA = PERSONA_DIR / "current.json"
PERSONA_HISTORY = PERSONA_DIR / "history"


class PersonaManager:
    def __init__(self):
        self._ensure_directories()
        self._load_current_persona()

    def _ensure_directories(self):
        PERSONA_DIR.mkdir(parents=True, exist_ok=True)
        PERSONA_HISTORY.mkdir(parents=True, exist_ok=True)

    def _load_current_persona(self):
        if CURRENT_PERSONA.exists():
            with open(CURRENT_PERSONA, "r", encoding="utf-8") as f:
                self.current_persona = json.load(f)
        else:
            self.current_persona = self._create_default_persona()
            self._save_persona(self.current_persona, CURRENT_PERSONA)

    def _create_default_persona(self) -> Dict:
        return {
            "version": "v2.0",
            "isStable": True,
            "createdAt": datetime.now().isoformat(),
            "persona": {
                "en": {
                    "identity": "You are a knowledgeable, warm, and engaging museum storyteller at the Shanghai Museum, specializing in Chinese art and history for international visitors.",
                    "personality": "You are curious, patient, and genuinely passionate about sharing Chinese culture.",
                    "principles": [
                        "Start with a hook/story, then add factual details",
                        "Use everyday analogies (e.g., \"3000-year-old pressure cooker!\")",
                        "Explain Chinese cultural concepts in simple terms",
                        "Go deeper when visitor shows interest",
                        "Make it sound like a friendly conversation, not a textbook"
                    ],
                    "cultural_translator": [
                        "When you mention Chinese cultural concepts, explain them briefly:",
                        "Example: Ritual vessel → \"a special object for ancient ceremonies\"",
                        "Example: Inscription → \"writing cast into bronze\"",
                        "Keep explanations 1-2 sentences max"
                    ],
                    "boundaries": ["I don't discuss modern politics"],
                    "fallback": "That's an interesting question! I'd be happy to share more about the artifact instead.",
                    "tone": "Warm, engaging, professional but friendly"
                },
                "zh": {
                    "identity": "你是上海博物馆一位博学、温暖且富有魅力的故事家。",
                    "personality": "你充满好奇心、耐心，并且真诚地热爱分享中国文化。",
                    "principles": [
                        "以一个悬念或故事开头，然后再加入事实细节",
                        "使用生活化类比（如：3000年前的\"高压锅\"！）",
                        "用简单的话解释中国文化概念",
                        "访客表现出兴趣时再深入讲解",
                        "听起来像友好对话，不像教科书"
                    ],
                    "cultural_translator": [
                        "提到中国文化概念时，要简要解释：",
                        "例：礼器 → \"古代用于仪式的特殊器具\"",
                        "例：铭文 → \"铸在青铜器上的文字\"",
                        "解释不超过1-2句话"
                    ],
                    "boundaries": ["我不讨论现代政治"],
                    "fallback": "这是个有趣的问题！我很乐意给您介绍我们面前的这件文物。",
                    "tone": "温暖、迷人、专业但友好"
                }
            }
        }

    def _save_persona(self, persona_data: Dict, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(persona_data, f, ensure_ascii=False, indent=2)

    def get_persona(self, language: str = "en") -> Dict:
        lang = language if language in self.current_persona["persona"] else "en"
        return self.current_persona["persona"][lang]

    def get_depth_template(self, language: str, depth_level: str) -> Dict:
        persona = self.get_persona(language)
        templates = persona.get("depthTemplates", {})
        return templates.get(depth_level) or templates.get("entry") or {
            "opener": "",
            "focus": "",
            "sentenceStyle": "",
        }

    def build_system_prompt(
        self,
        language: str = "en",
        depth_level: str = "entry",
        artifact_expanded: Optional[Dict] = None,
    ) -> str:
        persona = self.get_persona(language)
        dt = self.get_depth_template(language, depth_level)

        parts: list = [
            persona["identity"],
            "",
            "### Personality",
            persona["personality"],
            "",
            "### Guiding Principles",
            *(f"- {p}" for p in persona["principles"]),
            "",
            "### Cultural Translator",
            *(f"- {i}" for i in persona.get("cultural_translator", [])),
            "",
            "### Boundaries",
            *(f"- {b}" for b in persona["boundaries"]),
            "",
            f"### How to respond at this depth level ({depth_level})",
            f"- {dt['opener']}",
            f"- Focus: {dt['focus']}",
            f"- Sentence style: {dt['sentenceStyle']}",
            "",
            "### Fallback",
            persona["fallback"],
            "",
            "### Tone",
            persona["tone"],
        ]

        if artifact_expanded:
            parts += ["", "### Current artifact (facts only — do not invent beyond this)"]
            parts.append(self._format_artifact_facts(artifact_expanded, language))

            nps = (artifact_expanded.get("narrativePoints") or {}).get(depth_level) or []
            if nps:
                parts += ["", "### Narrative points you may draw from"]
                parts += [f"- {p}" for p in nps]

            related = self._format_related_entities(artifact_expanded, language)
            if related:
                parts += ["", "### Related entities the visitor can ask about next", related]

        return "\n".join(parts)

    def _format_artifact_facts(self, a: Dict, language: str) -> str:
        lang = language if language in ("en", "zh") else "en"

        def bi(obj):
            return obj.get(lang) if isinstance(obj, dict) else obj

        lines = [f"- Name: {bi(a['name'])}"]
        hall = a.get("hall") or {}
        dyn  = a.get("dynasty") or {}
        if dyn:
            lines.append(f"- Dynasty: {bi(dyn.get('name'))} ({bi((dyn.get('period') or {}).get('label'))})")
        if hall:
            lines.append(f"- Hall: {bi(hall.get('name'))}, floor {hall.get('floor')}")
        if a.get("period"):
            lines.append(f"- Period: {bi(a['period'].get('label'))}")
        dims = a.get("dimensions") or {}
        if dims:
            dim_parts = [f"{k} {v['value']} {v['unit']}" for k, v in dims.items()]
            lines.append(f"- Dimensions: {', '.join(dim_parts)}")
        if a.get("material"):
            lines.append(f"- Material: {', '.join(a['material'])}")
        if a.get("techniques"):
            lines.append(f"- Techniques: {', '.join(a['techniques'])}")
        insc = a.get("inscriptions") or {}
        if insc:
            sig = bi(insc.get("significance")) if insc.get("significance") else ""
            lines.append(f"- Inscriptions: {insc.get('characterCount', 0)} characters. {sig}")
        ctx = a.get("culturalContext") or {}
        if ctx.get("ritualUse"):
            lines.append(f"- Ritual use: {bi(ctx.get('ritualUse'))}")
        if ctx.get("socialFunction"):
            lines.append(f"- Social function: {bi(ctx.get('socialFunction'))}")
        return "\n".join(lines)

    def _format_related_entities(self, a: Dict, language: str) -> str:
        lang = language if language in ("en", "zh") else "en"

        def bi(x):
            return x.get(lang) if isinstance(x, dict) else x

        chunks = []
        persons = a.get("persons") or []
        if persons:
            chunks.append("- Persons: " + ", ".join(bi(p["name"]) for p in persons))
        rels = a.get("relationships") or {}
        for kind, targets in rels.items():
            if targets:
                chunks.append(f"- {kind}: {', '.join(targets)}")
        return "\n".join(chunks)

    def get_version(self) -> str:
        return self.current_persona["version"]

    def get_all_versions(self) -> list:
        versions = [{"version": self.current_persona["version"], "isCurrent": True, "isStable": self.current_persona["isStable"], "createdAt": self.current_persona["createdAt"]}]
        for file in sorted(PERSONA_HISTORY.glob("v*.json"), reverse=True):
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                versions.append({
                    "version": data["version"],
                    "isCurrent": False,
                    "isStable": data.get("isStable", False),
                    "createdAt": data["createdAt"]
                })
        return versions

    def rollback_to_version(self, version: str) -> bool:
        version_file = PERSONA_HISTORY / f"{version}.json"
        if not version_file.exists():
            return False
        with open(version_file, "r", encoding="utf-8") as f:
            old_persona = json.load(f)
        self._save_persona(self.current_persona, PERSONA_HISTORY / f"{self.current_persona['version']}.json")
        old_persona["isStable"] = True
        self.current_persona = old_persona
        self._save_persona(self.current_persona, CURRENT_PERSONA)
        return True


persona_manager = PersonaManager()
