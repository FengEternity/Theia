# Theia Agent

LangGraph 驱动的论文→视频流水线。将学术 PDF 经过解析、多遍信息提取、多 Agent 脚本生成、语音合成、视频渲染，输出完整的讲解视频。

## 安装

```bash
cd packages/agent
uv pip install -e .
```

## CLI

```bash
# 完整流水线
theia render paper.pdf -o output.mp4

# 指定预设
theia render paper.pdf --preset portrait        # 竖屏 9:16
theia render paper.pdf --preset xiaohongshu     # 小红书 3:4
theia render paper.pdf --preset bilibili        # B站

# 完整参数
theia render paper.pdf \
  -o output.mp4 \
  -m kimi-k2-0905-preview \
  --extract-model kimi-k2-0905-preview \
  --script-model kimi-k2-0905-preview \
  --scan-model kimi-k2-0905-preview \
  -l auto \
  --voice zh-CN-YunxiNeural \
  --backend pipeline \
  --preset landscape \
  --fps 30 \
  --narration-style popsci \
  --theme academic \
  --skip-tts \
  --skip-render \
  -v

# 单步执行
theia parse paper.pdf -o ./workspace/parsed     # 仅解析 PDF
theia extract paper.pdf -m kimi-k2-0905-preview # 解析 + 信息提取
```

### CLI 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-o, --output` | 输出视频路径 | 自动生成 |
| `-w, --workspace` | 工作目录 | `./workspace` |
| `-m, --model` | 后备 LLM 模型 | `kimi-k2-0905-preview` |
| `--extract-model` | 信息提取模型 | 同 `-m` |
| `--script-model` | 脚本生成模型 | 同 `-m` |
| `--scan-model` | Pass 1 快速扫描模型 | 同 `-m` |
| `-l, --language` | 输出语言（zh/en/auto） | `zh` |
| `--voice` | Edge TTS 语音名称 | 按语言自动选择 |
| `--backend` | MinerU 后端 | `pipeline` |
| `--preset` | 视频尺寸预设 | `landscape` |
| `--fps` | 帧率 | `30` |
| `--narration-style` | 旁白风格（default/academic/story/popsci） | `default` |
| `--theme` | 视觉主题（academic/popsci） | `academic` |
| `--skip-tts` | 跳过语音合成 | `false` |
| `--skip-render` | 仅生成脚本 | `false` |
| `-v, --verbose` | 调试日志 | `false` |

## 流水线

基于 LangGraph StateGraph，6 步处理：

```
parse → extract → quality_gate → script → tts → render
```

| 步骤 | 模块 | 技术 | 输入 → 输出 |
|------|------|------|-------------|
| 1. 解析 | `parsing/` | MinerU（云端/本地） | PDF → Markdown + 图片 |
| 2. 提取 | `extraction/` | LLM 多遍提取 + 图表分析 | Markdown + 图片 → `PaperSummary` |
| 3. 门控 | `quality/` | 规则 + LLM 评估 | PaperSummary → 质量评分 + 自动修复 |
| 4. 脚本 | `output/` | 多 Agent 协作 | PaperSummary → `VideoScript` |
| 5. 语音 | `output/tts.py` | Edge TTS | 旁白文本 → MP3（每场景一个） |
| 6. 渲染 | `output/renderer.py` | Remotion CLI | Script + 音频 + 图片 → MP4 |

### 运行模式

- **批量模式** — 全程自动，PDF 进 MP4 出
- **交互模式** — 通过 LangGraph `interrupt()` 在每步后暂停，等待用户审核/编辑，再通过 `Command(resume=...)` 继续

### 信息提取策略

采用多遍提取架构（`extraction/`）：

1. **快速扫描**（Pass 1）— 轻量模型整体扫描论文，建立结构骨架
2. **分段深入**（`sections.py`）— 按章节分块，独立提取每段关键信息
3. **合成整合**（`synthesize.py`）— 多段结果合成为完整 `PaperSummary`
4. **图表分析**（`figure_analyzer.py`）— 多模态 LLM 分析图表，生成描述和重要性评分
5. **表格分析**（`table_analyst.py`）— LLM 提取表格数据并转换为结构化格式

### 多 Agent 脚本生成

`output/` 模块采用 4 Agent 协作架构：

| Agent | 模块 | 职责 |
|-------|------|------|
| Story Architect | `story_architect.py` | 全局叙事规划：场景选择、编排、叙事弧线、时长预算 |
| Scene Writer | `scene_writer.py` | 逐场景撰写旁白、视觉数据和注意力标注 |
| Visual Director | `visual_director.py` | 动画编排：基于规则引擎生成 AnimationPhase 序列 |
| Pacing Reviewer | `pacing_reviewer.py` | 节奏校验：时长约束、场景比例、注意力平衡 |

场景类型和预算由 `scene_registry.py` 集中管理。

### 质量门控

`quality/` 在提取后进行多层评估：

- **L1 结构检查** — 必填字段、长度约束、格式校验
- **L2 语义检查** — 内容一致性、方法-结果对应
- **L3 LLM 评估** — 可选的深度质量评分（需额外 LLM 调用）
- **自动修复** — 对可修复问题自动补全（标题、摘要截断等）

## 模块结构

```
theia/
├── cli.py                    # CLI 入口（Click）
├── pipeline.py               # LangGraph StateGraph 编排
├── schemas.py                # Pydantic 数据模型
├── schemas_compat.py         # 数据模型兼容层（迁移期间）
├── scene_registry.py         # 场景类型注册与预算
├── cache.py                  # 文件缓存（解析/提取结果）
│
├── parsing/                  # 输入解析
│   ├── pdf.py                # MinerU PDF 解析（云端/本地自动选择）
│   ├── web.py                # 网页文章解析
│   └── zhihu.py              # 知乎专栏解析
│
├── extraction/               # 信息提取
│   ├── extractor.py          # 提取入口
│   ├── multi_pass.py         # 多遍提取主逻辑
│   ├── sections.py           # 分段提取
│   ├── synthesize.py         # 提取结果合成
│   ├── figure_analyzer.py    # 图表多模态分析
│   ├── table_analyst.py      # 表格数据提取
│   └── utils.py              # 提取工具函数
│
├── llm/                      # LLM 交互层
│   ├── client.py             # 统一调用（robust_completion、JSON 解析）
│   └── config.py             # 多模型配置、语言检测、Token 截断
│
├── output/                   # 输出生成
│   ├── scriptwriter.py       # 脚本生成入口（编排 4 Agent）
│   ├── story_architect.py    # Agent 1: 全局叙事规划
│   ├── scene_writer.py       # Agent 2: 场景旁白生成
│   ├── visual_director.py    # Agent 3: 动画编排（规则引擎）
│   ├── pacing_reviewer.py    # Agent 4: 节奏审核
│   ├── tts.py                # Edge TTS 语音合成
│   ├── renderer.py           # Remotion 渲染桥接（subprocess）
│   ├── manim_renderer.py     # Manim 动画渲染（可选）
│   └── manim_templates.py    # Manim 模板
│
├── quality/                  # 质量评估
│   ├── evaluator.py          # 多层评估器
│   └── gate.py               # 质量门控（评估 + 自动修复）
│
└── prompts/                  # 提示词模板
    ├── extraction_pass1.py   # Pass 1 扫描
    ├── extraction_pass2.py   # Pass 2 深度提取
    ├── extraction_section.py # 分段提取
    ├── extraction_single.py  # 单遍提取（后备）
    ├── story_architect.py    # 故事架构师
    ├── scene_writer.py       # 场景编剧
    └── table_analyst.py      # 表格分析
```

## 数据模型

核心模型定义在 `schemas.py`：

- **`PaperSummary`** — 论文结构化摘要（标题、摘要、方法、结果、图表等）
- **`Figure`** — 图片信息（路径、描述、重要性评分、类型）
- **`StoryBlueprint`** — 叙事蓝图（场景计划列表、全局参数）
- **`ScenePlan`** — 单场景计划（类型、标题、数据来源）
- **`SceneNarration`** — 场景旁白（文本、注意力标注、视觉数据）
- **`VisualChoreography`** — 视觉编排（AnimationPhase 序列）
- **`AnimationPhase`** — 动画阶段（时间范围、注意力模式、元素）
- **`VideoScript`** — 视频脚本（场景序列，完整渲染数据）
- **`PipelineInput`** — 流水线输入参数验证
- **`StepInfo`** — 步骤进度信息
- **`ProgressCallback`** — 进度回调协议（与 server 解耦）

## 依赖

- [LangGraph](https://github.com/langchain-ai/langgraph) — 流水线编排
- [LiteLLM](https://github.com/BerriAI/litellm) — 统一 LLM API
- [MinerU (magic-pdf)](https://github.com/opendatalab/MinerU) — PDF 解析
- [edge-tts](https://github.com/rany2/edge-tts) — 微软 TTS
- [Pydantic](https://docs.pydantic.dev/) — 数据模型
- [Click](https://click.palletsprojects.com/) — CLI 框架

## 更新日志

- **2026-02-28** — 模块化重构：拆分为 `extraction/`、`llm/`、`output/`、`parsing/`、`quality/` 子模块；多 Agent 脚本生成（Story Architect + Scene Writer + Visual Director + Pacing Reviewer）；场景注册中心；表格分析
- **2026-02-25** — extractor 拆分为多轮提取架构，新增图片分析、质量门控、旁白风格支持
- **2026-02-24** — 统一 LLM 调用层，ProgressCallback 协议解耦 agent 与 server
- **2026-02-22** — LangGraph 交互模式（interrupt/resume），文件缓存
- **2026-02-18** — 初始版本：5 步线性流水线，CLI 入口
