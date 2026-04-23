# AI Travel Guide - Shanghai Museum

> 上海博物馆 AI 智能导览系统 — 三层本体论架构 + 语音交互

## 🌐 线上访问

| 环境 | 地址 |
|------|------|
| **生产服务器** | http://47.97.225.14 |
| **GitHub 仓库** | https://github.com/binchenz/ai_travel_guide |

---

## 技术架构

### 三层本体论数据模型

```
FACTS  (data/ontology/)
  artifacts.json   — 15 件展品（结构化字段：period/dimensions/narrativePoints）
  halls.json       — 3 个展厅
  dynasties.json   — 11 个朝代（有前后继承关系）
  persons.json     — 7 位历史人物
  schemas/         — JSON Schema 验证（每次启动自动校验）

NARRATIVE  (data/persona/current.json v2.1)
  depthTemplates.entry/deeper/expert — 叙事模板（与事实层解耦）
  principles / boundaries / tone

SYNTHESIS  (backend/ontology/ + persona.py)
  expand_artifact()        — 一层引用展开（hall/dynasty/persons）
  build_system_prompt()    — 事实 × 叙事模板 → LLM
```

### 后端 (Python 3.11 / FastAPI)

| 端点 | 功能 |
|------|------|
| `GET /exhibits` | 展品列表（含 hallId/dynastyId/personIds） |
| `GET /exhibits/{id}` | 展品详情（展开 hall/dynasty/persons 对象） |
| `GET /ontology/halls` | 展厅列表 |
| `GET /ontology/dynasties` | 朝代列表 |
| `GET /ontology/persons` | 人物列表 |
| `GET /ontology/{type}/{id}/artifacts` | 按展厅/朝代/人物筛选展品 |
| `POST /chat` | 聊天（非流式） |
| `POST /chat/stream` | 聊天（SSE 流式） |
| `POST /tts` | 语音合成（Edge TTS 主，火山 V3 备） |
| `POST /asr` | 语音识别（火山 SAUC bigmodel） |
| `GET /voice/health` | 语音服务健康状态 |
| `GET /voice/metrics` | 语音服务性能指标 |

### 前端 (React 18 / TypeScript / Vite)

- 展品卡片列表（15 件，3 展厅）
- **EntityChip**：展厅 / 朝代 / 人物点击 chip
- **EntityDrawer**：侧滑抽屉展示实体详情 + 相关展品
- 三档深度聊天（入门 / 进阶 / 专家）
- 语音合成（TTS）— 1-segment 预取消除段间停顿
- 语音识别（ASR）— 浏览器 WebM → 16kHz WAV 转码后发送

---

## 本地开发

### 前提

- Python 3.11+
- Node.js 20+

### 启动

```bash
# 1. 克隆
git clone https://github.com/binchenz/ai_travel_guide.git
cd ai_travel_guide

# 2. 后端
cp backend/.env.example backend/.env
# 在 .env 里填写凭证（见下方环境变量说明）
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py          # 监听 :8080

# 3. 前端（新终端）
cd frontend && npm install && npm run dev    # 监听 :3000
```

访问 http://localhost:3000

---

## 环境变量

参考 `backend/.env.example`，复制为 `backend/.env` 后填写：

```bash
# LLM（Moonshot K2 兼容 OpenAI 接口）
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.moonshot.cn/v1
MODEL_NAME=kimi-k2-turbo-preview

# 火山引擎语音服务
VOLCANO_APP_KEY=<App ID>
VOLCANO_ACCESS_TOKEN=<Access Token>

# 语音后端调优（可选）
VOICE_TTS_BACKEND=edge        # edge | volcano | auto
VOICE_TTS_CACHE_SIZE=256
VOICE_TTS_MAX_CONCURRENCY=8
```

> **安全提示**：`.env` 已在 `.gitignore` 中，切勿提交到仓库。

---

## 生产服务器

| 项目 | 详情 |
|------|------|
| 服务商 | 阿里云 ECS |
| 公网 IP | `47.97.225.14` |
| 系统 | Alibaba Cloud Linux 3 |
| Python | 3.11 |
| Node.js | 20.x |
| Web 服务器 | nginx 1.20 |
| 后端进程 | systemd `ai-guide.service` |
| 代码目录 | `/root/ai_travel_guide` |

### 常用运维命令

```bash
# 查看后端实时日志
journalctl -u ai-guide -f

# 重启后端
systemctl restart ai-guide

# 更新部署（拉取最新代码 + 重建前端）
cd /root/ai_travel_guide && git pull && \
  cd frontend && npm run build && \
  systemctl restart ai-guide && systemctl reload nginx

# 查看 nginx 错误日志
tail -50 /var/log/nginx/error.log
```

### 快速一键重部署（服务器上运行）

```bash
cd /root/ai_travel_guide && git pull && bash deploy.sh
```

---

## 功能列表

- [x] 展品列表（15 件，跨 3 展厅 / 11 朝代 / 7 历史人物）
- [x] 三层本体论：Hall / Dynasty / Person 独立实体 + JSON Schema 验证
- [x] EntityChip + EntityDrawer（点击朝代/展厅/人物查看相关展品）
- [x] 聊天问答（非流式 + SSE 流式）
- [x] 三档深度（入门 / 进阶 / 专家）— 深度感知 prompt
- [x] 语音合成（Edge TTS LRU 缓存 + 1-segment 预取）
- [x] 语音识别（WebM→WAV 转码，解决浏览器格式问题）
- [x] 语音观测性（/voice/health + /voice/metrics）
- [x] 生产部署（nginx 反代 + systemd 进程守护）

## 下一步

1. 配置 Moonshot API Key，开启 AI 聊天功能
2. 申请并配置火山 TTS V3（当前使用 Edge TTS 兜底）
3. 绑定域名 + HTTPS（Let's Encrypt）
4. 添加更多展品数据

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11, FastAPI, Uvicorn, Pydantic v2 |
| 数据验证 | JSON Schema 2020-12, jsonschema |
| 语音合成 | Edge-TTS (主), 火山引擎 TTS V3 (备) |
| 语音识别 | 火山引擎 SAUC bigmodel WebSocket |
| 前端 | React 18, TypeScript, Vite, Tailwind CSS |
| Web 服务器 | nginx (反向代理 + 静态文件) |
| 进程管理 | systemd |
| 代码托管 | GitHub (binchenz/ai_travel_guide) |
