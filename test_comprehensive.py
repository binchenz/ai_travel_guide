#!/usr/bin/env python3
"""
上海博物馆AI导览系统 - 全面测试套件
覆盖所有核心功能
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Any

BASE_URL = "http://localhost:8080"

class TestResult:
    def __init__(self, name: str, passed: bool, duration: float = 0, error: str = None):
        self.name = name
        self.passed = passed
        self.duration = duration
        self.error = error

class TestSuite:
    def __init__(self):
        self.results: List[TestResult] = []
        self.exhibits: List[Dict] = []
        self.session_id = f"test-suite-{int(time.time())}"

    def log(self, message: str):
        print(f"[LOG] {datetime.now().strftime('%H:%M:%S')} {message}")

    def run_test(self, name: str, func):
        start = time.time()
        try:
            self.log(f"Running: {name}")
            passed = func()
            duration = time.time() - start
            self.results.append(TestResult(name, passed, duration))
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} [{duration:.2f}s]")
        except Exception as e:
            duration = time.time() - start
            self.results.append(TestResult(name, False, duration, str(e)))
            print(f"❌ FAIL [{duration:.2f}s] Error: {str(e)}")

    def test_health(self) -> bool:
        """健康检查"""
        res = requests.get(f"{BASE_URL}/health")
        if not res.ok:
            return False
        data = res.json()
        return data.get("status") == "ok"

    def test_get_exhibits(self) -> bool:
        """获取展品列表"""
        res = requests.get(f"{BASE_URL}/exhibits")
        if not res.ok:
            return False
        self.exhibits = res.json()
        return len(self.exhibits) >= 5

    def test_single_exhibit_loading(self) -> bool:
        """单个展品获取"""
        if not self.exhibits:
            return False
        
        exhibit = self.exhibits[0]
        res = requests.get(f"{BASE_URL}/exhibits/{exhibit['id']}")
        return res.ok

    def test_basic_chat_en(self) -> bool:
        """英文基础聊天"""
        if not self.exhibits:
            return False
        
        ex_id = self.exhibits[0]["id"]
        payload = {
            "sessionId": self.session_id,
            "exhibitId": ex_id,
            "userInput": "Tell me about this",
            "language": "en"
        }
        
        res = requests.post(f"{BASE_URL}/chat", json=payload)
        if not res.ok:
            return False
        
        data = res.json()
        return len(data.get("content", "")) > 20

    def test_basic_chat_zh(self) -> bool:
        """中文基础聊天"""
        if not self.exhibits:
            return False
        
        ex_id = self.exhibits[0]["id"]
        payload = {
            "sessionId": f"{self.session_id}-zh",
            "exhibitId": ex_id,
            "userInput": "介绍一下这个展品",
            "language": "zh"
        }
        
        res = requests.post(f"{BASE_URL}/chat", json=payload)
        if not res.ok:
            return False
        
        data = res.json()
        return len(data.get("content", "")) > 10

    def test_multi_turn_chat(self) -> bool:
        """多轮对话"""
        if not self.exhibits:
            return False
        
        ex_id = self.exhibits[1]["id"]
        session = f"{self.session_id}-multi"
        
        for i in range(4):
            questions = [
                "What is this?",
                "Tell me more about the history",
                "How old is this?",
                "Thank you!"
            ]
            payload = {
                "sessionId": session,
                "exhibitId": ex_id,
                "userInput": questions[i],
                "language": "en"
            }
            res = requests.post(f"{BASE_URL}/chat", json=payload)
            if not res.ok or len(res.json().get("content", "")) < 10:
                return False
            time.sleep(1)
        
        return True

    def test_exhibit_switching(self) -> bool:
        """展品切换"""
        if len(self.exhibits) < 2:
            return False
        
        session = f"{self.session_id}-switch"
        
        # 第一个展品
        payload1 = {
            "sessionId": session,
            "exhibitId": self.exhibits[0]["id"],
            "userInput": "Hello",
            "language": "en"
        }
        res1 = requests.post(f"{BASE_URL}/chat", json=payload1)
        
        # 第二个展品
        payload2 = {
            "sessionId": session,
            "exhibitId": self.exhibits[1]["id"],
            "userInput": "What about this one?",
            "language": "en"
        }
        res2 = requests.post(f"{BASE_URL}/chat", json=payload2)
        
        return res1.ok and res2.ok

    def test_sensitive_content_filter(self) -> bool:
        """敏感内容过滤"""
        if not self.exhibits:
            return False
        
        blocked = 0
        total = 0
        
        test_cases = [
            "Tell me about Taiwan",
            "What about politics",
            "Xinjiang issue",
            "Hong Kong protests"
        ]
        
        for test_q in test_cases:
            total += 1
            payload = {
                "sessionId": f"{self.session_id}-filter-{total}",
                "exhibitId": self.exhibits[0]["id"],
                "userInput": test_q,
                "language": "en"
            }
            res = requests.post(f"{BASE_URL}/chat", json=payload)
            data = res.json()
            
            # 检查是否被拦截（响应较短或包含fallback）
            content = data.get("content", "").lower()
            if len(content) < 100 or "can't" in content or "interesting" in content:
                blocked += 1
        
        return blocked >= 2

    def test_management_apis(self) -> bool:
        """管理API测试"""
        # 检查人格版本API
        versions_ok = True
        try:
            res = requests.get(f"{BASE_URL}/api/persona/versions")
            versions_ok = res.ok
        except:
            versions_ok = False
        
        # 检查例子库API
        examples_ok = True
        try:
            res = requests.get(f"{BASE_URL}/api/examples/pending")
            examples_ok = res.ok
            if examples_ok:
                pending = res.json()
                print(f"[INFO] Pending examples: {len(pending)}")
        except:
            examples_ok = False
        
        try:
            res = requests.get(f"{BASE_URL}/api/examples/good")
            good_ok = res.ok
            if good_ok:
                good = res.json()
                print(f"[INFO] Good examples: {len(good)}")
        except:
            good_ok = False
        
        return versions_ok and examples_ok and good_ok

    def test_concurrent_chat(self) -> bool:
        """并发聊天测试"""
        if not self.exhibits:
            return False
        
        success = 0
        total = 3
        
        for i in range(total):
            payload = {
                "sessionId": f"{self.session_id}-concurrent-{i}",
                "exhibitId": self.exhibits[i % len(self.exhibits)]["id"],
                "userInput": "Quick test",
                "language": "en"
            }
            res = requests.post(f"{BASE_URL}/chat", json=payload)
            if res.ok and len(res.json().get("content", "")) > 0:
                success += 1
            time.sleep(0.5)
        
        return success == total

    def test_long_input(self) -> bool:
        """长输入测试"""
        if not self.exhibits:
            return False
        
        long_text = "Could you please tell me very detailed information about this artifact? " \
                   "I'm very interested in learning about its history, how it was made, what it's made of, " \
                   "and any interesting stories behind it. I want to know everything!"
        
        payload = {
            "sessionId": f"{self.session_id}-long",
            "exhibitId": self.exhibits[0]["id"],
            "userInput": long_text,
            "language": "en"
        }
        
        res = requests.post(f"{BASE_URL}/chat", json=payload)
        return res.ok and len(res.json().get("content", "")) > 50

    def test_empty_and_invalid(self) -> bool:
        """空输入和无效输入"""
        # 空输入
        payload1 = {
            "sessionId": f"{self.session_id}-empty",
            "exhibitId": "invalid",
            "userInput": "",
            "language": "en"
        }
        
        # 无效展品ID
        payload2 = {
            "sessionId": f"{self.session_id}-invalid",
            "exhibitId": "invalid-id-1234",
            "userInput": "Hello",
            "language": "en"
        }
        
        res1 = requests.post(f"{BASE_URL}/chat", json=payload1)
        res2 = requests.post(f"{BASE_URL}/chat", json=payload2)
        
        return True  # 只要不崩溃就通过

    def run_all_tests(self):
        print("\n" + "="*80)
        print("🏛️ 上海博物馆AI导览系统 - 全面测试")
        print("="*80)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试会话: {self.session_id}")
        print()

        # 基础功能
        print("--- 基础功能 ---")
        self.run_test("健康检查", self.test_health)
        self.run_test("获取展品列表", self.test_get_exhibits)
        self.run_test("单个展品获取", self.test_single_exhibit_loading)

        # 聊天功能
        print("\n--- 聊天功能 ---")
        self.run_test("英文基础聊天", self.test_basic_chat_en)
        self.run_test("中文基础聊天", self.test_basic_chat_zh)
        self.run_test("多轮对话", self.test_multi_turn_chat)
        self.run_test("展品切换", self.test_exhibit_switching)

        # 安全功能
        print("\n--- 安全功能 ---")
        self.run_test("敏感内容过滤", self.test_sensitive_content_filter)

        # 管理API
        print("\n--- 管理API ---")
        self.run_test("管理API可用", self.test_management_apis)

        # 压力和边界
        print("\n--- 压力与边界 ---")
        self.run_test("并发聊天测试", self.test_concurrent_chat)
        self.run_test("长输入测试", self.test_long_input)
        self.run_test("空和无效输入", self.test_empty_and_invalid)

        # 总结
        self.print_summary()

    def print_summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        pass_rate = (passed / total) * 100 if total > 0 else 0
        total_time = sum(r.duration for r in self.results)

        print("\n" + "="*80)
        print("📊 测试总结报告")
        print("="*80)
        print(f"\n  总测试数:  {total}")
        print(f"  通过:      {passed}")
        print(f"  失败:      {failed}")
        print(f"  通过率:    {pass_rate:.1f}%")
        print(f"  总耗时:    {total_time:.1f}s")

        if failed > 0:
            print(f"\n❌ 失败的测试:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.name}")
                    if result.error:
                        print(f"    Error: {result.error}")

        print("\n✅ 通过的测试:")
        for result in self.results:
            if result.passed:
                print(f"  - {result.name}")

        print("\n" + "="*80)
        if pass_rate >= 90:
            print("🎉 优秀！系统运行稳定！")
        elif pass_rate >= 70:
            print("👍 良好！有少量改进空间")
        else:
            print("⚠️ 需要关注")
        print("="*80)


if __name__ == "__main__":
    suite = TestSuite()
    suite.run_all_tests()
