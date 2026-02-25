# Theia Agent

LangGraph 驱动的论文→视频流水线。将学术 PDF 经过解析、信息提取、脚本生成、语音合成、视频渲染，输出完整的讲解视频。

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

# 完整参数
theia render paper.pdf \
  -o output.mp4 \
  -m gpt-4o \
  --extract-model gpt-4o \
  --script-model gpt-4o-mini \
  --scan-model gpt-4o-mini \
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
theia extract paper.pdf -m gpt-4o               # 解析 + 信息提取
```

### CLI 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-o, --output` | 输出视频路径 | 自动生成 |
| `-w, --workspace` | 工作目录 | `./workspace` |
| `-m, --model` | 后备 LLM 模型 | `gpt-4o` |
| `--extract-model` | 信息提取模型 | 同 `-m` |
| `--script-model` | 脚本生成模型 | `gpt-4o-mini` |
| `--scan-model` | Pass 1 快速扫描模型 | `gpt-4o-mini` |
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

基于 LangGraph StateGraph，5 步处理：

```
parse → extract → script → tts → render
```

| 步骤 | 模块 | 技术 | 输入 → 输出 |
|------|------|------|-------------|
| 1. 解析 | `parser.py` | MinerU | PDF → Markdown + 图片 |
| 2. 提取 | `extractor.py` | LLM 多轮提取 | Markdown + 图片 → `PaperSummary` |
| 3. 脚本 | `scriptwriter.py` | LLM | PaperSummary → `VideoScript` |
| 4. 语音 | `tts.py` | Edge TTS | 旁白文本 → MP3（每场景一个） |
| 5. 渲染 | `renderer.py` | Remotion CLI | Script + 音频 + 图片 → MP4 |

### 运行模式

- **批量模式** — 全程自动，PDF 进 MP4 出
- **交互模式** — 通过 LangGraph `interrupt()` 在每步后暂停，等待用户审核/编辑，再通过 `Command(resume=...)` 继续

### 信息提取策略

采用多轮提取架构（`_extract_multi_pass.py`）：

1. **快速扫描**（Pass 1）— 轻量模型整体扫描论文，建立结构骨架
2. **分段深入**（`_extract_sections.py`）— 按章节分块，独立提取每段关键信息
3. **合成整合**（`_extract_synthesize.py`）— 多段结果合成为完整 `PaperSummary`
4. **图片分析**（`figure_analyzer.py`）— 多模态 LLM 分析图表，生成描述和重要性评分

### 质量门控

`quality_gate.py` 在提取后检查输出质量，确保结构化数据的完整性和准确性。

## 模块说明

```
theia/
├── cli.py                  # CLI 入口（Click）
├── pipeline.py             # LangGraph StateGraph 编排
├── parser.py               # MinerU PDF 解析（云端/本地自动选择）
├── extractor.py            # 信息提取入口
├── _extract_multi_pass.py  # 多轮提取主逻辑
├── _extract_sections.py    # 分段提取
├── _extract_synthesize.py  # 提取结果合成
├── figure_analyzer.py      # 图片多模态分析
├── scriptwriter.py         # 视频脚本生成
├── tts.py                  # Edge TTS 语音合成
├── renderer.py             # Remotion 渲染桥接（subprocess）
├── quality_gate.py         # 质量门控
├── llm_config.py           # LLM 配置（多模型策略 + 语言检测 + 截断）
├── llm_client.py           # LLM 统一调用（LiteLLM）
├── cache.py                # 文件缓存（解析/提取结果）
├── evaluator.py            # 输出评估
└── schemas.py              # Pydantic 数据模型（PaperSummary, VideoScript 等）
```

## 数据模型

核心模型定义在 `schemas.py`：

- **`PaperSummary`** — 论文结构化摘要（标题、摘要、方法、结果、图表等）
- **`Figure`** — 图片信息（路径、描述、重要性评分、类型）
- **`VideoScript`** — 视频脚本（场景序列，每场景含类型、内容、旁白）
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

- **2026-02-25** — extractor 拆分为多轮提取架构，新增图片分析、质量门控、旁白风格支持
- **2026-02-24** — 统一 LLM 调用层，ProgressCallback 协议解耦 agent 与 server
- **2026-02-22** — LangGraph 交互模式（interrupt/resume），文件缓存
- **2026-02-18** — 初始版本：5 步线性流水线，CLI 入口
