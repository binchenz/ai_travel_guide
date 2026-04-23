#!/usr/bin/env python3
"""
多层次记忆管理系统
- 短期记忆（会话内）
- 中期记忆（会话内用户画像）
- 长期记忆（可持久化，跨会话）
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
MEMORY_DIR = DATA_DIR / "memory"


class MemoryManager:
    def __init__(self):
        self._ensure_dirs()
        self._load_static_knowledge()
    
    def _ensure_dirs(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_static_knowledge(self):
        """加载静态知识用于后期增强"""
        self.visitor_profiles = {
            "typical": {
                "en": "Western tourist, likely knows little about Chinese history",
                "zh": "中国游客，可能对历史有一定了解"
            }
        }
    
    def build_short_term_memory(self, history: List[Dict], max_turns: int = 6) -> str:
        """
        构建短期记忆：最近对话历史
        超过max_turns时会对更早对话进行摘要
        """
        if not history:
            return ""
        
        # 取最近max_turns轮
        recent_history = history[-max_turns:]
        
        # 格式化对话历史
        memory_parts = ["\n\n### 最近对话历史"]
        
        for idx, msg in enumerate(recent_history):
            role_prefix = "👤" if msg['role'] == 'user' else "🗣️"
            content = msg['content']
            # 超长内容截断
            if len(content) > 400:
                content = content[:380] + "..."
            memory_parts.append(f"{role_prefix} {content}")
        
        return "\n".join(memory_parts)
    
    def build_mid_term_memory(self, session: Dict[str, Any]) -> str:
        """
        构建中期记忆：用户画像、当前参观状态
        """
        memory_parts = ["\n\n### 游客画像与参观状态"]
        
        # 语言
        lang_str = "English" if session.get('language') == 'en' else "中文"
        memory_parts.append(f"- 使用语言: {lang_str}")
        
        # 当前深度
        depth_label = {
            "entry": "入门级（刚接触）",
            "deeper": "深入级（已有了解）",
            "expert": "专家级（深度讨论）"
        }.get(session.get('depthLevel'), session.get('depthLevel', 'entry'))
        memory_parts.append(f"- 当前讲解深度: {depth_label}")
        
        # 已参观展品
        visited = session.get('visitedExhibits', [])
        if visited:
            visited_names = [
                ex.split('/')[-1].replace('-', ' ').title() for ex in visited
            ]
            memory_parts.append(f"- 已参观展品: {', '.join(visited_names)}")
        
        # 用户兴趣（从对话提取的关键词）
        interests = session.get('interests', [])
        if interests:
            memory_parts.append(f"- 表现出兴趣: {', '.join(interests)}")
        
        # 对话轮数
        memory_parts.append(f"- 当前对话轮数: {session.get('turnCount', 0)}")
        
        return "\n".join(memory_parts)
    
    def infer_user_interests(self, user_input: str, current_interests: List[str]) -> List[str]:
        """
        从用户输入推断兴趣标签
        """
        interest_keywords = {
            "history": ["history", "朝代", "历史", "ancient"],
            "art": ["art", "艺术", "beautiful", "美"],
            "technique": ["technique", "技术", "craft", "工艺"],
            "politics": ["politics", "政治", "law", "法律"],
            "writing": ["inscription", "文字", "calligraphy", "书法"],
            "comparison": ["compare", "对比", "western", "西方"],
            "culture": ["culture", "文化", "belief", "信仰"]
        }
        
        new_interests = []
        input_lower = user_input.lower()
        
        for interest, keywords in interest_keywords.items():
            if any(kw in input_lower for kw in keywords) and interest not in current_interests:
                new_interests.append(interest)
        
        return current_interests + new_interests
    
    def should_adjust_depth(self, session: Dict[str, Any], user_input: str) -> Optional[str]:
        """
        判断是否需要调整深度
        返回: "entry", "deeper", "expert", 或 None
        """
        current_depth = session.get('depthLevel', 'entry')
        turn_count = session.get('turnCount', 0)
        
        # 询问更深入细节 → 升高
        deeper_signals = [
            "tell me more", "更详细", "深入", "details", "具体", "how did they"
        ]
        if any(s in user_input.lower() for s in deeper_signals) and turn_count >= 2:
            if current_depth == 'entry':
                return 'deeper'
            elif current_depth == 'deeper':
                return 'expert'
        
        # 要求简化 → 降低
        simpler_signals = [
            "simpler", "简单", "太难", "too complex", "confusing", "confuse"
        ]
        if any(s in user_input.lower() for s in simpler_signals):
            if current_depth == 'expert':
                return 'deeper'
            elif current_depth == 'deeper':
                return 'entry'
        
        # 默认规则：2轮后自动加深
        if turn_count == 2 and current_depth == 'entry':
            return 'deeper'
        if turn_count == 5 and current_depth == 'deeper':
            return 'expert'
        
        return None
    
    def build_full_prompt(self, base_prompt: str, session: Dict[str, Any]) -> str:
        """
        构建完整的记忆增强提示词
        """
        parts = [base_prompt]
        
        # 中期记忆
        mid_term = self.build_mid_term_memory(session)
        parts.append(mid_term)
        
        # 短期记忆
        short_term = self.build_short_term_memory(session.get('history', []))
        parts.append(short_term)
        
        return "".join(parts)


memory_manager = MemoryManager()
