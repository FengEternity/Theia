# Theia 重构实施计划

> 生成日期: 2026-02-24
> 基于代码库完整审查（14 个 agent 模块 + server 模块）

## 全局概览

```
Phase 1: 基础设施层重构（消除技术债务）
   ├── 1A: 统一 LLM 调用层
   ├── 1B: 统一 JSON 解析工具层
   ├── 1C: Prompt 模板外置
   └── 1D: extractor.py 拆分

Phase 2: 架构解耦（核心架构升级）
   ├── 2A: Progress Callback 替代日志解析
   ├── 2B: PipelineState 分层重构
   └── 2C: 可配置路径 + 依赖注入

Phase 3: 人工干预系统（核心产品功能）
   ├── 3A: LangGraph interrupt 接入
   ├── 3B: 中间产物 CRUD API
   ├── 3C: 任意步骤重跑能力
   └── 3D: 前端 Pipeline Stepper

Phase 4: 智能质量控制（ReAct 局部引入）
   ├── 4A: 质量门控升级为多维评估循环
   └── 4B: 自适应错误恢复策略
```

**建议执行顺序：** 1A → 1B → 1C → 1D → 2A → 2B → 2C → 4A → 4B → 3A → 3B → 3C → 3D

---

## Phase 1: 基础设施层重构

### 1A: 统一 LLM 调用层

**问题诊断：** `_robust_completion` + `_direct_openai_completion` 在 3 个文件中重复实现：

| 文件 | 行数 | 特点 |
|------|------|------|
| `extractor.py:1151-1323` | ~173 行 | 最完整：参数降级 + fallback + Azure 认证 |
| `scriptwriter.py:363-399` | ~37 行 | 简化版：仅参数降级 |
| `evaluator.py:608-623` | ~16 行 | 最简版：仅 `openai/` 前缀处理 |
| `figure_analyzer.py:225` | 1 行 | 直接 import extractor 的（跨模块耦合） |

**重构方案：** 新建 `packages/agent/theia/llm_client.py`

**模块公共 API：**

```python
# llm_client.py

def robust_completion(kwargs: dict) -> ModelResponse:
    """统一的 LLM 调用入口，带参数降级和 API 故障转移。"""
    ...

def extract_json_from_response(response: ModelResponse) -> str:
    """从 LLM 响应中提取 JSON（兼容推理模型）。"""
    ...

def strip_json_fences(text: str) -> str:
    """去除 Markdown 代码围栏。"""
    ...
```

**内部实现（从 extractor.py 迁移）：**
- `_direct_openai_completion(kwargs)` — OpenAI 直连
- `_try_fallback(kwargs, exc)` — 主备切换
- `_normalize_model_params(kwargs)` — 参数标准化（gpt-5/o3/o4 系列）
- `_ensure_direct_openai_kwargs(kwargs)` — openai/ 前缀处理

**影响的文件：**
- `extractor.py` — 删除 `_robust_completion` 等 7 个函数（~200 行），改为 import
- `scriptwriter.py` — 删除 `_robust_completion` + `_direct_openai_completion`（~37 行）
- `evaluator.py` — 删除 `_direct_openai_completion`（~16 行）
- `figure_analyzer.py` — 从 `from .extractor import _robust_completion` 改为 `from .llm_client import robust_completion`

**预计节省：** ~220 行重复代码

**验证方式：** 运行 `theia extract paper.pdf` 确认提取流程正常

---

### 1B: 统一 JSON 解析工具层

**问题诊断：**
- `_strip_json_fences` 在 `extractor.py:1349-1356` 和 `figure_analyzer.py:282-289` 完全重复
- `_extract_json_from_reasoning` 仅在 `extractor.py` 中，但 `evaluator.py` 也需要类似逻辑

**重构方案：** 纳入 `llm_client.py`，作为 JSON 提取的标准工具

**依赖：** Phase 1A

---

### 1C: Prompt 模板外置

**问题诊断：**

| 文件 | Prompt | 行数 |
|------|--------|------|
| `extractor.py` | `EXTRACTION_SYSTEM_PROMPT` | ~40 行 |
| `extractor.py` | `FEW_SHOT_EXAMPLE` | ~35 行 |
| `extractor.py` | `PASS1_PROMPT` | ~30 行 |
| `extractor.py` | `PASS2_PROMPT` | ~55 行 |
| `extractor.py` | `PASS2_SECTION_PROMPT` | ~35 行 |
| `extractor.py` | `PASS2_MERGE_PROMPT` | ~35 行 |
| `scriptwriter.py` | `SCRIPT_SYSTEM_PROMPT` | ~120 行 |
| `scriptwriter.py` | `NARRATION_STYLE_OVERRIDES` | ~40 行 |
| `evaluator.py` | `_JUDGE_SYSTEM` + `_JUDGE_PROMPT` | ~50 行 |

**重构方案：** 创建 prompts 模块

```
packages/agent/theia/prompts/
├── __init__.py                # load_prompt(name) 工具函数
├── extraction_single.py       # EXTRACTION_SYSTEM_PROMPT + FEW_SHOT_EXAMPLE
├── extraction_pass1.py        # PASS1_PROMPT
├── extraction_pass2.py        # PASS2_PROMPT
├── extraction_section.py      # PASS2_SECTION_PROMPT
├── extraction_merge.py        # PASS2_MERGE_PROMPT
├── scriptwriter.py            # SCRIPT_SYSTEM_PROMPT + NARRATION_STYLE_OVERRIDES
└── evaluator_judge.py         # _JUDGE_SYSTEM + _JUDGE_PROMPT
```

每个文件导出常量，`__init__.py` 提供统一加载接口。

**好处：**
- prompt 修改不需要理解 1357 行的 extractor.py
- 支持后续 A/B 测试不同 prompt 版本
- `extractor.py` 减少约 230 行
- `scriptwriter.py` 减少约 160 行

---

### 1D: extractor.py 拆分

**前置条件：** 1A + 1B + 1C 完成后

**当前状态：** extractor.py 1357 行，经过 1A/1B/1C 后约 800 行

**拆分方案：**

```
packages/agent/theia/
├── extractor.py                # 公共 API 入口 (~100 行)
│   └── extract_paper_summary()
├── _extract_multi_pass.py      # 三遍提取核心逻辑 (~250 行)
│   ├── _extract_multi_pass()
│   ├── _pass1_quick_scan()
│   └── _pass2_deep_extract()
├── _extract_sections.py        # 分段提取 (~200 行)
│   ├── _pass2_chunked_extract()
│   ├── _extract_single_section()
│   ├── _merge_section_results()
│   └── _manual_merge()
├── _extract_synthesize.py      # 融合与质量验证 (~120 行)
│   ├── _synthesize()
│   ├── _quality_score()
│   └── _sections_from_content_list()
└── _extract_utils.py           # 提取专用工具 (~50 行)
    └── _estimate_tokens()
```

**公共入口保持不变：**

```python
# extractor.py
from ._extract_multi_pass import _extract_multi_pass

def extract_paper_summary(markdown_content, *, model="gpt-4o", ...) -> PaperSummary:
    return _extract_multi_pass(markdown_content, ...)
```

---

## Phase 2: 架构解耦

### 2A: Progress Callback 替代日志解析

**问题诊断：** `task_manager.py` 的 `_PipelineLogHandler` 通过正则 `步骤\s*(\d)/5` 解析日志获取进度

```python
# 当前（脆弱）
_STEP_RE = re.compile(r"步骤\s*(\d)/5")
class _PipelineLogHandler(logging.Handler):
    def emit(self, record):
        msg = record.getMessage()
        m = _STEP_RE.search(msg)  # 依赖日志文本格式
```

**重构方案：** 引入 `ProgressCallback` 协议

**schemas.py 新增：**

```python
from typing import Protocol, runtime_checkable

class StepInfo(BaseModel):
    step: int                  # 当前步骤 (1-5)
    total_steps: int           # 总步骤数 (5)
    name: str                  # "parse" | "extract" | "script" | "tts" | "render"
    status: str                # "started" | "progress" | "completed" | "failed"
    message: str = ""
    progress_pct: int = 0      # 步骤内进度 0-100
    detail: dict = {}          # 额外信息（如 "pass": "2/3"）

@runtime_checkable
class ProgressCallback(Protocol):
    def on_step(self, info: StepInfo) -> None: ...
```

**pipeline.py 改造：**

```python
def run_pipeline(..., progress: ProgressCallback | None = None) -> dict:
    ...
    
def parse_node(state: PipelineState) -> dict:
    cb = state.get("_progress_callback")
    if cb:
        cb.on_step(StepInfo(step=1, total_steps=5, name="parse", status="started",
                           message="使用 MinerU 解析 PDF"))
    # ... 原有逻辑 ...
    if cb:
        cb.on_step(StepInfo(step=1, total_steps=5, name="parse", status="completed",
                           message=f"解析完成: {len(result.markdown)} 字符"))
```

**task_manager.py 改造：**

```python
class _TaskProgressCallback:
    """实现 ProgressCallback，更新 DB + SSE。"""
    _NAME_TO_STAGE = {
        "parse": TaskStage.PARSING,
        "extract": TaskStage.EXTRACTING,
        "script": TaskStage.SCRIPTING,
        "tts": TaskStage.TTS,
        "render": TaskStage.RENDERING,
    }
    
    def __init__(self, mgr: TaskManager, task_id: str, cancel_event: threading.Event):
        self.mgr = mgr
        self.task_id = task_id
        self.cancel_event = cancel_event
    
    def on_step(self, info: StepInfo) -> None:
        if self.cancel_event.is_set():
            raise _CancelledError("任务已被用户取消")
        stage = self._NAME_TO_STAGE.get(info.name)
        if stage and info.status == "started":
            self.mgr._update_stage(self.task_id, stage, info.message)
```

**好处：**
- 完全消除日志正则解析依赖
- 支持更细粒度的进度（如 "提取中 Pass 2/3"，"TTS 3/7 个场景"）
- Agent 和 Server 通过协议解耦，可独立测试
- CLI 模式也可以接入 callback 显示进度条

---

### 2B: PipelineState 分层

**问题诊断：** 当前 `PipelineState` 是扁平 TypedDict，混杂了 20+ 输入参数、中间状态和输出

**重构方案：**

```python
class PipelineInput(BaseModel):
    """用户输入参数，不可变。"""
    pdf_path: str
    workspace: str
    language: str = "zh"
    video_preset: str = "landscape"
    fps: int = 30
    skip_tts: bool = False
    skip_render: bool = False
    use_cache: bool = True
    narration_style: str = "default"
    theme: str = "academic"
    speech_rate: int = 0
    output_path: str | None = None
    interactive_mode: bool = False  # Phase 3 用
    
    # LLM 配置（通过 LLMConfig 注入）
    extract_model: str = "gpt-4o"
    scan_model: str = "gpt-4o-mini"
    script_model: str = "gpt-4o-mini"
    figure_model: str = "gpt-4o"
    tts_voice: str | None = None
    mineru_backend: str = "pipeline"


class PipelineArtifacts(TypedDict, total=False):
    """中间产物，每步产生。可持久化、可编辑。"""
    detected_language: str
    markdown_content: str
    content_list_json: str | None
    parsed_dir: str
    figures_json: str
    paper_summary_json: str
    video_script_json: str


class PipelineState(TypedDict, total=False):
    """LangGraph 完整状态 = Input + Artifacts + Output + Internal"""
    # 输入（不可变）
    input: dict  # PipelineInput.model_dump()
    
    # 中间产物（可编辑）
    artifacts: PipelineArtifacts
    
    # 输出
    output_video: str | None
    error: str | None
    
    # 内部（不持久化）
    _progress_callback: object | None
```

**好处：**
- 职责清晰：Input 不可变，Artifacts 是中间产物
- 为 Phase 3 的人工编辑提供明确的编辑目标
- Artifacts 可以直接序列化/反序列化，支持断点恢复

---

### 2C: 可配置路径 + 依赖注入

**问题诊断：**

1. `renderer.py:20` — `VIDEO_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent / "video"` 硬编码
2. `task_manager.py:38` — `WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent / "workspace"` 硬编码
3. `task_manager.py:619` — `manager = TaskManager()` 模块级单例

**重构方案：**

```python
# renderer.py — 参数化
def render_video(
    script: VideoScript,
    output_path: Path,
    *,
    workspace: Path | None = None,
    parsed_dir: Path | None = None,
    video_package_dir: Path | None = None,  # 新增
) -> Path:
    video_dir = video_package_dir or _find_video_package()
    ...

def _find_video_package() -> Path:
    # 1. 环境变量 THEIA_VIDEO_PACKAGE_DIR
    # 2. 相对路径（向后兼容）
    env_dir = os.getenv("THEIA_VIDEO_PACKAGE_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.exists():
            return p
    return _default_video_package_dir()

# task_manager.py — 依赖注入
class TaskManager:
    def __init__(self, workspace: Path | None = None) -> None:
        self._workspace = workspace or Path(
            os.getenv("THEIA_WORKSPACE", str(_DEFAULT_WORKSPACE))
        )
        ...

# server/main.py — 工厂创建
from .task_manager import TaskManager
manager = TaskManager()  # 仍然可以是单例，但可测试
```

---

## Phase 3: 人工干预系统

### 3A: LangGraph interrupt 接入

**核心改造：** 在 `build_graph()` 中支持 interactive 模式

```python
from langgraph.types import interrupt

def extract_node(state: PipelineState) -> dict:
    # ... 正常的提取逻辑 ...
    summary_json = summary.model_dump_json(indent=2)
    
    # 如果启用了逐步模式，在此暂停等待人工审核
    input_cfg = state.get("input", {})
    if input_cfg.get("interactive_mode"):
        decision = interrupt({
            "step": "extract",
            "artifact_type": "paper_summary",
            "data": json.loads(summary_json),
            "message": "论文信息提取完成，请审核或编辑后继续",
        })
        
        action = decision.get("action", "approve")
        if action == "edit":
            summary = PaperSummary(**decision["data"])
            summary_json = summary.model_dump_json(indent=2)
        elif action == "retry":
            # 清除缓存，重新提取
            return extract_node(state)
    
    return {"paper_summary_json": summary_json}
```

**需要添加 interrupt 的节点：**

| 节点 | 审核内容 | 用户操作 |
|------|---------|---------|
| `extract_node` | PaperSummary (JSON) | 编辑 title/method/results 等 |
| `script_node` | VideoScript (JSON) | 编辑旁白文本、调整场景顺序/时长 |
| `tts_node` | 音频文件 | 试听、重新合成某个场景 |

**build_graph 改造：**

```python
def build_graph(*, with_checkpointer: bool = False, interactive: bool = False):
    builder = StateGraph(PipelineState)
    builder.add_node("parse_node", parse_node)
    builder.add_node("extract_node", extract_node)
    builder.add_node("script_node", script_node)
    builder.add_node("tts_node", tts_node)
    builder.add_node("render_node", render_node)
    
    builder.add_edge(START, "parse_node")
    builder.add_edge("parse_node", "extract_node")
    builder.add_conditional_edges(
        "extract_node", route_after_extract,
        {"script_node": "script_node", "extract_node": "extract_node"},
    )
    builder.add_edge("script_node", "tts_node")
    builder.add_edge("tts_node", "render_node")
    builder.add_edge("render_node", END)
    
    use_checkpointer = with_checkpointer or interactive
    checkpointer = MemorySaver() if use_checkpointer else None
    return builder.compile(checkpointer=checkpointer)
```

---

### 3B: 中间产物 CRUD API

**新增 routes.py 端点：**

```python
# 获取等待审核的中间产物
@router.get("/tasks/{task_id}/pending-review")
async def get_pending_review(task_id: str):
    """返回当前等待审核的中间产物（仅逐步模式）。"""
    ...

# 编辑中间产物
@router.put("/tasks/{task_id}/artifacts/{artifact_type}")
async def update_artifact(task_id: str, artifact_type: str, body: dict):
    """编辑指定类型的中间产物。
    artifact_type: summary | script | markdown
    """
    ...

# 审核通过，继续执行
@router.post("/tasks/{task_id}/approve")
async def approve_and_continue(task_id: str, body: dict | None = None):
    """批准当前步骤结果，继续下一步。
    body 可选包含编辑后的数据。
    """
    ...

# 拒绝，重新执行当前步骤
@router.post("/tasks/{task_id}/reject")
async def reject_and_retry(task_id: str):
    """拒绝当前步骤结果，重新执行。"""
    ...

# 从指定步骤重跑
@router.post("/tasks/{task_id}/resume-from")
async def resume_from_step(task_id: str, step: str = Query(...)):
    """从指定步骤开始重新执行（使用已有的中间产物）。
    step: parse | extract | script | tts | render
    """
    ...
```

**task_manager.py 新增方法：**

```python
class TaskManager:
    def get_pending_review(self, task_id: str) -> dict | None:
        """获取当前等待审核的中间产物。"""
        ...
    
    def update_artifact(self, task_id: str, artifact_type: str, data: dict) -> bool:
        """更新中间产物并持久化到文件。"""
        ...
    
    def approve_and_continue(self, task_id: str, edited_data: dict | None = None) -> TaskResponse:
        """审核通过，恢复 LangGraph 执行。"""
        ...
    
    def reject_and_retry(self, task_id: str) -> TaskResponse:
        """拒绝当前结果，重新执行当前步骤。"""
        ...
    
    def resume_from_step(self, task_id: str, step: str) -> TaskResponse:
        """从指定步骤开始重新执行。"""
        ...
```

---

### 3C: 任意步骤重跑

**核心能力：** 用户编辑了 `paper_summary.json` 后，可以只重跑 `script → tts → render`

**实现方式：**

```python
def run_pipeline_from(
    step: str,              # "parse" | "extract" | "script" | "tts" | "render"
    workspace: Path,
    *,
    existing_artifacts: dict,  # 之前的中间产物
    pipeline_input: dict,      # 用户配置
    progress: ProgressCallback | None = None,
) -> dict:
    """从指定步骤开始执行流水线，使用已有的中间产物。"""
    
    step_order = ["parse", "extract", "script", "tts", "render"]
    start_idx = step_order.index(step)
    
    # 构建初始状态：合并 input + 已有产物
    state = {
        "input": pipeline_input,
        "artifacts": existing_artifacts,
        "_progress_callback": progress,
    }
    
    # 构建只包含从 step 开始的子图
    graph = build_partial_graph(start_step=step)
    result = graph.invoke(state)
    return result
```

---

### 3D: 前端 Pipeline Stepper

**Vue 组件设计：**

```
PipelineStepper.vue
├── StepIndicator.vue       # 步骤进度条 (5 步)
├── ArtifactEditor.vue      # 中间产物编辑器
│   ├── SummaryEditor.vue   # PaperSummary JSON 树编辑
│   ├── ScriptEditor.vue    # VideoScript 场景编辑
│   └── AudioPreview.vue    # 音频试听
└── StepActions.vue         # [继续] [编辑] [重新执行] 按钮
```

**交互流程（逐步模式）：**

```
1. 用户上传 PDF → 选择"逐步模式" ✅
2. [Parse ✅] → 完成后显示 Markdown 预览
     → [继续] [编辑 Markdown]
3. [Extract ⏸️] → 完成后显示 Summary 编辑器
     → JSON 树编辑器 (title, problem, method, results...)
     → [继续] [重新提取] [手动编辑后继续]
4. [Script ⏸️] → 完成后显示脚本编辑器
     → 场景卡片列表（可拖拽排序、编辑旁白、调整时长）
     → [继续] [重新生成]
5. [TTS ⏸️] → 完成后可试听每个场景音频
     → [继续] [重新合成]
6. [Render] → 自动执行 → 完成
```

**API 交互时序：**

```
POST /api/tasks (config.interactive_mode=true)
  → SSE: stage=parsing
  → SSE: stage=extracting
  → SSE: stage=pending_review, artifact_type=summary
  → [用户在前端编辑 summary]
  → PUT /api/tasks/{id}/artifacts/summary
  → POST /api/tasks/{id}/approve
  → SSE: stage=scripting
  → ...
```

---

## Phase 4: 智能质量控制

### 4A: 质量门控升级

**当前状态：** `route_after_extract` 仅检查 `len(summary_json) < 100`

```python
# 当前（过于简单）
def route_after_extract(state):
    if len(state.get("paper_summary_json", "")) < 100:
        return "extract_node"
    return "script_node"
```

**升级为 ReAct 式多维评估循环：**

```python
def quality_gate_node(state: PipelineState) -> dict:
    """ReAct 式质量控制：评估 → 分析弱点 → 针对性修复 → 再评估。
    
    循环最多 3 次，每次针对最薄弱的维度进行修复。
    """
    summary = PaperSummary.model_validate_json(state["paper_summary_json"])
    markdown = state["markdown_content"]
    evaluator = ExtractionEvaluator(markdown)
    
    for attempt in range(3):
        result = evaluator.evaluate_fast(summary)
        
        if result.fast_total >= 4.0:
            logger.info("质量评分 %.1f/6.0，通过门控", result.fast_total)
            break
        
        # Thought: 分析哪些维度不足
        weak_dims = []
        if result.l1.field_completeness < 0.7:
            weak_dims.append("field_completeness")
        if result.l2.grounding < 1.0:
            weak_dims.append("grounding")
        if result.l2.entity_match < 0.5:
            weak_dims.append("entity_match")
        if result.l2.section_coverage < 0.6:
            weak_dims.append("section_coverage")
        
        if not weak_dims:
            break
        
        logger.warning(
            "质量评分 %.1f/6.0 (不足阈值 4.0)，薄弱维度: %s，第 %d 次修复",
            result.fast_total, weak_dims, attempt + 1,
        )
        
        # Action: 针对性修复
        summary = _targeted_repair(summary, weak_dims, markdown, state)
    
    return {"paper_summary_json": summary.model_dump_json()}


def _targeted_repair(
    summary: PaperSummary,
    weak_dims: list[str],
    markdown: str,
    state: dict,
) -> PaperSummary:
    """针对薄弱维度进行精准修复。"""
    
    if "field_completeness" in weak_dims:
        # 找到缺失的字段，针对性追问
        missing = _find_missing_fields(summary)
        if missing:
            summary = _fill_missing_fields(summary, missing, markdown, state)
    
    if "grounding" in weak_dims:
        # 验证关键术语是否在原文中，替换幻觉内容
        summary = _verify_and_fix_grounding(summary, markdown)
    
    if "entity_match" in weak_dims:
        # 从原文中重新提取实体信息
        summary = _re_extract_entities(summary, markdown, state)
    
    return summary
```

**Graph 改造：** 将 `quality_gate_node` 插入到 extract 和 script 之间

```python
builder.add_node("quality_gate", quality_gate_node)
builder.add_edge("extract_node", "quality_gate")
builder.add_edge("quality_gate", "script_node")
```

---

### 4B: 自适应错误恢复

**当前状态：** 各模块各自处理错误，重试策略分散且不一致

**重构方案：** 统一的错误恢复策略（可纳入 `llm_client.py`）

```python
class RecoveryStrategy:
    """自适应错误恢复策略。
    
    根据错误类型自动决定恢复策略。
    """
    
    @staticmethod
    def classify(exc: Exception) -> str:
        """分类错误，返回恢复策略。
        
        返回:
            "retry" — 简单重试（网络超时等）
            "retry_with_backoff" — 带退避重试（频率限制）
            "reduce_input" — 缩减输入重试（token 超限）
            "fallback_model" — 切换备用模型（服务端 5xx）
            "skip" — 跳过当前步骤（非关键错误）
            "abort" — 终止（不可恢复错误）
        """
        msg = str(exc).lower()
        
        if any(kw in msg for kw in ("rate limit", "429", "ratelimit", "quota")):
            return "retry_with_backoff"
        if any(kw in msg for kw in ("context_length", "too large", "tokens_limit", "413")):
            return "reduce_input"
        if any(kw in msg for kw in ("timeout", "timed out", "connection")):
            return "retry"
        if any(kw in msg for kw in ("500", "502", "503", "internal server")):
            return "fallback_model"
        if "invalid" in msg or "format" in msg:
            return "retry"
        
        return "abort"
    
    @staticmethod
    def execute(strategy: str, kwargs: dict, exc: Exception, attempt: int) -> dict:
        """执行恢复策略，返回修改后的 kwargs。"""
        if strategy == "retry_with_backoff":
            import time
            time.sleep(min(2 ** attempt, 60))
            return kwargs
        
        if strategy == "reduce_input":
            messages = kwargs.get("messages", [])
            for msg in messages:
                if isinstance(msg.get("content"), str) and len(msg["content"]) > 10000:
                    msg["content"] = msg["content"][:len(msg["content"]) // 2] + "\n\n[... 已截断 ...]"
            return kwargs
        
        if strategy == "fallback_model":
            # 切换到备用模型
            fallback = _get_fallback_config(kwargs)
            if fallback:
                kwargs.update(fallback)
            return kwargs
        
        raise exc  # abort
```

---

## 实施排期

| 阶段 | 预计工时 | 依赖 | 风险 | 代码变更量 | 状态 |
|------|---------|------|------|-----------|------|
| **1A**: 统一 LLM 层 | 2-3h | 无 | 低 | +200 行 / -220 行 | ✅ 已完成 |
| **1B**: JSON 工具统一 | 0.5h | 1A | 低 | -30 行 | ✅ 已完成 |
| **1C**: Prompt 外置 | 1-2h | 无 | 低 | +10 文件 / -400 行内联 | ✅ 已完成 |
| **1D**: extractor 拆分 | 2-3h | 1A+1B+1C | 中 | +4 文件 / 重组 800 行 | ✅ 已完成 |
| **2A**: Progress Callback | 2-3h | 无 | 中 | +150 行 / -50 行 | ✅ 已完成 |
| **2B**: State 分层 | 1-2h | 无 | 中 | 重组 ~100 行 | ✅ 已完成 |
| **2C**: 依赖注入 | 1h | 无 | 低 | ~50 行 | ✅ 已完成 |
| **3A**: interrupt 接入 | 3-4h | 2A+2B | 高 | +200 行 | ✅ 已完成 |
| **3B**: 产物 CRUD API | 2-3h | 3A | 中 | +250 行 | ✅ 已完成 |
| **3C**: 步骤重跑 | 2h | 3A+3B | 中 | +150 行 | ✅ 已完成 |
| **4A**: 质量门控升级 | 2-3h | 1A | 中 | +200 行 | ✅ 已完成 |
| **4B**: 错误恢复 | 1-2h | 1A | 低 | +100 行 | ✅ 已完成 |
| **3D**: 前端 Stepper | 4-6h | 3B+3C | 中 | +500 行 Vue | ✅ 已完成 |

---

## 架构演进路线图

```
Phase 1 (当前→)          Phase 2              Phase 3              Phase 4
──────────────          ──────────           ──────────           ──────────
扁平 TypedDict   →   分层 State       →   Artifacts 可编辑  →   自适应质量控制
日志正则解析     →   ProgressCallback →   SSE + 审核流     →   细粒度进度
重复 LLM 调用    →   统一 llm_client  →   统一错误恢复     →   自适应降级
内联 prompt      →   prompts 目录     →   A/B 测试框架     →   prompt 自动优化
线性 StateGraph  →   条件路由优化     →   interrupt 暂停   →   ReAct 子循环
1357 行巨文件    →   4-5 个模块       →   每模块 <300 行   →   可插拔模块
```

---

## ReAct 模式决策说明

**结论：不全面采用 ReAct，局部引入到质量控制和错误恢复。**

**原因：**
1. Theia 的核心流水线是确定性管线（PDF → 解析 → 提取 → 脚本 → 语音 → 渲染），步骤顺序固定
2. 全面 ReAct 会引入不必要的推理成本（每步都让 LLM 决定"下一步做什么"）
3. 产品需要可预测的 5 步进度条，不是"Agent 在自己探索"

**局部引入的场景：**
- **Phase 4A 质量门控**：评估 → 分析弱点 → 针对性修复 → 再评估（ReAct 循环）
- **Phase 4B 错误恢复**：分类错误 → 选择策略 → 执行恢复（推理-行动模式）
- **未来可能**：script_node 内部让 LLM 自主调整场景编排策略

---

## 附录：重构前后目录结构对比

### 重构前（当前）

```
packages/agent/theia/
├── __init__.py
├── _utils.py               # 共享工具函数 (86 行)
├── cache.py                 # 文件缓存 (77 行)
├── cli.py                   # CLI 入口 (158 行)
├── evaluator.py             # 质量评估 (624 行) ← 含重复的 _direct_openai_completion
├── extractor.py             # LLM 信息提取 (1357 行) ← 巨文件
├── figure_analyzer.py       # 图表分析 (290 行) ← import extractor._robust_completion
├── llm_config.py            # LLM 配置 + 文本工具 (273 行)
├── parser.py                # MinerU 解析 (383 行)
├── pipeline.py              # LangGraph 编排 (553 行)
├── renderer.py              # Remotion 渲染 (259 行)
├── schemas.py               # Pydantic 数据模型 (159 行)
├── scriptwriter.py          # 脚本生成 (400 行) ← 含重复的 _robust_completion
└── tts.py                   # Edge TTS (324 行)
                             共 14 个文件，~4943 行
```

### 重构后（全部 Phase 完成）

```
packages/agent/theia/
├── __init__.py
├── _utils.py                    # 共享工具函数 (不变)
│
│ # ═══ Phase 1A: 统一 LLM 调用层 ═══
├── llm_client.py                # [新] 统一 LLM 调用层 (~200 行)
│   ├── robust_completion()          # 带降级/故障转移的 LLM 调用
│   ├── extract_json_from_response() # JSON 提取（含推理模型）
│   ├── strip_json_fences()          # Markdown 围栏清理
│   ├── _direct_openai_completion()  # OpenAI 直连
│   ├── _try_fallback()              # 主备切换
│   ├── _normalize_model_params()    # 参数标准化
│   └── RecoveryStrategy             # [Phase 4B] 自适应错误恢复
│
│ # ═══ Phase 1C: Prompt 模板外置 ═══
├── prompts/                     # [新] Prompt 模板目录
│   ├── __init__.py                  # load_prompt() 工具
│   ├── extraction_single.py         # 单次提取 prompt
│   ├── extraction_pass1.py          # Pass 1 快速扫描
│   ├── extraction_pass2.py          # Pass 2 深度提取
│   ├── extraction_section.py        # 分段提取
│   ├── extraction_merge.py          # 分段融合
│   ├── scriptwriter.py              # 脚本生成 + 风格模板
│   └── evaluator_judge.py           # L3 评估
│
│ # ═══ Phase 1D: extractor 拆分 ═══
├── extractor.py                 # [重构] 公共 API 入口 (~100 行)
│   └── extract_paper_summary()
├── _extract_multi_pass.py       # [新] 三遍提取核心逻辑 (~250 行)
│   ├── _extract_multi_pass()
│   ├── _pass1_quick_scan()
│   └── _pass2_deep_extract()
├── _extract_sections.py         # [新] 分段提取 (~200 行)
│   ├── _pass2_chunked_extract()
│   ├── _extract_single_section()
│   ├── _merge_section_results()
│   └── _manual_merge()
├── _extract_synthesize.py       # [新] 融合与验证 (~120 行)
│   ├── _synthesize()
│   └── _sections_from_content_list()
│
│ # ═══ Phase 4A: 质量门控 ═══
├── _extract_quality.py          # [新] 质量门控节点 (~150 行)
│   ├── quality_gate_node()
│   └── _targeted_repair()
│
│ # ═══ Phase 2B: State 分层 ═══
├── schemas.py                   # [扩展] 数据模型 (~220 行)
│   ├── PaperSummary, VideoScript...   # 原有模型
│   ├── PipelineInput              # [新] 输入参数（不可变）
│   ├── PipelineArtifacts          # [新] 中间产物（可编辑）
│   ├── StepInfo                   # [新] 进度信息
│   └── ProgressCallback           # [新] 进度回调协议
│
│ # ═══ Phase 2A + 3A: Pipeline 重构 ═══
├── pipeline.py                  # [重构] LangGraph 编排 (~400 行)
│   ├── PipelineState                # 分层状态
│   ├── build_graph()                # 支持 interactive 模式
│   ├── run_pipeline()               # 支持 progress callback
│   ├── run_pipeline_from()          # [新/Phase 3C] 从指定步骤重跑
│   └── 各节点函数                    # 支持 interrupt (Phase 3A)
│
│ # ═══ 简化后的模块 ═══
├── evaluator.py                 # [简化] 质量评估 (~500 行, -120 行)
├── figure_analyzer.py           # [简化] 图表分析 (~270 行, -20 行)
├── scriptwriter.py              # [简化] 脚本生成 (~200 行, -200 行)
│
│ # ═══ 不变的模块 ═══
├── llm_config.py                # LLM 配置 (不变)
├── cache.py                     # 文件缓存 (不变)
├── cli.py                       # CLI 入口 (不变)
├── parser.py                    # MinerU 解析 (不变)
├── renderer.py                  # [微调] video_package_dir 可配置
└── tts.py                       # Edge TTS (不变)

                                 共 24 个文件
                                 最大文件 ~250 行 (原 1357 行)
                                 重复代码 0 行 (原 ~250 行)
```

### Server 端变更

```
packages/server/server/
├── main.py                      # (不变)
├── routes.py                    # [扩展] +5 个端点
│   ├── 原有 ~15 个端点 (不变)
│   ├── GET  /tasks/{id}/pending-review     # [Phase 3B]
│   ├── PUT  /tasks/{id}/artifacts/{type}   # [Phase 3B]
│   ├── POST /tasks/{id}/approve            # [Phase 3B]
│   ├── POST /tasks/{id}/reject             # [Phase 3B]
│   └── POST /tasks/{id}/resume-from        # [Phase 3C]
├── task_manager.py              # [重构]
│   ├── TaskManager(workspace=...)   # 可配置 workspace
│   ├── _TaskProgressCallback        # [Phase 2A] 替代 _PipelineLogHandler
│   ├── get_pending_review()         # [Phase 3B]
│   ├── update_artifact()            # [Phase 3B]
│   ├── approve_and_continue()       # [Phase 3B]
│   └── resume_from_step()           # [Phase 3C]
├── models.py                    # [微调] TaskConfig 新增 interactive_mode
├── database.py                  # (不变)
└── db_models.py                 # (不变)
```

### 前端变更 (Phase 3D)

```
packages/web/src/
├── views/
│   ├── UploadView.vue           # [微调] 新增"逐步模式"开关
│   └── TaskDetailView.vue       # [扩展] 集成 Pipeline Stepper
├── components/
│   ├── PipelineStepper.vue      # [新] 步骤进度条 + 审核流
│   ├── ArtifactEditor.vue       # [新] 中间产物编辑器框架
│   │   ├── SummaryEditor.vue    # [新] PaperSummary JSON 编辑
│   │   ├── ScriptEditor.vue     # [新] 场景编辑器（旁白/时长/排序）
│   │   └── AudioPreview.vue     # [新] 音频试听
│   └── StepActions.vue          # [新] 操作按钮组
└── api/
    └── tasks.ts                 # [扩展] 新增 approve/reject/resume API
```

### 量化对比

| 维度 | 重构前 | 重构后 | 变化 |
|------|--------|--------|------|
| Agent 文件数 | 14 | 24 | +10（拆分为更小模块） |
| Agent 最大文件行数 | 1357 行 | ~250 行 | -81% |
| LLM 调用重复代码 | ~250 行（3 处） | 0 行 | -100% |
| Prompt 管理 | 散落在 3 文件中 | 独立 `prompts/` 目录 | 集中管理 |
| Server-Agent 耦合 | 日志正则 | Protocol Callback | 完全解耦 |
| 人工干预能力 | 无 | 逐步审核/编辑/重跑 | 0→1 |
| Server API 端点 | ~15 | ~20 | +5 |
| 前端新组件 | 0 | 6 | Pipeline Stepper 完整体系 |
