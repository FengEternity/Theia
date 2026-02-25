# Theia

论文 PDF 到讲解视频 Agent。使用 MinerU 解析学术论文，通过 LLM 提取关键信息并生成视频脚本，Edge TTS 合成旁白，Remotion 渲染为带动画的讲解视频。

## 架构

```
PDF → MinerU (解析) → LLM (提取) → LLM (脚本) → Edge TTS (旁白) → Remotion (渲染) → MP4

┌───────────────────────────────────────────────────────────────┐
│  Vue 3 前端  ←→  FastAPI 后端  ←→  LangGraph 管道             │
│  (上传/配置/进度/预览)  (SSE 实时推送)   (5 步流水线)           │
│                                                               │
│  交互模式: 每步可暂停 → 用户审核/编辑 → 继续                    │
│  批量模式: PDF 进 → MP4 出，全程自动                            │
└───────────────────────────────────────────────────────────────┘
```

## 前置要求

- Python 3.11+、[uv](https://github.com/astral-sh/uv)
- Node.js 18+、pnpm 或 npm

## 快速开始

```bash
# 1. 安装依赖
cd packages/agent  && uv pip install -e .
cd packages/server && uv pip install -e .
cd packages/video  && pnpm install
cd packages/web    && npm install

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 设置 LLM API Key 和 MINERU_API_KEY

# 3. 启动服务
cd packages/server && uv run uvicorn server.main:app --reload --port 8000
cd packages/web    && npm run dev

# 4. 打开 http://localhost:5173/
```

设置了 `MINERU_API_KEY` 时使用 mineru.net 云端 API（推荐快速上手），否则回退到本地 MinerU。

## 命令行

```bash
theia render paper.pdf -o output.mp4                    # 完整流水线
theia render paper.pdf --preset portrait                # 竖屏 9:16
theia parse paper.pdf -o ./workspace/parsed             # 仅解析
theia extract paper.pdf -m gpt-4o                       # 解析 + 提取
```

## 项目结构

```
packages/
├── agent/     # LangGraph 管道（解析→提取→脚本→TTS→渲染）
├── server/    # FastAPI 后端（任务管理、SSE、REST API）
├── video/     # Remotion 视频引擎（15 种场景、18 种组件）
└── web/       # Vue 3 前端（上传/配置/进度/审核/预览）
```

各模块详细文档见对应目录的 README。

## 视频预设

| 预设 | 尺寸 | 适用平台 |
|------|------|---------|
| `landscape` | 1920×1080 | YouTube、B站 |
| `portrait` | 1080×1920 | 抖音 |
| `xiaohongshu` | 1080×1440 | 小红书 |
| `square` | 1080×1080 | 微博、Instagram |

## 核心技术

| 层 | 技术 |
|------|-----------|
| Agent 框架 | LangGraph |
| PDF 解析 | MinerU |
| LLM | LiteLLM（OpenAI / Anthropic / DeepSeek / Ollama / Azure） |
| TTS | edge-tts |
| 视频渲染 | Remotion (React) + KaTeX |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 前端 | Vue 3 + Element Plus |
| 数据模型 | Pydantic (Python) + Zod (TypeScript) |

## 成本优化

| 步骤 | 默认模型 | 原因 |
|------|---------|------|
| 信息提取 | `gpt-4o` | 需要高准确性 |
| 脚本生成 | `gpt-4o-mini` | 轻量模型即可 |

通过 `THEIA_EXTRACT_MODEL` / `THEIA_SCRIPT_MODEL` 环境变量覆盖。

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `THEIA_LLM_MODEL` | 默认 LLM 模型 | `gpt-4o` |
| `THEIA_EXTRACT_MODEL` | 信息提取模型 | `gpt-4o` |
| `THEIA_SCRIPT_MODEL` | 脚本生成模型 | `gpt-4o-mini` |
| `THEIA_LANGUAGE` | 输出语言 | `zh` |
| `THEIA_FPS` | 视频帧率 | `30` |
| `THEIA_TTS_VOICE` | TTS 语音 | `zh-CN-YunxiNeural` |
| `THEIA_WORKSPACE` | 工作空间路径 | `workspace/` |
| `MINERU_API_KEY` | MinerU 云端 API Key | — |
| `OPENAI_API_KEY` | OpenAI API Key | — |
