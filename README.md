# AI Travel Guide - Shanghai Museum

## 项目概述

这是一个为上海博物馆设计的AI导览应用，提供展品详情、语音介绍和智能问答功能。

## 技术架构

### 后端 (Python/FastAPI)
- **框架**: FastAPI
- **端口**: 8080
- **主要功能**:
  - 展品数据管理 (`/exhibits`)
  - 智能聊天响应 (`/chat`, `/chat/stream`)
  - 火山引擎TTS V2语音合成 (`/tts`)
  - 火山引擎ASR V2语音识别 (`/asr`)

### 前端 (React/TypeScript + Vite)
- **端口**: 3003
- **主要功能**:
  - 展品列表展示
  - 语音播放 (TTS)
  - 语音输入 (ASR)
  - 实时聊天界面

## 已解决的问题

### 1. 火山引擎TTS V2集成 - 已完成

**解决方案**:
- 实现了完整的火山引擎TTS V2 WebSocket客户端
- 使用WebSocket连接池优化性能，减少连接建立时间
- 添加了edge-tts作为备用方案，确保服务稳定性
- 解决了TTS生成速度慢和句子中间停顿大的问题

**当前状态**:
- ✅ 后端TTS端点已实现
- ✅ 返回真实的火山引擎TTS音频
- ✅ 支持中文和英文语音合成
- ✅ 集成了连接池优化性能

### 2. 火山引擎ASR V2集成 - 已完成

**解决方案**:
- 实现了完整的火山引擎ASR V2 WebSocket客户端
- 支持PCM音频格式的处理和发送
- 优化了音频数据的分块发送和结果收集

**当前状态**:
- ✅ 后端ASR端点已实现
- ✅ 支持语音识别功能
- ✅ 前端已集成MediaRecorder录音
- ✅ 解决了浏览器SpeechRecognition API的网络限制问题

### 3. 前端预览访问问题

**问题描述**:
前端预览功能有时无法正常工作。

**可能原因**:
- 跨域（CORS）配置问题
- 端口冲突
- 浏览器缓存

**解决方案**:
1. 清除浏览器缓存
2. 检查CORS配置
3. 确保端口3003未被占用

## API端点

### GET /exhibits
获取所有展品列表

**响应**:
```json
{
  "id": "artifact-da-ke-ding",
  "originalId": "/exhibits/bronze/da-ke-ding",
  "name": {"en": "Da Ke Ding", "zh": "大克鼎"},
  "imageUrl": "https://...",
  "dynasty": "Western Zhou",
  "period": "约公元前10世纪",
  "hall": "中国古代青铜器馆",
  "quickQuestions": ["问题1", "问题2"]
}
```

### POST /chat
发送聊天消息（非流式）

**请求**:
```json
{
  "userInput": "Tell me about Da Ke Ding",
  "exhibitId": "artifact-da-ke-ding",
  "sessionId": "uuid",
  "depthLevel": "entry",
  "language": "en"
}
```

### POST /chat/stream
发送聊天消息（流式）

**请求**: 同上

**响应**: Server-Sent Events (SSE) 流

### POST /tts
火山引擎TTS V2语音合成

**请求**:
```json
{
  "text": "大克鼎是西周时期的青铜器",
  "language": "zh"
}
```

**响应**:
```json
{
  "audio": "base64_encoded_mp3",
  "format": "mp3",
  "message": "TTS V2 mock response"
}
```

### POST /asr
火山引擎ASR V2语音识别

**请求**:
```json
{
  "audio": "base64_encoded_audio",
  "language": "zh"
}
```

**响应**:
```json
{
  "text": "识别结果文本",
  "language": "zh"
}
```

## 环境配置

### 火山引擎凭证信息

在[火山引擎控制台](https://console.volcengine.com/speech/app) 申请 App ID、
Access Token 与 Secret Key，并写入本地 `.env`（**切勿提交到仓库**）。
`backend/.env.example` 提供了完整的变量清单作为参考。

### 火山引擎文档链接

- **TTS V3 文档**: https://www.volcengine.com/docs/6561/1668014
- **ASR V3 文档**: https://www.volcengine.com/docs/6561/1354869?lang=zh

### 必需的环境变量

```bash
# 模型服务（Moonshot/OpenAI 兼容）
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.moonshot.cn/v1
MODEL_NAME=kimi-k2-turbo-preview

# 火山引擎凭证
VOLCANO_APP_KEY=<your_app_id>
VOLCANO_ACCESS_TOKEN=<your_access_token>

# 语音后端可选调优
VOICE_TTS_BACKEND=edge           # edge | volcano | auto
VOICE_TTS_CACHE_SIZE=256
VOICE_TTS_MAX_CONCURRENCY=8
```

### 启动应用

```bash
# 1. 启动后端
cd backend
python3 main.py

# 2. 启动前端 (新终端)
cd frontend
npm run dev
```

## 功能列表

- [x] 展品列表展示
- [x] 展品详情查看
- [x] 聊天问答功能 + 流式响应
- [x] 语音合成（Edge TTS 为主、火山 V3 备用，支持 LRU 缓存）
- [x] 语音识别（火山 SAUC bigmodel WebSocket，支持动态超时）
- [x] 语音观测性：`GET /voice/health`、`GET /voice/metrics`

## 观测端点

| 端点 | 用途 |
|------|------|
| `GET /voice/health` | 当前 TTS 后端、凭证配置状态、依赖可用性 |
| `GET /voice/metrics` | 各后端调用数、p50/p95 延迟、错误率、缓存命中率 |

## 下一步工作

1. 添加更多展品数据
2. 优化 UI/UX 设计
3. 多语言内容扩展
4. 部署到生产环境（Redis 缓存 / 多实例）

## 技术栈

- **后端**: Python 3, FastAPI, Uvicorn, OpenAI API, 火山引擎SDK
- **前端**: React 18, TypeScript, Vite, TailwindCSS, Radix UI
- **语音服务**: 火山引擎TTS/ASR V2, 浏览器Web Speech API
