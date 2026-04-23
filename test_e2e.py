#!/usr/bin/env python3
"""
端到端API测试脚本 - 上海博物馆AI导览项目
"""
import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8080"
EXHIBIT_IDS = [
    "artifact-da-ke-ding",
    "artifact-shang-yang-sheng", 
    "artifact-mao-gong-ding",
    "artifact-si-yang-fang-zun",
    "artifact-qing-shen"
]

def print_test(name: str, success: bool, details: str = ""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n[{status}] {name}")
    if details:
        print(f"   {details}")

def test_health():
    """测试健康检查端点"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        success = response.status_code == 200
        data = response.json() if success else {}
        print_test("Health Check", success,
                  f"Status: {response.status_code}, OpenAI Configured: {data.get('openai_configured', False)}")
        return success
    except Exception as e:
        print_test("Health Check", False, f"Exception: {str(e)}")
        return False

def test_get_exhibits():
    """测试获取展品列表"""
    try:
        response = requests.get(f"{BASE_URL}/exhibits")
        success = response.status_code == 200
        if success:
            data = response.json()
            print_test("Get Exhibits List", success,
                      f"Returned {len(data)} exhibits")
            return data
        else:
            print_test("Get Exhibits List", False, f"Status: {response.status_code}")
            return []
    except Exception as e:
        print_test("Get Exhibits List", False, f"Exception: {str(e)}")
        return []

def test_get_exhibit(exhibit_id: str):
    """测试获取单个展品"""
    try:
        response = requests.get(f"{BASE_URL}/exhibits/{exhibit_id}")
        success = response.status_code == 200
        print_test(f"Get Single Exhibit: {exhibit_id}", success,
                  f"Status: {response.status_code}")
        return success
    except Exception as e:
        print_test(f"Get Single Exhibit: {exhibit_id}", False, f"Exception: {str(e)}")
        return False

def test_chat_flow(exhibit_id: str, language: str, num_turns: int = 3):
    """测试多轮对话"""
    session_id = f"test-session-{exhibit_id.replace('/', '-')}-{int(time.time())}"
    questions = [
        "Tell me about this object",
        "What's the story behind it?", 
        "Can you give more details?"
    ]
    
    all_success = True
    for i, question in enumerate(questions[:num_turns]):
        try:
            time.sleep(1)  # 避免限流
            payload = {
                "sessionId": session_id,
                "exhibitId": exhibit_id,
                "userInput": question,
                "language": language
            }
            response = requests.post(
                f"{BASE_URL}/chat",
                json=payload,
                timeout=30
            )
            success = response.status_code == 200
            if success:
                data = response.json()
                print_test(f"Chat Turn {i+1}: {question[:30]}...", True,
                          f"Response length: {len(data['content'])} chars, Depth: {data['depthLevel']}")
            else:
                print_test(f"Chat Turn {i+1}: {question[:30]}...", False,
                          f"Status: {response.status_code}")
                all_success = False
        except Exception as e:
            print_test(f"Chat Turn {i+1}: {question[:30]}...", False,
                      f"Exception: {str(e)}")
            all_success = False
    return all_success

def run_full_test_suite():
    """运行完整测试套件"""
    print("=" * 60)
    print("上海博物馆AI导览 - 端到端测试套件")
    print("=" * 60)
    
    results = {}
    
    # 基础API测试
    results["health"] = test_health()
    exhibits = test_get_exhibits()
    results["exhibits_list"] = len(exhibits) > 0
    
    # 单展品测试
    for exhibit_id in EXHIBIT_IDS:
        results[f"exhibit_{exhibit_id}"] = test_get_exhibit(exhibit_id)
    
    # 对话测试
    print("\n" + "=" * 60)
    print("对话测试 (英语)")
    print("=" * 60)
    results["chat_en"] = test_chat_flow("artifact/da-ke-ding", "en")
    
    print("\n" + "=" * 60)
    print("对话测试 (中文)")
    print("=" * 60)
    results["chat_zh"] = test_chat_flow("artifact/shang-yang-sheng", "zh", 2)
    
    # 多展品测试
    print("\n" + "=" * 60)
    print("多展品对话测试")
    print("=" * 60)
    for i, exhibit_id in enumerate(EXHIBIT_IDS[:2]):
        results[f"multi_chat_{i}"] = test_chat_flow(exhibit_id, "en", 2)
    
    # 统计结果
    print("\n" + "=" * 60)
    print("测试结果统计")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n总计: {total} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {total - passed} 个")
    print(f"成功率: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败，请检查上面的输出")
    
    return success_rate == 100

if __name__ == "__main__":
    success = run_full_test_suite()
    exit(0 if success else 1)
