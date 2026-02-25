# Theia 技术方案设计文档

## 1. 项目概述

Theia 是一个端到端的论文讲解视频生成 Agent。它接收一篇学术论文 PDF 作为输入，经过解析、信息抽取、脚本编写、语音合成、视频渲染五个阶段，最终输出一个带旁白的动态信息图风格讲解视频（MP4）。

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Theia 系统架构                                 │
│                                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────────────────────┐    │
│  │   Vue 3 前端 (Web)   │←→│      FastAPI 后端 (Server)               │    │
│  │                       │    │                                         │    │
│  │  上传页 / 配置面板    │HTTP│  POST /api/tasks → 创建任务             │    │
│  │  任务列表 / 状态标签  │ +  │  GET  /api/tasks/{id}/events → SSE     │    │
│  │  实时进度 / 视频预览  │SSE │  GET  /api/tasks/{id}/video → 下载     │    │
│  └─────────────────────┘    │  TaskManager → 后台线程 → run_pipeline  │    │
│                               └──────────────┬──────────────────────────┘    │
│                                              │                               │
│  ┌───────────────────────────────────────────┼──────────────────────────┐   │
│  │                    Theia Agent (Python)    │                          │   │
│  │                                           ↓                          │   │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌─────────┐          │   │
│  │  │  MinerU   │→│ LLM       │→│ Script      │→│ Edge    │          │   │
│  │  │  Parser   │  │ Extractor │  │ Writer     │  │ TTS     │          │   │
│  │  └──────────┘  └───────────┘  └────────────┘  └─────────┘          │   │
│  │       ↓              ↓              ↓              ↓                 │   │
│  │   Markdown      PaperSummary   VideoScript    Audio Files           │   │
│  │   + Images      (JSON)         (JSON)         (.mp3)                │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────┐                       │   │
│  │  │       LangGraph Pipeline Orchestrator     │                       │   │
│  │  │     (pipeline.py + cache.py + cli.py)     │                       │   │
│  │  └──────────────────────────────────────────┘                       │   │
│  │                        │                                             │   │
│  │                   subprocess                                         │   │
│  │                        ↓                                             │   │
│  │  ┌──────────────────────────────────────────┐                       │   │
│  │  │        Remotion Renderer (Node.js)        │                       │   │
│  │  │  React 场景组件 + 动画 + 音频 → MP4        │                       │   │
│  │  └──────────────────────────────────────────┘                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| **Agent 框架** | **LangGraph** | DAG 编排，支持条件路由/人机交互/状态持久化，为未来扩展预留 |
| 主编排语言 | Python | MinerU/LiteLLM/edge-tts 均为 Python 生态，编排能力强 |
| 视频渲染 | Node.js (Remotion) | 唯一成熟的代码驱动视频方案，React 组件即帧 |
| 跨语言通信 | JSON 文件 + subprocess | 简单可靠，无需维护 RPC/HTTP 服务 |
| LLM 接入 | LiteLLM | 统一接口支持 10+ 提供商，零切换成本 |
| 数据契约 | Pydantic (Python) + Zod (TypeScript) | 双端类型安全，运行时校验 |
| **Web 后端** | **FastAPI** | 异步 HTTP API + SSE 实时进度推送，后台线程管理管道任务 |
| **Web 前端** | **Vue 3 + Element Plus** | 上传/配置/实时进度可视化/视频预览，TypeScript 类型安全 |
| 进度推送 | SSE (Server-Sent Events) | 单向推送，比 WebSocket 更简单，满足进度通知需求 |

### 2.2 Agent 框架选型：为什么选 LangGraph

**备选方案对比：**

| 框架 | 优势 | 劣势 | 适用场景 |
|------|------|------|---------|
| **LangGraph** | DAG 编排、状态管理、条件路由、人机交互、持久化 checkpointer | 学习曲线稍高 | 需要复杂流程控制的 Agent |
| CrewAI | 多 Agent 协作、角色定义简单 | 底层依赖 LangChain，灵活性有限 | 多角色分工场景 |
| Pydantic AI | 轻量、与 Pydantic 深度集成 | 生态较新，编排能力弱 | 简单 Agent |
| Dify | 可视化编排、低代码 | 重量级、需要部署服务 | 非开发者使用 |
| 自研 | 完全可控 | 需自行实现状态管理/重试/路由 | 极简场景 |

**选择 LangGraph 的理由：**

1. **v1 足够简单**：线性 StateGraph 5 个节点直连，代码量与纯函数方案相当
2. **未来扩展零成本**：
   - 条件路由：已内置质量检查（`route_after_extract`，摘要太短自动重试）
   - 人机交互：加 `interrupt()` 即可在任意节点暂停等待用户确认
   - 多 Agent：节点可替换为子 graph 或工具调用 Agent
   - 持久化：加 `InMemorySaver` / `SqliteSaver` 即可断点续跑
3. **状态管理内置**：TypedDict 定义的 `PipelineState` 自动在节点间传递
4. **可观测性**：LangSmith 集成，可追踪每个节点的输入输出

**当前 Graph 结构（v1）：**

```
START → parse_node → extract_node ─┐
                                    ├─→ script_node → tts_node → render_node → END
                   (quality gate) ──┘
                   (summary 太短则重试)
```

**未来 Graph 结构（v2 规划）：**

```
START → parse_node → extract_node ──→ [人工确认摘要] ──→ script_node
                          ↑                                    │
                          └── (质量不达标重试)                   ↓
                                                        [人工确认脚本]
                                                              │
                                              ┌───────────────┤
                                              ↓               ↓
                                          tts_node      (skip_tts)
                                              │               │
                                              └───────┬───────┘
                                                      ↓
                                                 render_node → END
```

## 3. 技术栈详情

### 3.1 Python Agent 核心

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **Agent 框架** | **LangGraph** | **v1.0+** | **StateGraph 流水线编排、条件路由、状态管理** |
| PDF 解析 | MinerU (magic-pdf) | v2.7+ | 论文 PDF → 结构化 Markdown + 图片 |
| LLM 调用 | LiteLLM | latest | 统一多 provider LLM API |
| 语音合成 | edge-tts | latest | 免费、高质量中英文 TTS |
| 数据模型 | Pydantic | v2.0+ | 类型安全的数据验证和序列化 |
| CLI 框架 | Click | latest | 命令行入口和参数解析 |
| 音频分析 | mutagen | latest | 获取 MP3 精确时长（音画同步关键） |
| 运行时 | Python | 3.10+ | 类型联合语法 (`X | Y`) 支持 |
| 包管理 | uv | latest | 快速依赖安装 |

### 3.2 Node.js 视频渲染引擎

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 视频框架 | Remotion | v4.0+ | React 组件 → 视频帧 → MP4 |
| 转场动画 | @remotion/transitions | v4.0+ | fade/slide 等场景转场 |
| 音频处理 | @remotion/media-utils | v4.0+ | 视频内音频集成 |
| UI 框架 | React | v19.0+ | 声明式 UI 渲染 |
| 公式渲染 | KaTeX | v0.16+ | LaTeX → HTML（数学公式） |
| 类型验证 | Zod | v3.23+ | 运行时 JSON schema 校验 |
| 类型系统 | TypeScript | v5.7+ | 静态类型检查 |
| 包管理 | pnpm | latest | 高效 Node.js 依赖管理 |

### 3.3 支持的 LLM 提供商

通过 LiteLLM 统一接入，仅需设置环境变量即可切换：

| 提供商 | 模型标识符示例 | 环境变量 |
|--------|---------------|---------|
| OpenAI | `gpt-4o`, `gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| DeepSeek | `deepseek/deepseek-chat` | `DEEPSEEK_API_KEY` |
| Ollama (本地) | `ollama/llama3`, `ollama/qwen2` | `OLLAMA_API_BASE` |
| Azure OpenAI | `azure/gpt-4o` | `AZURE_API_KEY` + `AZURE_API_BASE` |

## 4. 数据流与核心模型

### 4.1 五阶段流水线

```
                    Stage 1          Stage 2         Stage 3         Stage 4        Stage 5
                   ┌────────┐      ┌─────────┐     ┌─────────┐    ┌────────┐     ┌─────────┐
  paper.pdf  ───→  │ Parse  │ ───→ │ Extract │ ──→ │ Script  │ ─→ │  TTS   │ ──→ │ Render  │ ──→ video.mp4
                   │ MinerU │      │  LLM    │     │ Writer  │    │ edge   │     │Remotion │
                   └────────┘      └─────────┘     └─────────┘    └────────┘     └─────────┘
                       ↓                ↓               ↓              ↓
                   Markdown +      PaperSummary    VideoScript    Audio files
                   Images          (JSON)          (JSON)         (.mp3)
```

### 4.2 PaperSummary（LLM 抽取结果）

LLM 从论文 Markdown 中抽取的结构化信息：

```
PaperSummary
├── title: str                    # 论文标题
├── authors: list[str]            # 作者列表
├── year: int | None              # 发表年份
├── problem: str                  # 研究问题（2-3 句）
├── method: MethodDetail
│   ├── summary: str              # 方法概述（1 段）
│   ├── key_steps: list[str]      # 方法步骤（有序）
│   └── formulas: list[str]       # 关键公式（LaTeX）
├── results: ResultDetail
│   ├── datasets: list[str]       # 使用的数据集
│   ├── metrics: list[str]        # 关键指标（含数值）
│   └── findings: str             # 实验发现总结
├── conclusion: str               # 结论（1 段）
├── contributions: list[str]      # 核心贡献点
└── figures: list[Figure]         # 关键图表
    ├── path: str
    └── caption: str
```

### 4.3 VideoScript（传给 Remotion 的脚本）

驱动视频渲染的完整脚本：

```
VideoScript
├── meta: VideoMeta
│   ├── fps: 30
│   ├── width: 1920              # 由视频预设决定
│   └── height: 1080
└── scenes: list[Scene]
    ├── type: "title" | "overview" | "method" | "formula" | "figure" | "result" | "conclusion"
    ├── durationInFrames: int     # 精确帧数（由 TTS 音频时长计算）
    ├── narration: str            # 旁白文本
    ├── audioFile: str | null     # 音频文件路径
    └── data: dict                # 场景特定数据负载
```

**视频尺寸预设**：

| 预设 | 尺寸 | 适用平台 |
|------|------|---------|
| `landscape` | 1920×1080 | YouTube、B站 |
| `portrait` | 1080×1920 | 抖音 |
| `xiaohongshu` | 1080×1440 | 小红书 |
| `square` | 1080×1080 | 微博、Instagram |

### 4.4 Python/TypeScript 类型同步

Python 端使用 Pydantic，TypeScript 端使用 Zod，两者保持字段一致：

| Python (snake_case) | TypeScript (camelCase) | 转换层 |
|---------------------|----------------------|--------|
| `PaperSummary` | — (Python 内部) | — |
| `VideoScript` | `VideoScript` | `renderer._to_camel_case_dict()` |
| `Scene.duration_in_frames` | `Scene.durationInFrames` | 自动转换 |
| `Scene.audio_file` | `Scene.audioFile` | 自动转换 |

## 5. 模块详细设计

### 5.1 parser.py — MinerU PDF 解析

**职责**：将 PDF 转为结构化 Markdown + 提取图片。

**核心 API**：
```python
def parse_pdf(pdf_path, output_dir, *, lang="ch", backend="pipeline") -> ParseResult
```

**双模式支持**：

| 模式 | 触发条件 | 优势 | 劣势 |
|------|---------|------|------|
| **本地** | 未设置 `MINERU_API_KEY` | 无网络依赖，隐私安全 | 需安装 mineru + 下载模型 |
| **云端** | 设置了 `MINERU_API_KEY` | 无需 GPU/本地安装，开箱即用 | 需网络，有配额限制 |

**本地后端选择**：
- `pipeline`：纯 CPU，精度约 82%，适合无 GPU 环境
- `hybrid-auto-engine`：GPU 加速，精度约 90%，需 CUDA

**云端 API 流程**（mineru.net）：
1. 通过批量上传接口获取 pre-signed URL
2. PUT 上传 PDF 文件
3. 创建解析任务（POST `/api/v4/extract/task`）
4. 轮询任务状态直到 `done`
5. 下载 ZIP 结果并解压（Markdown + 图片 + content_list）

**输出**：
- Markdown 文本（保留公式 LaTeX、表格 HTML、图片引用）
- 提取的图片文件
- content_list.json（按阅读顺序的内容块列表）

### 5.2 llm_config.py — LLM 配置与工具

**职责**：管理多模型策略、语言检测、智能文本截断。

**分步骤模型策略**：

| 步骤 | 默认模型 | 环境变量 | 理由 |
|------|---------|---------|------|
| 信息抽取 | `gpt-4o` | `THEIA_EXTRACT_MODEL` | 需要高准确性，正确提取结构化信息 |
| 脚本生成 | `gpt-4o-mini` | `THEIA_SCRIPT_MODEL` | 创意生成任务，小模型即可胜任，成本降低 ~90% |

```python
@dataclass
class LLMConfig:
    extract_model: str  # 信息抽取模型
    script_model: str   # 脚本生成模型（默认更便宜）
```

**自动语言检测**：
```python
def detect_language(text: str) -> str  # "zh" or "en"
```
- 基于 CJK 字符占比的轻量检测（无额外依赖，处理 5000 字符样本）
- CJK 占比 > 15% 判定为中文
- 检测结果自动传递给后续步骤（TTS 语音选择、旁白语言等）

**智能截断**：
```python
def smart_truncate(text: str, max_chars: int = 80_000) -> str
```
- 按 Markdown 标题分段
- **优先保留**：Abstract、Introduction、Method、Results、Conclusion
- **优先丢弃**：References、Appendix、Acknowledgements
- 相同 token 预算下信息密度显著提升

### 5.3 extractor.py — LLM 信息抽取

**职责**：调用 LLM 从论文 Markdown 中提取结构化摘要。

**核心 API**：
```python
def extract_paper_summary(markdown_content, *, model="gpt-4o", max_retries=3) -> PaperSummary
```

**关键设计**：
- 使用 `response_format={"type": "json_object"}` 强制 JSON 输出
- System prompt 明确定义输出 schema 和提取指南
- **Few-shot 示例**：在 prompt 中包含完整的输入→输出示例，提升格式一致性
- **智能截断**：调用 `smart_truncate()` 保留高价值段落
- 指数退避重试（2s, 4s, 8s）应对瞬态错误和格式失败
- Pydantic 验证确保输出结构正确

**Prompt 结构**：
```
[system] Schema 定义 + 提取指南
[user]   Few-shot 输入示例
[assistant] "Understood. I will follow this format precisely."
[user]   "Now extract from this paper: {actual_content}"
```

### 5.4 scriptwriter.py — 视频脚本生成

**职责**：将 PaperSummary 转为分场景 VideoScript，生成口语化旁白。

**核心 API**：
```python
def generate_video_script(summary, *, model="gpt-4o-mini", fps=30, language="zh") -> VideoScript
```

**注意**：默认使用 `gpt-4o-mini`，旁白生成是较轻的创意任务。

**场景编排**（7 种场景类型）：
1. **Title**（~5s）：论文标题 + 作者
2. **Overview**（~10-15s）：研究问题 + 贡献点
3. **Method**（~15-20s）：方法步骤概览
4. **Formula**（~10-15s）：关键公式独占全屏展示 + 解释
5. **Figure**（~10-15s）：关键图表独占全屏展示 + 说明
6. **Result**（~10-15s）：数据集 + 指标 + 发现
7. **Conclusion**（~5-10s）：总结 + 要点

**时长估算**：
- 中文：4 字/秒
- 英文：14 字符/秒
- 最终被 TTS 实际音频时长覆盖

### 5.4 tts.py — Edge TTS 语音合成

**职责**：为每个场景生成语音旁白，并回写精确时长。

**核心 API**：
```python
def synthesize_narration(script, audio_dir, *, voice=None, language="zh") -> VideoScript
```

**音画同步机制**：
1. 为每个场景生成独立 MP3 文件
2. 用 mutagen 读取精确音频时长
3. 计算 `duration_in_frames = ceil(duration_seconds * fps)`
4. 回写到 VideoScript，确保视频帧与音频完全同步

**默认语音**：
- 中文：`zh-CN-YunxiNeural`（男声，清晰自然）
- 英文：`en-US-GuyNeural`

### 5.5 renderer.py — Remotion 渲染桥接

**职责**：将 VideoScript 传递给 Remotion CLI 进行视频渲染。

**核心 API**：
```python
def render_video(script, output_path, *, workspace=None) -> Path
```

**跨语言通信**：
1. 将 VideoScript 转为 camelCase JSON
2. 复制音频文件到 Remotion `public/` 目录
3. 通过 `--props` 参数将 JSON 传给 `npx remotion render`
4. subprocess 执行，超时 600 秒

### 5.6 cache.py — 文件缓存

**职责**：避免重复的 MinerU 解析和 LLM 调用。

**缓存键**：`{pdf_stem}_{sha256_hash_16}_{step_name}`

**缓存策略**：
- 基于 PDF 文件 SHA256 前 16 位作为唯一标识
- 缓存 PaperSummary 等 Pydantic 模型的 JSON 序列化
- 存储在 `workspace/.theia_cache/` 目录

### 5.7 pipeline.py — LangGraph 流水线编排

**职责**：基于 LangGraph StateGraph 编排五个步骤，管理状态和路由。

**Graph 状态（TypedDict）**：
```python
class PipelineState(TypedDict, total=False):
    # Input / Config
    pdf_path: str
    workspace: str
    extract_model: str      # 信息抽取模型（默认 gpt-4o）
    script_model: str       # 脚本生成模型（默认 gpt-4o-mini）
    language: str
    # ...

    # Auto-detected
    detected_language: str  # parse_node 自动检测

    # Intermediate results
    markdown_content: str
    paper_summary_json: str
    video_script_json: str

    # Output
    output_video: str
```

**Graph 节点**：
| 节点 | 函数 | 使用模型 | 输入 | 输出 |
|------|------|---------|------|------|
| `parse_node` | MinerU 解析 | — | `pdf_path` | `markdown_content`, `detected_language` |
| `extract_node` | LLM 抽取 | `extract_model` (gpt-4o) | `markdown_content` | `paper_summary_json` |
| `script_node` | 脚本生成 | `script_model` (gpt-4o-mini) | `paper_summary_json` | `video_script_json` |
| `tts_node` | 语音合成 | — | `video_script_json` | 更新 `video_script_json` |
| `render_node` | 视频渲染 | — | `video_script_json` | `output_video` |

**语言自动检测流**：
```
parse_node → detect_language() → detected_language → script_node / tts_node 自动使用
```

**条件路由**：
- `route_after_extract`：摘要质量检查，太短自动重试抽取
- 未来可在任意节点间插入 `interrupt()` 实现人机交互

**核心 API**：
```python
def build_graph(*, with_checkpointer=False) -> StateGraph  # 构建 graph
def run_pipeline(pdf_path, ...) -> dict                     # 执行完整流水线
```

**特性**：
- LangGraph StateGraph 自动管理节点间状态传递
- **分模型策略**：抽取用强模型，脚本用快模型，成本优化 ~50%
- **自动语言检测**：无需手动指定，parse 后自动检测并传递
- 条件路由已内置（质量检查），未来可加更多分支
- 加 `InMemorySaver` 即可启用 checkpoint（断点续跑、人机交互）
- 每个节点保存中间文件到 workspace（便于调试）
- 集成文件缓存（`use_cache=True`）避免重复 LLM 调用

### 5.9 cli.py — 命令行入口

三个子命令：

```
theia render <pdf>    # 完整流水线：PDF → MP4
theia parse <pdf>     # 仅 MinerU 解析
theia extract <pdf>   # 解析 + LLM 抽取（不生成视频）
```

**`render` 命令完整参数**：

```bash
theia render paper.pdf \
  -o output.mp4 \                   # 输出路径
  -m gpt-4o \                       # 默认 LLM 模型
  --extract-model gpt-4o \          # 信息抽取专用模型
  --script-model gpt-4o-mini \      # 脚本生成专用模型（更便宜）
  -l auto \                         # 语言: zh / en / auto（自动检测）
  --voice zh-CN-YunxiNeural \       # TTS 语音
  --backend pipeline \              # MinerU 后端
  --fps 30 \
  --skip-tts \                      # 跳过 TTS
  --skip-render \                   # 跳过渲染
  -v                                # 详细日志
```

## 6. Remotion 视频引擎设计

### 6.1 组件架构

```
Root.tsx                          # Remotion 注册入口
└── PaperVideo.tsx                # 主 Composition
    ├── TransitionSeries          # 场景序列 + 转场
    │   ├── TitleScene.tsx        # 标题场景
    │   ├── OverviewScene.tsx     # 研究概述场景
    │   ├── MethodScene.tsx       # 方法场景
    │   ├── FormulaScene.tsx      # 公式场景（KaTeX 渲染）
    │   ├── FigureScene.tsx       # 图表场景（全屏展示）
    │   ├── ResultScene.tsx       # 结果场景
    │   └── ConclusionScene.tsx   # 结论场景
    └── ProgressBar.tsx           # 全局进度条

通用组件：
├── BarChart.tsx                  # 动画水平柱状图
├── DataTable.tsx                 # 动画数据表格
├── HighlightText.tsx             # 关键词高亮文本
└── ProgressBar.tsx               # 底部进度条

Hooks：
└── useScale.ts                   # 响应式缩放（适配多尺寸/竖屏/横屏）
```

### 6.2 响应式布局系统

通过 `useScale` Hook 实现多尺寸自适应：

```typescript
export function useScale() {
  const { width, height } = useVideoConfig();
  const isPortrait = height > width;
  const scale = isPortrait ? Math.max(0.8, width / 1080) : Math.max(0.8, width / 1920);
  const s = (px: number) => Math.round(px * scale);
  // 竖屏模式预留 12% 顶底安全区域
  const padV = isPortrait ? Math.round(height * 0.12) : s(50);
  return { s, pad, isPortrait, isSquare, ... };
}
```

- 横屏基准: 1920px 宽 → `scale = 1.0`
- 竖屏基准: 1080px 宽 → `scale = 1.0`（不缩小，保证字号够大）
- 所有场景组件根据 `isPortrait` 动态切换 flex 方向和元素排列
- 字号、间距、内边距均通过 `s()` 函数动态缩放

### 6.3 动画系统

| 动画类型 | Remotion API | 用途 |
|---------|-------------|------|
| 线性插值 | `interpolate()` | 透明度、位移、缩放 |
| 弹性动画 | `spring()` | 列表项弹入、卡片缩放 |
| 转场 | `TransitionSeries` + `fade()`/`slide()` | 场景间过渡 |

**转场策略**：奇偶场景交替使用 `fade()` 和 `slide({ direction: "from-right" })`。

### 6.4 视觉风格

- **配色**：深色背景（Slate 900/800），亮色文本，蓝紫色强调
- **背景**：135° 线性渐变（`#0f172a` → `#1e293b`）
- **标题场景**：蓝紫渐变装饰线 + 大字标题居中
- **数据场景**：绿色系强调色（`#10b981`）
- **结论场景**：琥珀色系（`#f59e0b`）
- **字体**：system-ui, sans-serif

## 7. 运行时目录结构

```
workspace/
├── parsed/
│   ├── {stem}/                   # MinerU 输出
│   │   └── pipeline/
│   │       ├── {stem}.md
│   │       ├── images/
│   │       └── {stem}_content_list.json
│   └── {stem}.md                 # 复制的 Markdown
├── scripts/
│   ├── {stem}_summary.json       # LLM 抽取结果
│   └── {stem}_script.json        # 最终视频脚本
├── audio/
│   ├── scene_0.mp3               # 各场景音频
│   ├── scene_1.mp3
│   └── ...
├── output/
│   └── {stem}.mp4                # 最终视频
└── .theia_cache/                 # 缓存目录
    └── {stem}_{hash}_{step}.json
```

## 8. Web 前端与 API 服务

### 8.1 FastAPI 后端 (packages/server/)

**职责**：为 Vue 前端提供 HTTP API，管理异步任务，通过 SSE 推送实时进度。

**代码结构**：
```
packages/server/
├── server/
│   ├── main.py            # FastAPI 应用入口、CORS 配置
│   ├── routes.py          # 7 个 API 端点
│   ├── task_manager.py    # 任务调度 + 进度捕获 + SSE 事件流
│   └── models.py          # Pydantic 请求/响应模型
└── pyproject.toml
```

**API 端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks` | 上传 PDF + 配置 JSON，创建异步任务 |
| GET | `/api/tasks` | 获取所有任务列表（按创建时间倒序） |
| GET | `/api/tasks/{id}` | 获取单个任务详情 |
| GET | `/api/tasks/{id}/events` | SSE 实时推送进度事件 |
| GET | `/api/tasks/{id}/video` | 流式传输/下载生成的视频 |
| GET | `/api/presets` | 获取可用视频尺寸预设 |
| DELETE | `/api/tasks/{id}` | 删除任务及工作目录 |

**任务生命周期**：

```
创建任务 (POST /api/tasks)
    → 保存 PDF 到 workspace/tasks/{id}/input/
    → 启动后台线程
    → 线程内调用 run_pipeline()
    → 自定义 logging handler 拦截 "步骤 X/5" 日志
    → 更新任务状态 + 推送 SSE 事件
    → 完成/失败时终止 SSE 流
```

**任务状态**：

| 状态 | 进度 | 说明 |
|------|------|------|
| `pending` | 0% | 等待开始 |
| `parsing` | 10% | MinerU PDF 解析中 |
| `extracting` | 30% | LLM 信息提取中 |
| `scripting` | 50% | 脚本生成中 |
| `tts` | 70% | 语音合成中 |
| `rendering` | 85% | Remotion 视频渲染中 |
| `completed` | 100% | 已完成 |
| `failed` | -1 | 执行失败 |

**进度捕获机制**：

通过自定义 `_PipelineLogHandler`（继承 `logging.Handler`）注入到 `theia.pipeline` 的 logger 中，正则匹配 `步骤\s*(\d)/5` 来实时更新任务阶段。每次状态变更通过 `asyncio.Queue` 推送给所有 SSE 订阅者。

**SSE 事件格式**：

```json
{
  "stage": "extracting",
  "progress": 30,
  "stage_label": "信息提取中",
  "message": "步骤 2/5: 使用 LLM 提取论文信息",
  "video_path": null,
  "error": null
}
```

### 8.2 Vue 3 前端 (packages/web/)

**技术栈**：Vue 3 + TypeScript + Vite + Vue Router + Element Plus + axios

**代码结构**：
```
packages/web/
├── src/
│   ├── App.vue              # 顶部导航栏 + 路由出口
│   ├── main.ts              # 应用入口、注册 Element Plus
│   ├── router/index.ts      # 路由配置（3 个视图）
│   ├── api/
│   │   ├── client.ts        # axios 封装 + API 调用函数
│   │   └── types.ts         # TypeScript 类型定义
│   └── views/
│       ├── UploadView.vue   # PDF 上传 + 配置面板
│       ├── TaskListView.vue # 任务列表表格
│       └── TaskDetailView.vue # 任务详情 + 进度 + 视频预览
├── vite.config.ts           # Vite 配置 + /api 代理
├── index.html
└── package.json
```

**页面功能**：

**上传页 (`/`)**：
- 拖拽/点击上传 PDF 文件
- 配置面板：视频尺寸预设、旁白语言、帧率、TTS 开关
- 预设列表从后端 `/api/presets` 动态加载
- 提交后自动跳转到任务详情页

**任务列表 (`/tasks`)**：
- Element Plus 表格：文件名、状态标签、进度条、创建时间、操作
- 5 秒自动轮询刷新
- 删除任务时弹出确认对话框

**任务详情 (`/tasks/:id`)**：
- 条纹进度条（未完成时显示流动动画）
- 5 步管道可视化时间线（圆形图标 + 脉冲动画标记当前步骤）
- SSE 实时更新（浏览器原生 `EventSource` API）
- 完成后：内嵌 `<video>` 播放器 + 下载按钮
- 失败时：红色错误卡片 + 详细错误信息
- 处理日志列表（实时追加）

**开发启动**：

```bash
# 后端
cd packages/server && uvicorn server.main:app --reload --port 8000

# 前端（自动代理 /api → localhost:8000）
cd packages/web && npm run dev
```

## 9. 环境配置

通过 `.env` 文件配置（参考 `.env.example`）：

```bash
# LLM API Keys（任选一个提供商）
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# DEEPSEEK_API_KEY=...

# MinerU
# MINERU_MODEL_SOURCE=modelscope  # 国内加速

# Theia 默认值
THEIA_LLM_MODEL=gpt-4o
THEIA_LANGUAGE=zh
THEIA_FPS=30
THEIA_MINERU_BACKEND=pipeline
THEIA_TTS_VOICE=zh-CN-YunxiNeural

# 分步骤模型配置（成本优化）
THEIA_EXTRACT_MODEL=gpt-4o         # 信息抽取：需要准确性，用强模型
THEIA_SCRIPT_MODEL=gpt-4o-mini     # 脚本生成：创意任务，用快/便宜模型
```

## 10. 性能与限制

### 10.1 典型处理时间（10 页论文）

| 阶段 | 预计耗时 | 备注 |
|------|---------|------|
| MinerU 解析 | 30-60s | CPU 模式；GPU 可降至 10-20s |
| LLM 抽取 | 5-15s | 取决于模型和网络 |
| 脚本生成 | 3-8s | 较短的 LLM 调用 |
| TTS 合成 | 10-20s | 5 个场景并行 |
| Remotion 渲染 | 30-120s | 取决于视频时长和机器性能 |
| **总计** | **~1.5-4 分钟** | 缓存命中后跳过前两步 |

### 10.2 当前限制

- MinerU 对超复杂排版（多栏+大量公式交错）的阅读顺序可能不准确
- Edge TTS 为在线服务，需要网络连接
- 任务管理使用内存存储，服务重启后任务列表丢失（本地开发足够）

## 11. 已完成的优化

| 优化项 | 描述 | 效果 |
|--------|------|------|
| 分步骤模型策略 | 抽取用 gpt-4o，脚本用 gpt-4o-mini | 成本降低 ~50% |
| 智能截断 | 按标题分段，优先丢弃 References/Appendix | 同 token 预算信息密度提升 |
| Few-shot Prompt | 抽取 prompt 增加完整示例 | 格式一致性和首次成功率提升 |
| 自动语言检测 | CJK 字符比例启发式检测 | 免去手动指定语言，自动适配 TTS |
| LangGraph 编排 | StateGraph + 条件路由 | 为未来扩展预留架构基础 |
| KaTeX 公式渲染 | FormulaScene 使用 KaTeX 渲染 LaTeX | 公式从原文变为美观数学符号 |
| 独占式场景 | 关键公式/图表独占全屏场景 | 重要信息展示更清晰 |
| 响应式布局 | useScale Hook 多尺寸适配 | 横屏/竖屏/正方形自动适配 |
| 多平台预设 | 6 种视频尺寸预设 | 一键适配 B 站/抖音/小红书等平台 |
| Web 界面 | Vue 3 + FastAPI + SSE | 可视化操作，实时进度，视频预览 |

## 12. 扩展路线

| 优先级 | 特性 | 描述 |
|--------|------|------|
| P0 | 主题系统 | 支持亮色/暗色/自定义配色方案 |
| P1 | 人机交互 | LangGraph interrupt() 在摘要/脚本阶段暂停确认 |
| P1 | 背景音乐 | 可选的轻音乐叠加 |
| P1 | 任务持久化 | SQLite 存储任务状态，服务重启不丢失 |
| P2 | 批量处理 | 一次处理多篇论文 |
| P2 | LangSmith 可观测性 | 追踪每个节点的输入输出和 token 消耗 |
| P2 | 用户认证 | Web 端登录/注册，多用户隔离 |
| P3 | Docker 部署 | 前后端 + 依赖一键 Docker Compose 启动 |
| P3 | 多 Agent 协作 | 解析 Agent + 写作 Agent + 设计 Agent 分工 |
