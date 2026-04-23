# 上海博物馆电子导游 Agent 设计方案

**日期**: 2026-04-22  
**版本**: v1.0  
**状态**: 已批准

---

## 1. 项目概述

为上海博物馆入境游客提供基于 AI Agent 的电子导游服务，替代传统预录音频讲解器，实现"像真人导游一样"的个性化、交互式参观体验。

### 1.1 核心差异化

| 维度 | 传统语音讲解器 | 本方案 AI 导游 Agent |
|------|--------------|-------------------|
| 交互方式 | 单向播放 | 双向对话 |
| 内容深度 | 固定不变 | 由浅入深，动态调整 |
| 个性化 | 无 | 基于游客背景和兴趣定制 |
| 连续性 | 孤立片段 | 跨展品关联，构建完整认知 |

### 1.2 约束条件

- 上海博物馆不允许第三方导游进入
- 游客需使用自有手机设备
- 馆内 GPS 信号弱，需替代定位方案
- 目标用户为英语为主、中文为辅的入境游客

---

## 2. 需求分析

### 2.1 用户画像

**主要用户**: 英语国家入境游客，对中国文化了解有限  
**次要用户**: 中文用户（本地游客或华人）  
**使用场景**: 博物馆现场参观，边走边聊

### 2.2 功能需求

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 展品讲解 | 基于展品提供定制化讲解内容 |
| P0 | 双向对话 | 游客可提问，Agent 回答 |
| P0 | 深度调节 | 根据游客反应调整讲解深度 |
| P1 | 展品识别 | 支持拍照识别或手动选择 |
| P1 | 语音交互 | TTS 播报 + STT 语音输入 |
| P2 | 路线推荐 | 基于时间和兴趣推荐参观路线 |
| P2 | 社交分享 | 生成个性化参观报告 |

### 2.3 非功能需求

- **性能**: 首屏加载 < 3s，对话响应 < 5s
- **可用性**: 支持弱网/离线降级
- **可扩展性**: 本体论框架支持多博物馆复用
- **准确性**: 核心事实零幻觉

---

## 3. 系统架构

### 3.1 总体架构

```
+---------------------+
|     前端 Web App     |
|  (React + TypeScript)|
+---------------------+
           |
           | HTTPS
           v
+---------------------+
|     后端 API         |
|   (Python/FastAPI)   |
+---------------------+
           |
     +-----+-----+
     |           |
     v           v
+---------+  +---------+
| 游客状态 |  | 本体论  |
|  管理    |  | 知识库  |
+---------+  +---------+
     |
     v
+---------+
| LLM 服务 |
| (GPT-4o) |
+---------+
```

### 3.2 组件职责

| 组件 | 职责 |
|------|------|
| 前端 Web App | 用户界面、语音交互、本地缓存 |
| 后端 API | 请求路由、状态管理、Prompt 组装、事实校验 |
| 游客状态管理 | 维护会话状态、游客画像、参观历史 |
| 本体论知识库 | 展品结构化数据、关系图谱、分层故事线 |
| LLM 服务 | 自然语言生成、多语言处理、视觉识别 |

---

## 4. 本体论知识框架

### 4.1 设计原则

采用**轻量级本体论**（Lightweight Ontology），在灵活性和结构性之间取得平衡：

- 用 JSON-LD 表示，易于扩展和解析
- 每个展品包含**事实层**（客观数据）和**叙事层**（分层故事线）
- 定义展品间关系，支持联想推荐

### 4.2 展品本体结构

```json
{
  "@context": "https://museum-ontology.shanghai-museum.org/",
  "@id": "artifact/da-ke-ding",
  "@type": "BronzeWare",
  "name": {
    "en": "Da Ke Ding",
    "zh": "大克鼎"
  },
  "dynasty": "Western Zhou",
  "period": "10th century BCE",
  "dimensions": {
    "height": "93.1cm",
    "weight": "201.5kg"
  },
  "material": ["bronze", "tin", "lead"],
  "techniques": ["piece-mold casting"],
  "inscriptions": {
    "content": "...",
    "characterCount": 290,
    "significance": "records land grants and rituals"
  },
  "culturalContext": {
    "ritualUse": "ancestral worship",
    "socialFunction": "symbol of aristocratic status",
    "relatedConcepts": ["ritual bronze system", "Zhou li", "feudal system"]
  },
  "storylines": {
    "entry": {
      "theme": "power and ritual",
      "hook": "Imagine a vessel so precious that it survived 3,000 years...",
      "keyPoints": ["size and weight impression", "basic ritual use", "survival story"]
    },
    "deeper": {
      "theme": "history decoded",
      "focus": "The 290-character inscription reveals...",
      "keyPoints": ["inscription content", "land grant system", "family lineage"]
    },
    "expert": {
      "theme": "art and craft",
      "focus": "Regional variations in metallurgical traditions...",
      "keyPoints": ["casting technique analysis", "alloy composition", "stylistic comparison"]
    }
  },
  "relationships": {
    "sameDynasty": ["artifact/mao-gong-ding", "artifact/san-shi-pan"],
    "sameTechnique": ["artifact/si-yang-fang-zun"],
    "sameTheme": ["artifact/li-gui"]
  }
}
```

### 4.3 本体扩展机制

```
BaseEntity
├── Artifact
│   ├── BronzeWare
│   ├── Ceramic
│   ├── Painting
│   ├── Calligraphy
│   └── Sculpture
├── Dynasty
├── Technique
├── Concept
└── Person
```

新展品类型通过继承 `Artifact` 基类并添加特定属性实现。

---

## 5. 导游 Agent 设计

### 5.1 游客状态机

```typescript
interface VisitorState {
  sessionId: string;
  language: 'en' | 'zh';
  cultureBackground: 'limited_chinese_knowledge' | 'some_chinese_knowledge' | 'familiar';
  visitedExhibits: string[];  // 已参观展品 ID 列表
  currentExhibit: string | null;
  interests: string[];  // 兴趣标签，如 ['bronze_casting', 'calligraphy']
  depthLevel: 'entry' | 'deeper' | 'expert';
  turnCount: number;  // 当前展品对话轮次
  totalTurnCount: number;  // 总会话轮次
}
```

### 5.2 对话策略

**状态转换规则**:

| 条件 | 动作 |
|------|------|
| 首次接触展品 | 使用 `storylines.entry`，设置 `turnCount = 0` |
| 游客提问深入问题 | 提升到 `deeper`，若已在 `deeper` 则提升到 `expert` |
| 游客表现出兴趣标签 | 记录兴趣，后续主动推荐相关展品 |
| 对话轮次 > 5 且无深入问题 | 主动推荐关联展品或询问是否换展品 |
| 游客表示不理解 | 降级到 `entry`，用更通俗的语言解释 |

### 5.3 Prompt 工程

**系统 Prompt 模板**:

```
You are a knowledgeable and engaging museum guide at the Shanghai Museum. 
Your goal is to provide a personalized, immersive experience for international visitors.

## Visitor Profile
- Language: {language}
- Cultural Background: {cultureBackground}
- Current Depth Level: {depthLevel}
- Interests: {interests}
- Previously Visited: {visitedExhibits}

## Current Exhibit
{exhibitOntology}  // 注入展品本体数据

## Rules
1. ONLY use facts from the provided exhibit ontology. Do NOT invent dates, measurements, or historical claims.
2. Adjust your explanation depth based on the visitor's level. Start simple, go deeper only when they show interest.
3. Use analogies to Western culture when helpful for understanding.
4. Keep responses concise (2-3 paragraphs max) unless the visitor asks for more detail.
5. If uncertain, say "According to current scholarship..." or "This remains a topic of debate among researchers..."
6. When appropriate, suggest related exhibits: {relatedExhibits}

## Conversation History
{history}

Visitor: {userInput}
Guide:
```

---

## 6. 前端交互设计

### 6.1 页面流程

```
扫码进入
  └── 语言选择 (EN/CN)
        └── 首页（展厅列表 / 拍照识别）
              └── 展品详情页（对话界面）
                    ├── 文字对话
                    ├── 语音输入/播报
                    ├── 展品信息卡片
                    └── 快捷问题按钮
```

### 6.2 对话界面

- **类聊天界面**：用户消息在右，Agent 消息在左
- **展品卡片**：顶部固定展示当前展品图片和基本信息
- **快捷问题**：根据展品动态生成，如 "Tell me more about the inscription", "How was this made?"
- **语音按钮**：支持按住说话和点击播放

### 6.3 离线支持

- Service Worker 缓存核心本体数据
- 已加载的展品内容可离线浏览
- 对话功能网络恢复后自动同步

---

## 7. Demo 阶段定位方案

### 7.1 方案对比

| 方案 | 实现方式 | 准确度 | 用户体验 | Demo 可行性 |
|------|---------|--------|---------|------------|
| 手动选择 | 展厅/展品列表 | 100% | 一般 | 高 |
| 拍照识别 | 多模态 LLM / Vision API | 70-85% | 好 | 中 |
| 二维码扫描 | 展品旁贴二维码 | 100% | 好 | 需馆方配合 |

### 7.2 Demo 推荐策略

**主路径**: 手动选择（保底，确保 Demo 稳定）  
**亮点功能**: 拍照识别（展示技术能力，但提供候选确认机制）  
**正式部署**: 蓝牙信标（需硬件部署，后期实施）

### 7.3 拍照识别流程

```
用户拍照上传
    └── 后端调用 Vision API
          └── 返回候选展品列表（Top 3）
                └── 用户确认或重新选择
                      └── 进入对话
```

---

## 8. 技术栈

### 8.1 选型决策

| 层级 | 技术 | 选型理由 |
|------|------|---------|
| 前端框架 | React 18 + TypeScript | 生态成熟，团队熟悉度高 |
| 样式方案 | Tailwind CSS | 快速开发，一致性强 |
| 状态管理 | Zustand | 轻量，适合本项目规模 |
| 后端框架 | Python + FastAPI | AI 生态丰富，异步性能好 |
| LLM | OpenAI GPT-4o | 多语言强，支持视觉，性价比高 |
| 语音 | Web Speech API (前端) + Azure TTS (备选) | 免费 + 高质量备选 |
| 数据库 | 内存/JSON 文件 (Demo) → PostgreSQL (生产) | 渐进扩展 |
| 部署 | Vercel (前端) + Render (后端) | 快速上线，成本可控 |

### 8.2 开发环境

- Node.js 20+
- Python 3.11+
- pnpm / npm
- uv / pip

---

## 9. 数据流

### 9.1 讲解请求流程

```
[用户] 选择展品 / 拍照 / 提问
   |
   v
[前端] 组装请求 { exhibitId, userInput, sessionId }
   |
   v
[后端] 1. 查询游客状态
      2. 查询展品本体
      3. 更新状态机（深度、兴趣等）
      4. 组装 Prompt
   |
   v
[LLM] 生成回复
   |
   v
[后端] 1. 事实校验（关键词匹配）
      2. 保存会话历史
      3. 返回响应
   |
   v
[前端] 渲染消息 + TTS 播报
```

### 9.2 状态持久化

- **短期**: 内存存储（Demo 阶段）
- **中期**: Redis（会话缓存）
- **长期**: PostgreSQL + 定期归档

---

## 10. 防幻觉机制

### 10.1 三层防护

```
Layer 1: Prompt 约束
├── 明确注入展品本体数据
├── 指令: "ONLY use provided facts"
└── 禁止编造年代、尺寸、历史事件

Layer 2: 后处理校验
├── 正则匹配：检查数字、年代是否在本体中
├── 关键词黑名单："可能", "也许", "据说" → 替换为置信度标注
└── 事实比对：提取命名实体，与本体核对

Layer 3: 置信度标注
├── 确定事实：直接陈述
├── 学术推测：标注 "According to current scholarship..."
└── 无法验证：标注 "This remains a topic of debate..."
```

### 10.2 人工审核流程

- Demo 阶段：所有生成内容抽样审核
- 生产阶段：建立反馈通道，游客可标记"不准确"
- 定期用审核结果微调 Prompt 和本体数据

---

## 11. 分阶段实施计划

### Phase 1: MVP (Week 1-2)

**目标**: 验证核心体验，可演示

**范围**:
- 5 件核心展品（大克鼎、商鞅方升等）
- 简单 JSON 本体（无复杂关系）
- 手动选择触发
- 文本对话为主
- 英文支持

**交付物**:
- 可访问的 Web Demo
- 基础对话功能
- 简单的游客状态跟踪

### Phase 2: 完善 (Week 3-4)

**目标**: 完整体验单展厅

**范围**:
- 扩展到青铜馆 15 件展品
- 完整本体论框架（含关系定义）
- 拍照识别功能
- 中文支持
- 语音交互（TTS）

**交付物**:
- 青铜馆完整导览
- 拍照识别 Demo
- 双语支持

### Phase 3: 增强 (Week 5-8)

**目标**: 产品级体验

**范围**:
- 多展厅覆盖
- 路线推荐
- 蓝牙信标集成
- 社交分享
- 数据分析后台

**交付物**:
- 完整产品
- 运营后台
- 部署文档

---

## 12. 风险与缓解措施

| 风险 | 影响 | 可能性 | 缓解措施 |
|------|------|--------|---------|
| LLM 产生幻觉 | 高 | 中 | 本体约束 + 事实校验 + 置信度标注 |
| 馆内网络不稳定 | 高 | 高 | 前端缓存 + 离线降级模式 |
| 拍照识别准确率低 | 中 | 中 | 候选确认机制 + 手动选择保底 |
| 本体构建工作量超预期 | 中 | 高 | 聚焦单展厅 MVP，LLM 辅助提取 |
| API 调用成本过高 | 中 | 低 | 缓存策略 + 限流 + 降级到静态内容 |
| 上博合作受阻 | 高 | 中 | 先以公开信息构建 Demo，再寻求合作 |
| 游客接受度低 | 高 | 中 | 早期用户测试，快速迭代 |

---

## 13. 成功指标

| 指标 | MVP 目标 | 产品目标 |
|------|---------|---------|
| 对话完成率 | > 70% | > 85% |
| 平均对话轮次 | > 3 轮 | > 5 轮 |
| 用户满意度 | > 3.5/5 | > 4.2/5 |
| 幻觉投诉率 | < 10% | < 2% |
| 页面加载时间 | < 5s | < 3s |
| 对话响应时间 | < 8s | < 5s |

---

## 14. 附录

### 14.1 术语表

| 术语 | 说明 |
|------|------|
| 本体论 (Ontology) | 对领域知识的形式化、结构化描述 |
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| TTS | Text-to-Speech，文字转语音 |
| STT | Speech-to-Text，语音转文字 |
| iBeacon | 蓝牙低功耗信标，用于室内定位 |

### 14.2 参考资源

- 上海博物馆官网: https://www.shanghaimuseum.net/
- JSON-LD 规范: https://json-ld.org/
- OpenAI API 文档: https://platform.openai.com/docs

---

*本文档由 AI 辅助生成，经人工审核确认。*
