#!/usr/bin/env python3
"""
端到端测试脚本 - 验证所有API功能
"""
import asyncio
import json
from dotenv import load_dotenv
load_dotenv('../.env')

async def run_tests():
    print('=== 端到端测试开始 ===')
    
    # 1. 测试展品列表
    print('\n1. 测试展品列表...')
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get('http://127.0.0.1:8080/exhibits')
        if resp.status_code == 200:
            exhibits = resp.json()
            print(f'   展品列表加载成功，共 {len(exhibits)} 个展品')
        else:
            print(f'   展品列表加载失败: {resp.status_code}')
    
    # 2. 测试TTS
    print('\n2. 测试TTS语音合成...')
    from volcano_tts import synthesize
    try:
        result = await synthesize('欢迎来到上海博物馆', 'zh')
        if 'audio' in result and len(result['audio']) > 100:
            print(f'   TTS测试成功，音频长度: {len(result["audio"])} 字符')
        else:
            print('   TTS返回数据异常')
    except Exception as e:
        print(f'   TTS测试失败: {e}')
    
    # 3. 测试ASR
    print('\n3. 测试ASR语音识别...')
    from volcano_asr import recognize
    try:
        result = await recognize('UklGRiQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YQAAAAA=', 'zh')
        if 'text' in result:
            print(f'   ASR测试成功，识别结果: "{result["text"]}"')
        else:
            print('   ASR返回数据异常')
    except Exception as e:
        print(f'   ASR测试失败: {e}')
    
    # 4. 测试聊天
    print('\n4. 测试聊天功能...')
    async with httpx.AsyncClient() as client:
        resp = await client.post('http://127.0.0.1:8080/chat', json={
            'userInput': 'Tell me about Da Ke Ding',
            'exhibitId': 'artifact-da-ke-ding',
            'sessionId': 'test-session-001',
            'language': 'en'
        })
        if resp.status_code == 200:
            data = resp.json()
            if 'content' in data and len(data['content']) > 10:
                print(f'   聊天测试成功，回复长度: {len(data["content"])} 字符')
            else:
                print('   聊天返回数据异常')
        else:
            print(f'   聊天测试失败: {resp.status_code}')
    
    # 5. 测试健康检查
    print('\n5. 测试健康检查...')
    async with httpx.AsyncClient() as client:
        resp = await client.get('http://127.0.0.1:8080/health')
        if resp.status_code == 200:
            data = resp.json()
            print(f'   健康检查成功，状态: {data.get("status", "unknown")}')
        else:
            print(f'   健康检查失败: {resp.status_code}')
    
    print('\n=== 端到端测试完成 ===')

if __name__ == '__main__':
    asyncio.run(run_tests())