# Theia

论文 PDF 到讲解视频 Agent。使用 MinerU 解析学术论文，通过多 Agent LLM 管道提取关键信息并生成视频脚本，Edge TTS 合成旁白，Remotion 渲染为带动画的讲解视频。

## 架构

```
PDF → MinerU (解析) → LLM 多遍提取 → 多 Agent 脚本 → Edge TTS → Remotion → MP4

┌───────────────────────────────────────────────────────────────┐
│  Vue 3 前端  ←→  FastAPI 后端  ←→  LangGraph 管道             │
│  (上传/配置/进度/预览)  (SSE 实时推送)   (6 步流水线)           │
│                                                               │
│  交互模式: 每步可暂停 → 用户审核/编辑 → 继续                    │
│  批量模式: PDF 进 → MP4 出，全程自动                            │
└───────────────────────────────────────────────────────────────┘
```

### 多 Agent 脚本生成

```
PaperSummary
    ↓
Story Architect (场景规划 + 叙事弧线)
    ↓
Scene Writer (旁白文本 + 注意力标注)
    ↓
Visual Director (动画编排，规则引擎)
    ↓
Pacing Reviewer (时长校验 + 节奏平衡)
    ↓
VideoScript
```

## 前置要求

- Python 3.11+、[uv](https://github.com/astral-sh/uv)
- Node.js 18+、pnpm

## 快速开始

```bash
# 1. 安装依赖
cd packages/agent  && uv pip install -e .
cd packages/server && uv pip install -e .
cd packages/video  && pnpm install
cd packages/web    && pnpm install

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 设置 THEIA_API_KEY (默认 Kimi)、MINERU_API_KEY 等

# 3. 启动服务
cd packages/server && uv run uvicorn server.main:app --reload --port 8000
cd packages/web    && pnpm dev

# 4. 打开 http://localhost:5173/
```

设置了 `MINERU_API_KEY` 时使用 mineru.net 云端 API（推荐快速上手），否则回退到本地 MinerU。

## 命令行

```bash
theia render paper.pdf -o output.mp4                    # 完整流水线
theia render paper.pdf --preset portrait                # 竖屏 9:16
theia render paper.pdf --preset bilibili                # B站横屏
theia parse paper.pdf -o ./workspace/parsed             # 仅解析
theia extract paper.pdf -m kimi-k2-0905-preview         # 解析 + 提取
```

## 项目结构

```
packages/
├── agent/     # LangGraph 管道
│   └── theia/
│       ├── extraction/   # 多遍提取、图表分析、表格分析
│       ├── llm/          # LLM 统一调用层与多模型配置
│       ├── output/       # 多 Agent 脚本生成、TTS、渲染
│       ├── parsing/      # PDF / 网页 / 知乎解析
│       ├── quality/      # 质量评估与自动修复
│       └── prompts/      # 提示词模板
├── server/    # FastAPI 后端（任务管理、SSE、REST API）
├── video/     # Remotion 视频引擎（15 种场景、21 个组件）
└── web/       # Vue 3 前端（上传/配置/进度/审核/预览）
```

各模块详细文档见对应目录的 README。

## 视频预设

| 预设 | 尺寸 | 适用平台 |
|------|------|---------|
| `landscape` | 1920×1080 | YouTube |
| `bilibili` | 1920×1080 | B站 |
| `portrait` | 1080×1920 | 通用竖屏 |
| `douyin` | 1080×1920 | 抖音 |
| `xiaohongshu` | 1080×1440 | 小红书 |
| `square` | 1080×1080 | 微博、Instagram |

## 核心技术

| 层 | 技术 |
|------|-----------|
| Agent 框架 | LangGraph |
| PDF 解析 | MinerU（云端 API / 本地） |
| LLM | LiteLLM（Kimi / OpenAI / Anthropic / DeepSeek / SiliconFlow / Ollama） |
| TTS | edge-tts |
| 视频渲染 | Remotion 4 (React 19) + KaTeX |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 前端 | Vue 3 + Element Plus + Vite 6 |
| 数据模型 | Pydantic (Python) + Zod (TypeScript) |

## 环境变量

所有步骤默认使用 Kimi (Moonshot AI) 模型。每个步骤可独立配置 `MODEL / API_KEY / API_BASE`，未设置时回退到通用凭据。

### 通用配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `THEIA_API_KEY` | 通用 LLM API Key（所有步骤的后备） | — |
| `THEIA_API_BASE` | 通用 LLM API 端点 | `https://api.moonshot.cn/v1` |
| `THEIA_LANGUAGE` | 输出语言 | `zh` |
| `THEIA_FPS` | 视频帧率 | `30` |
| `THEIA_TTS_VOICE` | TTS 语音 | `zh-CN-YunxiNeural` |
| `THEIA_NARRATION_STYLE` | 旁白风格（default/academic/story/popsci） | `default` |
| `THEIA_THEME` | 视觉主题（academic/popsci） | `academic` |
| `MINERU_API_KEY` | MinerU 云端 API Key | — |

### 各步骤模型

| 变量 | 步骤 | 默认模型 |
|------|------|---------|
| `THEIA_SCAN_MODEL` | Pass 1 快速扫描 | `kimi-k2-0905-preview` |
| `THEIA_EXTRACT_MODEL` | Pass 2 深度提取 | `kimi-k2-0905-preview` |
| `THEIA_FIGURE_MODEL` | 图表分析（需多模态） | `kimi-k2.5` |
| `THEIA_STORY_MODEL` | 故事架构师 | `kimi-k2-0905-preview` |
| `THEIA_SCENE_MODEL` | 场景编剧 | `kimi-k2-0905-preview` |
| `THEIA_GATE_MODEL` | 质量门控修复 | `kimi-k2-0905-preview` |
| `THEIA_JUDGE_MODEL` | L3 深度评估 | `kimi-k2-0905-preview` |

每个步骤还支持 `THEIA_{STEP}_API_KEY` 和 `THEIA_{STEP}_API_BASE`，未设置时回退到 `THEIA_API_KEY` / `THEIA_API_BASE`。

### LLM 速率限制

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `THEIA_LLM_MAX_CONCURRENT` | 最大并发请求数 | `3` |
| `THEIA_LLM_MIN_INTERVAL` | 请求最小间隔（秒） | `0.5` |
