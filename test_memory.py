#!/usr/bin/env python3
"""
记忆系统专项测试
"""
import requests
import time
import json

BASE_URL = "http://localhost:8080"

print("="*70)
print("🧠 上海博物馆AI导览 - 记忆系统测试")
print("="*70)

# 测试会话
SESSION_ID = "test-memory-session-001"

print("\n1. 测试初始对话（第一轮）")
print("-"*50)

res1 = requests.post(f"{BASE_URL}/chat", json={
    "sessionId": SESSION_ID,
    "exhibitId": "artifact-da-ke-ding",
    "userInput": "Tell me about this bronze. I'm interested in the history.",
    "language": "en"
})

data1 = res1.json()
print(f"✓ 响应长度: {len(data1['content'])}")
print(f"✓ 当前深度: {data1['depthLevel']}")
print(f"✓ 人格版本: {data1['personaVersion']}")
print(f"✓ 回答开头: {data1['content'][:80]}...")

time.sleep(1)

print("\n2. 测试第二轮（应该开始深化 + 记忆兴趣）")
print("-"*50)

res2 = requests.post(f"{BASE_URL}/chat", json={
    "sessionId": SESSION_ID,
    "exhibitId": "artifact-da-ke-ding",
    "userInput": "Tell me more about the inscription in detail.",
    "language": "en"
})

data2 = res2.json()
print(f"✓ 响应长度: {len(data2['content'])}")
print(f"✓ 当前深度: {data2['depthLevel']}")
print(f"✓ 深度变化: {data2['depthLevel']} (预期: deeper)")

time.sleep(1)

print("\n3. 测试第三轮（继续深化）")
print("-"*50)

res3 = requests.post(f"{BASE_URL}/chat", json={
    "sessionId": SESSION_ID,
    "exhibitId": "artifact-da-ke-ding",
    "userInput": "Can you compare this to ancient Western bronze work?",
    "language": "en"
})

data3 = res3.json()
print(f"✓ 响应长度: {len(data3['content'])}")
print(f"✓ 当前深度: {data3['depthLevel']}")

time.sleep(1)

print("\n4. 查看积累的待审核例子（进化系统）")
print("-"*50)

res_examples = requests.get(f"{BASE_URL}/api/examples/pending")
pending_examples = res_examples.json()
print(f"✓ 待审核例子数: {len(pending_examples)}")
if len(pending_examples) > 0:
    last_example = pending_examples[-1]
    print(f"✓ 最后一个问题: {last_example['question']}")
    print(f"✓ 展品: {last_example['exhibitId']}")

print("\n" + "="*70)
print("✅ 记忆系统测试完成！")
print("\n记忆系统功能清单:")
print("• 短期记忆: 最近6轮对话历史")
print("• 中期记忆: 用户画像（兴趣、语言、深度、参观过的展品）")
print("• 兴趣推断: 自动识别用户兴趣标签")
print("• 深度智能调整: 根据对话轮数和输入信号")
print("• 完整上下文拼接: 人格+例子+记忆")
print("="*70)
