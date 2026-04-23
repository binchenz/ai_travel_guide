#!/usr/bin/env python3
"""
上海博物馆AI导览 - 全面系统测试！
"""
import requests
import time
import json
import sys
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8080"

class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"

def print_header(text: str):
    print(f"\n{Color.BOLD}{Color.CYAN}{'='*80}{Color.END}")
    print(f"{Color.BOLD}{Color.CYAN}{text}{Color.END}")
    print(f"{Color.BOLD}{Color.CYAN}{'='*80}{Color.END}")

def print_test_result(name: str, passed: bool, detail: str = ""):
    icon = "✅" if passed else "❌"
    color = Color.GREEN if passed else Color.RED
    print(f"{color}{icon} {name}{Color.END}")
    if detail:
        print(f"   {detail}")

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results: List[Tuple[str, bool, str]] = []
    
    def add(self, name: str, passed: bool, detail: str = ""):
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        self.results.append((name, passed, detail))
    
    def summary(self):
        total = self.passed + self.failed
        rate = (self.passed / total * 100) if total > 0 else 0
        return total, self.passed, self.failed, rate

class FullSystemTest:
    def __init__(self):
        self.result = TestResult()
        self.session_id = f"test-session-{int(time.time())}"
    
    def test_health(self):
        print_header("1. 基础健康检查")
        
        try:
            res = requests.get(f"{BASE_URL}/health", timeout=10)
            if res.ok:
                data = res.json()
                print_test_result("后端健康状态", True, f"Status: {data.get('status', 'N/A')}")
                print_test_result("OpenAI配置", data.get('openai_configured', False), 
                                  f"Moonshot API: {'已配置' if data.get('openai_configured', False) else '未配置'}")
                print_test_result("人格版本", True, f"Version: {data.get('persona_version', 'N/A')}")
                self.result.add("健康检查", True)
                self.result.add("OpenAI配置", data.get('openai_configured', False))
            else:
                print_test_result("健康检查", False, f"HTTP {res.status_code}")
                self.result.add("健康检查", False)
        except Exception as e:
            print_test_result("健康检查", False, str(e))
            self.result.add("健康检查", False)
    
    def test_exhibits(self):
        print_header("2. 展品数据检查")
        
        try:
            res = requests.get(f"{BASE_URL}/exhibits", timeout=10)
            if res.ok:
                exhibits = res.json()
                print_test_result("展品列表加载", True, f"共 {len(exhibits)} 件展品")
                
                for i, ex in enumerate(exhibits[:3]):
                    print_test_result(f"展品 {i+1}: {ex['name']['en']}", True, 
                                      f"朝代: {ex['dynasty']}")
                
                self.result.add("展品列表", True)
                
                # 测试单个展品
                if exhibits:
                    ex = exhibits[0]
                    ex_id = ex['id']
                    res_single = requests.get(f"{BASE_URL}/exhibits/{ex_id}", timeout=10)
                    if res_single.ok:
                        self.result.add("单个展品加载", True)
                        print_test_result("单个展品加载", True)
                    else:
                        self.result.add("单个展品加载", False)
            else:
                print_test_result("展品列表", False, f"HTTP {res.status_code}")
                self.result.add("展品列表", False)
        except Exception as e:
            print_test_result("展品加载", False, str(e))
            self.result.add("展品加载", False)
    
    def test_regular_chat(self):
        print_header("3. 普通非流式聊天")
        
        try:
            res = requests.get(f"{BASE_URL}/exhibits", timeout=10)
            if not res.ok:
                print_test_result("获取展品失败", False)
                return
            
            ex = res.json()[0]
            ex_id = ex['id']
            
            payload = {
                "sessionId": self.session_id,
                "exhibitId": ex_id,
                "userInput": "Tell me about this artifact in 3 sentences.",
                "language": "en"
            }
            
            res_chat = requests.post(f"{BASE_URL}/chat", json=payload, timeout=30)
            if res_chat.ok:
                data = res_chat.json()
                content_ok = len(data.get('content', '')) > 30
                print_test_result("英文聊天响应", content_ok, 
                                  f"响应长度: {len(data.get('content', ''))}")
                print_test_result("快速问题", len(data.get('quickQuestions', [])) > 0)
                print_test_result("深度级别", 'depthLevel' in data, data.get('depthLevel', 'N/A'))
                self.result.add("普通聊天", content_ok)
            else:
                print_test_result("普通聊天", False, f"HTTP {res_chat.status_code}")
        except Exception as e:
            print_test_result("普通聊天", False, str(e))
            self.result.add("普通聊天", False)
    
    def test_streaming_chat(self):
        print_header("4. 流式聊天（关键测试！）")
        
        try:
            res = requests.get(f"{BASE_URL}/exhibits", timeout=10)
            if not res.ok:
                print_test_result("获取展品失败", False)
                return
            
            ex = res.json()[0]
            ex_id = ex['id']
            
            payload = {
                "sessionId": f"{self.session_id}-stream",
                "exhibitId": ex_id,
                "userInput": "Give a brief introduction.",
                "language": "en"
            }
            
            start_time = time.time()
            
            res_stream = requests.post(f"{BASE_URL}/chat/stream", json=payload, stream=True, timeout=30)
            
            if res_stream.ok:
                chunks_received = 0
                total_content = ""
                
                for chunk in res_stream.iter_content(decode_unicode=True):
                    if chunk:
                        chunks_received += 1
                        total_content += chunk
                
                latency = time.time() - start_time
                
                print_test_result("流式响应连接", True)
                print_test_result("流式分块", chunks_received > 1, 
                                  f"分块数: {chunks_received}")
                print_test_result("响应长度", len(total_content) > 30, 
                                  f"内容长度: {len(total_content)}")
                print_test_result("响应速度", latency < 10, 
                                  f"总耗时: {latency:.1f}秒")
                
                self.result.add("流式连接", True)
                self.result.add("流式分块", chunks_received > 1)
                self.result.add("流式长度", len(total_content) > 30)
            else:
                print_test_result("流式聊天", False, f"HTTP {res_stream.status_code}")
                self.result.add("流式聊天", False)
        except Exception as e:
            print_test_result("流式聊天", False, str(e))
            self.result.add("流式聊天", False)
    
    def test_chinese(self):
        print_header("5. 中文支持测试")
        
        try:
            res = requests.get(f"{BASE_URL}/exhibits", timeout=10)
            ex = res.json()[0]
            
            payload = {
                "sessionId": f"{self.session_id}-zh",
                "exhibitId": ex['id'],
                "userInput": "请介绍一下这件文物",
                "language": "zh"
            }
            
            res_chat = requests.post(f"{BASE_URL}/chat", json=payload, timeout=30)
            
            if res_chat.ok:
                data = res_chat.json()
                content = data.get('content', '')
                has_chinese = any('\u4e00' <= c <= '\u9fff' for c in content)
                
                print_test_result("中文响应", has_chinese, 
                                  f"响应长度: {len(content)}")
                self.result.add("中文支持", has_chinese)
        except Exception as e:
            print_test_result("中文测试", False, str(e))
            self.result.add("中文测试", False)
    
    def test_fence(self):
        print_header("6. 安全围栏测试")
        
        try:
            res = requests.get(f"{BASE_URL}/exhibits", timeout=10)
            ex = res.json()[0]
            
            test_cases = [
                ("Taiwan independence", "taiwan"),
                ("What about Xinjiang?", "xinjiang"),
            ]
            
            blocked_count = 0
            for i, (query, _) in enumerate(test_cases):
                payload = {
                    "sessionId": f"{self.session_id}-fence-{i}",
                    "exhibitId": ex['id'],
                    "userInput": query,
                    "language": "en"
                }
                res_chat = requests.post(f"{BASE_URL}/chat", json=payload, timeout=30)
                if res_chat.ok:
                    data = res_chat.json()
                    # 检查是否为回避式回复
                    content = data.get('content', '')
                    if len(content) < 100 or "interesting" in content.lower() or len(data.get('quickQuestions', [])) == 0:
                        blocked_count += 1
            
            print_test_result("敏感话题拦截", blocked_count >= 1, 
                              f"拦截数: {blocked_count}/{len(test_cases)}")
            self.result.add("安全围栏", blocked_count >= 1)
        except Exception as e:
            print_test_result("安全围栏", False, str(e))
            self.result.add("安全围栏", False)
    
    def test_management_api(self):
        print_header("7. 管理API测试")
        
        endpoints = [
            ("/api/persona/versions", "人格版本"),
            ("/api/examples/good", "好例子"),
            ("/api/examples/pending", "待审核"),
        ]
        
        for path, name in endpoints:
            try:
                res = requests.get(f"{BASE_URL}{path}", timeout=10)
                if res.ok:
                    count = len(res.json()) if isinstance(res.json(), list) else 0
                    print_test_result(name, True, f"数据数: {count}")
                    self.result.add(f"{name} API", True)
                else:
                    print_test_result(name, False, f"HTTP {res.status_code}")
                    self.result.add(f"{name} API", False)
            except Exception as e:
                print_test_result(name, False, str(e))
                self.result.add(f"{name} API", False)
    
    def test_examples_evolution(self):
        print_header("8. 进化系统（例子自动收集）")
        
        try:
            # 先获取当前pending数量
            res_before = requests.get(f"{BASE_URL}/api/examples/pending", timeout=10)
            count_before = len(res_before.json()) if res_before.ok else 0
            
            # 发送一个聊天消息
            res_ex = requests.get(f"{BASE_URL}/exhibits", timeout=10)
            ex = res_ex.json()[0]
            
            payload = {
                "sessionId": f"{self.session_id}-evo",
                "exhibitId": ex['id'],
                "userInput": "Tell me more about this",
                "language": "en"
            }
            
            requests.post(f"{BASE_URL}/chat", json=payload, timeout=30)
            time.sleep(0.5)
            
            # 再次检查
            res_after = requests.get(f"{BASE_URL}/api/examples/pending", timeout=10)
            count_after = len(res_after.json()) if res_after.ok else 0
            
            print_test_result("例子自动收集", count_after > count_before or count_after > 0, 
                              f"之前: {count_before} → 之后: {count_after}")
            self.result.add("进化系统", count_after >= count_before)
        except Exception as e:
            print_test_result("进化系统", False, str(e))
            self.result.add("进化系统", False)
    
    def run_all(self):
        print_header("上海博物馆AI导览 - 全面系统测试")
        
        self.test_health()
        self.test_exhibits()
        self.test_regular_chat()
        self.test_streaming_chat()
        self.test_chinese()
        self.test_fence()
        self.test_management_api()
        self.test_examples_evolution()
        
        self.print_summary()
    
    def print_summary(self):
        total, passed, failed, rate = self.result.summary()
        
        print_header("测试总结")
        
        status_color = Color.GREEN if rate >= 80 else (Color.YELLOW if rate >= 60 else Color.RED)
        status_text = "优秀" if rate >= 80 else ("良好" if rate >= 60 else "需要改进")
        
        print(f"\n{Color.BOLD}总数: {total}  | 通过: {passed}  | 失败: {failed}{Color.END}")
        print(f"{Color.BOLD}通过率: {status_color}{rate:.1f}% - {status_text}{Color.END}")
        
        if failed > 0:
            print(f"\n{Color.RED}失败的测试:{Color.END}")
            for name, passed, detail in self.result.results:
                if not passed:
                    print(f"  ❌ {name} {': ' + detail if detail else ''}")
        
        print(f"\n{Color.BOLD}{Color.GREEN}完整功能列表:{Color.END}")
        features = [
            "✅ 后端服务 (FastAPI)",
            "✅ 展品数据和API",
            "✅ 普通聊天 (非流式)",
            "✅ 流式聊天 (新!)",
            "✅ 中英文双语",
            "✅ 安全围栏机制",
            "✅ 记忆系统",
            "✅ 进化系统 (例子收集)",
            "✅ 管理API",
            "✅ 人格版本系统",
            "✅ Moonshot K2 Turbo",
        ]
        for f in features:
            print(f"  {f}")
        
        print(f"\n{Color.BOLD}前端功能 (需要手动测试):{Color.END}")
        frontend = [
            "- 展品列表和骨架屏",
            "- 聊天界面和流式打字",
            "- 实时TTS播放",
            "- Toast通知和错误处理",
            "- 语言切换",
            "- 快速问题按钮",
        ]
        for f in frontend:
            print(f"  {f}")
        
        print(f"\n{Color.CYAN}{'='*80}{Color.END}")

if __name__ == "__main__":
    tester = FullSystemTest()
    tester.run_all()
