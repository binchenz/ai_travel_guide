#!/usr/bin/env python3
"""
Safety fence module for the Shanghai Museum AI Guide.
Implements input filtering, persona reinforcement, and output moderation.
"""

import re
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class FenceResult:
    passed: bool
    message: Optional[str] = None
    blocked: bool = False


SENSITIVE_KEYWORDS_EN = [
    "taiwan", "tibet", "xinjiang", "hong kong", "democracy", "freedom",
    "politics", "communist", "government", "protest", "riot"
]
SENSITIVE_KEYWORDS_ZH = [
    "台湾", "西藏", "新疆", "香港", "民主", "自由", "政治", "共产党",
    "政府", "抗议", "暴动", "敏感"
]
MALICIOUS_PATTERNS = [
    r"(?i)ignore.*above",
    r"(?i)disregard.*instructions",
    r"(?i)act.*like",
    r"(?i)pretend.*to",
    r"(?i)system.*prompt"
]


class FenceManager:
    def __init__(self):
        pass

    def filter_input(self, user_input: str, language: str = "en") -> FenceResult:
        input_lower = user_input.lower()
        
        keywords = SENSITIVE_KEYWORDS_EN if language == "en" else SENSITIVE_KEYWORDS_ZH
        for keyword in keywords:
            if keyword in input_lower:
                return FenceResult(passed=False, message=f"Blocked: sensitive content detected", blocked=True)
        
        for pattern in MALICIOUS_PATTERNS:
            if re.search(pattern, user_input):
                return FenceResult(passed=False, message="Blocked: suspicious input pattern detected", blocked=True)
        
        return FenceResult(passed=True)

    def check_output(self, output: str, language: str = "en", exhibit_data: Optional[dict] = None) -> FenceResult:
        keywords = SENSITIVE_KEYWORDS_EN if language == "en" else SENSITIVE_KEYWORDS_ZH
        output_lower = output.lower()
        
        for keyword in keywords:
            if keyword in output_lower:
                return FenceResult(passed=False, message="Blocked: sensitive content in output", blocked=True)
        
        if exhibit_data:
            allowed_facts = self._extract_facts(exhibit_data)
            has_allowed_content = any(fact in output for fact in allowed_facts if len(fact) > 5)
        
        return FenceResult(passed=True)

    def _extract_facts(self, exhibit_data: dict) -> list:
        facts = []
        try:
            if "name" in exhibit_data:
                name = exhibit_data["name"]
                if isinstance(name, dict):
                    facts.extend(list(name.values()))
                else:
                    facts.append(str(name))
            
            if "dynasty" in exhibit_data:
                facts.append(str(exhibit_data["dynasty"]))
            
            if "period" in exhibit_data:
                facts.append(str(exhibit_data["period"]))
        except Exception:
            pass
        return facts

    def get_fallback_response(self, language: str = "en") -> str:
        fallbacks = {
            "en": "That's an interesting question! While I can't speak about that topic, I'd be delighted to tell you more about the wonderful artifact in front of us instead.",
            "zh": "这是个有趣的问题！虽然我不能谈论这个话题，但我很乐意给您介绍我们面前的这件精美文物。"
        }
        return fallbacks.get(language, fallbacks["en"])


fence_manager = FenceManager()
