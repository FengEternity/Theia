# 混合场景选择系统 — 技术设计文档 (v2.0)

> 版本: v2.0 | 日期: 2026-02-28  
> 基于: 多 Agent 协作架构（4-Agent Pipeline）  
> 前序: v1.0 方案评审后修订，适配当前代码库实际结构

---

## 1. 目标与现状

### 1.1 现状

| 层面 | 当前状态 |
|------|---------|
| `schemas.py` SceneType | 已定义 15 种 |
| 前端 Remotion 组件 | 已注册全部 15 种 |
| Story Architect prompt | 仅描述 7 种（title/overview/method/formula/figure/result/conclusion） |
| Scene Writer prompt | 仅描述 7 种的旁白写作指南和 data schema |
| Visual Director 模板 | 仅有 7 种的 `SCENE_TEMPLATES`，其余 fallback 到 overview |
| Pacing Reviewer 约束 | 仅有 7 种的 `SCENE_DURATION_BOUNDS`，其余默认 (10, 30)s |

### 1.2 目标

让 4-Agent 流水线能智能选择和使用全部 15 种场景类型，同时保持安全的降级路径。

### 1.3 核心思路

```
规则引擎（候选池）→ Story Architect（编排决策）→ Scene Writer（内容填充）
                                                    ↓
                                    Visual Director（编排模板）← 场景注册表
                                                    ↓
                                    Pacing Reviewer（约束校验）← 场景注册表
                                                    ↓
                                    后处理校验 + 降级（安全兜底）
```

---

## 2. 场景注册表（Single Source of Truth）

### 2.1 新建 `scene_registry.py`

所有场景元信息集中在此文件，其他模块从 registry 读取，不再各自维护硬编码表。

```python
@dataclass(frozen=True)
class SceneSpec:
    """单个场景类型的完整规格。"""
    name: str                           # 如 "concept"
    category: str                       # "universal" | "academic" | "popsci"
    description: str                    # 用途说明
    duration_bounds: tuple[float, float]  # (min_sec, max_sec)
    narration_word_range: tuple[int, int] # (min_chars, max_chars) 中文
    visual_pause_sec: float             # 额外视觉停顿
    min_scene_sec: float                # 最低时长下限
    data_schema: dict[str, str]         # 字段名 → 类型描述
    remotion_component: str             # 前端组件名
    template_phases: list[dict]         # Visual Director 的编排模板
    narration_guide: str                # Scene Writer 的旁白写作要求
    attention_default: str              # 默认注意力模式
    manim_capable: bool                 # 是否可分配 Manim 动画
    skip_aux_figures: bool              # 是否跳过辅助图片分配
```

### 2.2 API

```python
def get_spec(scene_type: str) -> SceneSpec
def get_duration_bounds() -> dict[str, tuple[float, float]]       # → Pacing Reviewer
def get_templates() -> dict[str, list[dict]]                       # → Visual Director
def get_narration_guides() -> dict[str, str]                       # → Scene Writer prompt
def get_data_schemas() -> dict[str, dict[str, str]]                # → Scene Writer prompt
def get_word_ranges() -> dict[str, tuple[int, int]]                # → Story Architect prompt
def get_visual_pauses() -> dict[str, float]                        # → scriptwriter.py
def get_min_scene_seconds() -> dict[str, float]                    # → scriptwriter.py
def get_skip_aux_figures_set() -> set[str]                         # → pipeline.py
def list_by_category(category: str) -> list[SceneSpec]
def all_scene_types() -> list[str]
```

### 2.3 收益

- **消除同步问题**：Prompt 中的场景表、Visual Director 的模板、Pacing Reviewer 的时长约束都从同一数据源生成
- **新增场景只需一处修改**：在 registry 中添加一个 `SceneSpec`，所有模块自动感知
- **可测试性**：对 registry 数据做静态验证（所有 SceneType 枚举值都有对应 spec、data_schema 非空等）

---

## 3. 三层架构（适配 4-Agent Pipeline）

### Layer 1: 候选池构建（规则引擎）

**位置**：`output/story_architect.py` 的 `_build_content_hints()` 升级为 `_build_scene_pool()`

```python
@dataclass
class SceneCandidate:
    scene_type: str
    score: float        # 0.0 ~ 1.0
    max_count: int      # 建议最大数量
    reason: str         # 推荐原因（注入 prompt）

@dataclass
class ScenePool:
    required: list[str]                # ["title", "overview", "conclusion"]
    candidates: list[SceneCandidate]   # 按 score 降序
    theme: str                         # "academic" | "popsci"
    budget: tuple[int, int]            # (min_scenes, max_scenes)
```

#### 映射规则

| 内容特征 | 触发条件 | 映射场景 | 分数 |
|----------|---------|---------|------|
| 有方法步骤 | `key_steps` 非空 | method | 1.0 |
| 有公式 | `formulas` >= 1 | formula | 0.9 |
| 有图表 | `figures` 非空 | figure | 0.9 |
| 有实验数据 | `findings` 非空 | result | 1.0 |
| 有核心概念 | `core_idea` > 20 字 或 `key_concepts` 非空 | concept | 0.7~0.8 |
| 有类比素材 | `analogies` 非空 或 theme == popsci | analogy | 0.5~0.85 |
| 有对比基线 | `baselines` >= 2 | comparison | 0.8 |
| 有组件关系 | `key_steps` >= 4 且 paper_type == system | relationship | 0.5 |
| 有代码片段 | `code_snippets` 非空 或 paper_type == system | code_demo | 0.6~0.8 |
| 系统+科普 | paper_type == system 且 theme == popsci | demo | 0.5 |
| 有关键要点 | `key_insights` >= 3 或 `contributions` >= 3 | summary_card | 0.7 |
| 科普主题 | theme == popsci | character_talk | 0.8 |

#### 场景预算

| 主题 | 最小 | 最大 | 建议总时长 |
|------|------|------|-----------|
| academic | 5 | 10 | 120~240s（与现有一致） |
| popsci | 7 | 12 | 120~300s |

> **v1 修正**：popsci 最大从 13 降为 12。13 × 20s = 260s 容易突破 300s 上限。

#### 输出示例

```python
ScenePool(
    required=["title", "overview", "conclusion"],
    candidates=[
        SceneCandidate("method", 1.0, 2, "6 个方法步骤"),
        SceneCandidate("result", 1.0, 1, "3 个基线对比"),
        SceneCandidate("formula", 0.9, 1, "1 个关键公式"),
        SceneCandidate("comparison", 0.8, 1, "3 个基线可做对比表"),
        SceneCandidate("concept", 0.7, 1, "有核心概念定义"),
        SceneCandidate("analogy", 0.5, 1, "方法可类比"),
    ],
    theme="academic",
    budget=(5, 10),
)
```

### Layer 2: Prompt 注入（替代 `_build_content_hints`）

`_build_pool_instruction(pool: ScenePool) -> str` 生成结构化指令，注入 Story Architect 的 user content：

```
### 本次候选场景池（根据论文内容分析得出）：

**必选场景**（不可省略）：title → overview → conclusion

**候选场景**（按推荐度排列，请从中选择合适的组合）：
- **method** [强烈推荐] score=1.0 — 6 个方法步骤，建议拆为 2 个
- **result** [强烈推荐] score=1.0 — 3 个基线对比
- **formula** [强烈推荐] score=0.9 — 1 个关键公式
- **comparison** [推荐] score=0.8 — 3 个基线可做对比表格
- **concept** [推荐] score=0.7 — 有核心概念需要定义
- **analogy** [可选] score=0.5 — 方法有类比价值

**场景总数**控制在 5~10 个（含必选）。
**不在候选池中的场景类型不可使用**。
```

### Layer 3: 后处理校验（在 `scriptwriter.py` 的 `generate_video_script` 中）

**位置**：在 Story Architect 返回 `StoryBlueprint` 后、进入 Agent 2-3-4 循环之前。

```python
def _validate_blueprint(blueprint: StoryBlueprint, pool: ScenePool) -> StoryBlueprint:
    """校验并修复蓝图。"""
    ...

def _build_fallback_blueprint(summary: PaperSummary) -> StoryBlueprint:
    """确定性降级：生成安全的 7 场景蓝图。"""
    ...
```

#### 校验规则

1. 第一个场景必须是 `title`
2. 最后一个场景必须是 `conclusion`
3. 必选场景（title, overview, conclusion）不可缺失
4. 所有场景类型必须属于候选池（required + candidates）
5. 场景总数在 `pool.budget` 范围内
6. 每种场景的数量不超过对应 `max_count`

#### 修复策略

| 问题 | 处理 |
|------|------|
| 缺少 `conclusion` | 自动追加到末尾 |
| 缺少 `overview` | 在 title 后插入 |
| 不在候选池中的场景类型 | 自动移除 |
| 场景数超过 budget 上限 | 移除分数最低的候选场景 |
| 场景数低于 budget 下限 | 按分数降序补充候选 |
| 严重问题（空蓝图 / 缺少 title） | 调用 `_build_fallback_blueprint()` |

---

## 4. 各模块具体改动

### 4.1 `schemas.py` — 数据模型扩展

新增 3 个字段到 `PaperSummary`（Optional，向后兼容）：

```python
class KeyConcept(BaseModel):
    term: str = Field(description="术语名称")
    definition: str = Field(description="一句话定义")
    related_terms: list[str] = Field(default_factory=list)

class Analogy(BaseModel):
    concept: str = Field(description="技术概念")
    analogy: str = Field(description="生活类比")
    mapping: str = Field(default="", description="映射说明")

class PaperSummary(BaseModel):
    # ... 已有字段 ...
    key_concepts: list[KeyConcept] = Field(default_factory=list, description="核心概念列表")
    analogies: list[Analogy] = Field(default_factory=list, description="概念类比列表")
    code_snippets: list[str] = Field(default_factory=list, description="代码片段列表")
```

### 4.2 `output/story_architect.py` — 候选池 + 蓝图校验

```
变更清单：
├── _build_content_hints()  →  重命名为 _build_scene_pool()，返回 ScenePool
├── 新增 _build_pool_instruction()  —  ScenePool → 注入 prompt 的文本
├── plan_story()  —  将候选池文本替代原 content_hints 注入 user_content
└── 新增 validate_blueprint()  —  在 scriptwriter.py 中调用
```

### 4.3 `prompts/story_architect.py` — 扩展场景类型表

将场景类型表从 7 种扩展到 15 种。内容**从 scene_registry 动态生成**（通过辅助函数），避免手动同步。

```python
from ..scene_registry import get_word_ranges, get_spec, all_scene_types

def _build_scene_type_table() -> str:
    """从 registry 生成 prompt 中的场景类型表。"""
    lines = ["| 类型 | 分类 | 用途 | 建议时长 | 字数范围 |",
             "|------|------|------|---------|---------|"]
    for st in all_scene_types():
        spec = get_spec(st)
        d_lo, d_hi = spec.duration_bounds
        w_lo, w_hi = spec.narration_word_range
        lines.append(f"| {st} | {spec.category} | {spec.description} | {d_lo:.0f}-{d_hi:.0f}s | {w_lo}-{w_hi} |")
    return "\n".join(lines)

STORY_ARCHITECT_SYSTEM_PROMPT = f"""\
...
### 可用场景类型：

{_build_scene_type_table()}

### 重要约束：
- **只能使用用户消息中「候选场景池」列出的场景类型**
- 不在候选池中的场景类型不可使用
...
"""
```

新增的规划原则：
- `concept` / `analogy` / `character_talk` 等科普场景在 academic 主题下不推荐
- `demo` / `code_demo` 仅当候选池中明确出现时才可使用
- 同类型场景（如多个 method）之间应穿插其他场景，避免连续重复

### 4.4 `prompts/scene_writer.py` — 扩展旁白指南和 data schema

新增 8 种场景的旁白写作要求和 data 字段格式。内容**从 scene_registry 动态生成**。

```python
from ..scene_registry import get_narration_guides, get_data_schemas

def _build_narration_rules() -> str:
    """从 registry 生成所有场景的旁白写作规则。"""
    ...

def _build_data_schema_section() -> str:
    """从 registry 生成所有场景的 data 字段格式。"""
    ...
```

各新增场景的 data schema 定义：

| 场景 | data 字段 |
|------|----------|
| concept | `{term, definition, related_terms?, formulas?}` |
| analogy | `{concept, analogy, mapping?, illustration?}` |
| comparison | `{title, columns: [{name, values: [str]}], highlight_column?}` |
| relationship | `{title, nodes: [{id, label}], edges: [{from, to, label?}]}` |
| demo | `{demo_type: "terminal"\|"chat"\|"editor", title, content}` |
| code_demo | `{language, code, highlights?: [line_numbers], title?}` |
| character_talk | `{character, topic, talking_points: [str]}` |
| summary_card | `{title, items: [{icon?, text}]}` |

### 4.5 `output/visual_director.py` — 扩展编排模板

**从 registry 获取模板**，替代硬编码的 `SCENE_TEMPLATES`：

```python
from ..scene_registry import get_templates

SCENE_TEMPLATES = get_templates()
```

新增 8 种场景的编排模板设计：

```python
# 以下模板将注册到 scene_registry.py 中

"concept": [
    {"pct_start": 0.0, "pct_end": 0.2, "mode": "voice_primary", "elements": ["term"], "transition": "fade_in"},
    {"pct_start": 0.2, "pct_end": 0.5, "mode": "synced", "elements": ["term", "definition"], "transition": "scale_in"},
    {"pct_start": 0.5, "pct_end": 1.0, "mode": "synced", "elements": ["term", "definition", "related_terms"], "transition": "fade_in"},
],

"analogy": [
    {"pct_start": 0.0, "pct_end": 0.35, "mode": "voice_primary", "elements": ["concept"], "transition": "fade_in"},
    {"pct_start": 0.35, "pct_end": 0.65, "mode": "visual_primary", "elements": ["concept", "analogy"], "transition": "slide_in"},
    {"pct_start": 0.65, "pct_end": 1.0, "mode": "synced", "elements": ["concept", "analogy", "mapping"], "transition": "fade_in"},
],

"comparison": [
    {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
    {"pct_start": 0.15, "pct_end": 1.0, "mode": "synced", "elements": ["title", "table"], "transition": "slide_in"},
],

"relationship": [
    {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
    {"pct_start": 0.15, "pct_end": 0.5, "mode": "visual_primary", "elements": ["nodes"], "transition": "scale_in"},
    {"pct_start": 0.5, "pct_end": 1.0, "mode": "synced", "elements": ["nodes", "edges"], "transition": "fade_in"},
],

"demo": [
    {"pct_start": 0.0, "pct_end": 0.1, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
    {"pct_start": 0.1, "pct_end": 1.0, "mode": "visual_primary", "elements": ["title", "content"], "transition": "scale_in"},
],

"code_demo": [
    {"pct_start": 0.0, "pct_end": 0.1, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
    {"pct_start": 0.1, "pct_end": 0.4, "mode": "visual_primary", "elements": ["code"], "transition": "scale_in"},
    {"pct_start": 0.4, "pct_end": 1.0, "mode": "synced", "elements": ["code", "highlights"], "transition": "none"},
],

"character_talk": [
    {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["character"], "transition": "scale_in"},
    {"pct_start": 0.15, "pct_end": 1.0, "mode": "synced", "elements": ["character", "talking_points"], "transition": "fade_in"},
],

"summary_card": [
    {"pct_start": 0.0, "pct_end": 0.1, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
    {"pct_start": 0.1, "pct_end": 1.0, "mode": "synced", "elements": ["title", "items"], "transition": "slide_in"},
],
```

同时扩展 `_assign_manim_for_scene()` 中的 Manim 动画分配：
- `comparison` 场景：可分配表格/柱状图动画
- `relationship` 场景：可分配节点-边动画（已有 Manim 能力）
- `concept` 场景：保留已有的公式写入逻辑
- 其他新场景暂不分配 Manim（可后续扩展）

### 4.6 `output/pacing_reviewer.py` — 扩展约束

**从 registry 获取时长约束**：

```python
from ..scene_registry import get_duration_bounds

SCENE_DURATION_BOUNDS = get_duration_bounds()
```

同时新增 `visual_pause` 配置：

```python
from ..scene_registry import get_visual_pauses

# 替代硬编码的 visual_pause dict
visual_pause_config = get_visual_pauses()
```

### 4.7 `output/scriptwriter.py` — 蓝图校验集成

在 `generate_video_script()` 中：

```python
def generate_video_script(...) -> VideoScript:
    # --- Agent 1: Story Architect ---
    pool = _build_scene_pool(summary, theme)  # 新增：构建候选池
    blueprint = plan_story(
        summary,
        scene_pool=pool,  # 新增：传入候选池
        model=story_model,
        ...
    )

    # --- 新增：蓝图校验 ---
    blueprint = _validate_blueprint(blueprint, pool)
    if blueprint is None:
        logger.warning("蓝图校验失败，降级到确定性模式")
        blueprint = _build_fallback_blueprint(summary)

    # --- Agent 2 + 3 + 4 循环（不变） ---
    ...
```

同时扩展以下硬编码字典，改为从 registry 读取：
- `VISUAL_PAUSE_SECONDS` → `get_visual_pauses()`
- `MIN_SCENE_SECONDS` → `get_min_scene_seconds()`

### 4.8 `pipeline.py` — 图片分配

新增 `_SKIP_AUX_FIGURES`，从 registry 获取：

```python
from .scene_registry import get_skip_aux_figures_set

_SKIP_AUX_FIGURES = get_skip_aux_figures_set()
# 预期值: {"formula", "figure", "character_talk", "code_demo", "demo"}
```

### 4.9 `extraction/` — 提取增强

在 Pass 2 prompt 中新增字段提取指令，使 LLM 输出 `key_concepts`、`analogies`、`code_snippets`。

这些字段为 Optional，提取失败不影响整体流程。synthesis 阶段做交叉验证：
- `key_concepts` 不为空时，确保 `term` 和 `definition` 非空
- `analogies` 不为空时，确保 `concept` 和 `analogy` 非空
- `code_snippets` 验证基本格式（非空字符串）

---

## 5. 全部 15 种场景规格一览

### 通用场景（universal）

| 场景 | 时长 | 字数 | 视觉停顿 | 跳过辅助图片 |
|------|------|------|---------|-------------|
| title | 5~10s | 15~35 | 0s | 否 |
| overview | 15~35s | 60~120 | 0s | 否 |
| conclusion | 10~22s | 40~80 | 0s | 否 |

### 学术场景（academic）

| 场景 | 时长 | 字数 | 视觉停顿 | 跳过辅助图片 |
|------|------|------|---------|-------------|
| method | 15~35s | 60~120 | 2s | 否 |
| formula | 15~30s | 55~100 | 5s | 是 |
| figure | 12~25s | 50~85 | 4s | 是 |
| result | 15~32s | 60~110 | 2s | 否 |

### 科普/增强场景（popsci）

| 场景 | 时长 | 字数 | 视觉停顿 | 跳过辅助图片 |
|------|------|------|---------|-------------|
| concept | 12~25s | 50~90 | 1s | 否 |
| analogy | 15~28s | 60~100 | 0s | 否 |
| comparison | 12~25s | 50~90 | 2s | 否 |
| relationship | 15~28s | 60~100 | 2s | 否 |
| demo | 12~25s | 40~80 | 3s | 是 |
| code_demo | 12~25s | 40~80 | 3s | 是 |
| character_talk | 10~20s | 40~70 | 0s | 是 |
| summary_card | 10~20s | 30~60 | 0s | 否 |

---

## 6. 数据流全景

```
PDF
 │
 ▼
┌─────────────────────────────────────────────────┐
│ Extraction Pipeline (extractor.py)              │
│  Pass 1 → PaperOverview                         │
│  Pass 2 → PaperSummary                          │
│           (新增: key_concepts/analogies/         │
│            code_snippets)                        │
│  Pass 3 → Figure Analysis                       │
└─────────────────────────────────────────────────┘
 │
 ▼
PaperSummary
 │
 ▼
┌─────────────────────────────────────────────────┐
│ scriptwriter.py: generate_video_script()        │
│                                                 │
│  1. _build_scene_pool(summary, theme)           │
│     → ScenePool (规则引擎)                       │
│                                                 │
│  2. plan_story(summary, scene_pool=pool)         │
│     → StoryBlueprint (Story Architect + LLM)    │
│                                                 │
│  3. _validate_blueprint(blueprint, pool)         │
│     → 校验 + 修复 / 降级                         │
│                                                 │
│  4. Write-Choreograph-Review Loop:              │
│     ├── write_scenes() (Scene Writer)           │
│     ├── choreograph_scenes() (Visual Director)  │
│     └── review_pacing() (Pacing Reviewer)       │
│                                                 │
│  5. 组装 VideoScript                             │
└─────────────────────────────────────────────────┘
 │
 ▼
VideoScript (Scene[])
 │
 ▼
┌─────────────────────────────────────────────────┐
│ pipeline.py: script_node()                      │
│  图片分配（跳过 _SKIP_AUX_FIGURES 中的场景）      │
│  缓存 → JSON 输出                                │
└─────────────────────────────────────────────────┘
 │
 ▼
Remotion (15 种场景组件，无需改动)
```

---

## 7. 实施计划

### Phase 1: 基础设施（预计 1~2 天）

| 序号 | 任务 | 文件 |
|------|------|------|
| 1.1 | 创建 `scene_registry.py`，注册全部 15 种场景的 SceneSpec | 新建 |
| 1.2 | `schemas.py` 新增 `KeyConcept`、`Analogy`、`PaperSummary` 三个字段 | 修改 |
| 1.3 | 单元测试：registry 数据完整性校验 | 新建 |

### Phase 2: Agent 适配（预计 2~3 天）

| 序号 | 任务 | 文件 |
|------|------|------|
| 2.1 | `story_architect.py`：实现 `_build_scene_pool()` + `_build_pool_instruction()` | 修改 |
| 2.2 | `prompts/story_architect.py`：从 registry 生成 15 种场景表 + 候选池约束 | 修改 |
| 2.3 | `prompts/scene_writer.py`：从 registry 生成 15 种旁白指南 + data schema | 修改 |
| 2.4 | `scriptwriter.py`：集成蓝图校验 + 降级逻辑 | 修改 |
| 2.5 | `visual_director.py`：从 registry 获取模板，扩展 8 种编排 | 修改 |
| 2.6 | `pacing_reviewer.py`：从 registry 获取约束 | 修改 |

### Phase 3: 提取增强 + 图片分配（预计 1 天）

| 序号 | 任务 | 文件 |
|------|------|------|
| 3.1 | Pass 2 prompt 新增字段提取 | prompts/extraction_*.py |
| 3.2 | `pipeline.py` 图片分配适配 | 修改 |

### Phase 4: 渐进验证（持续）

| 序号 | 任务 |
|------|------|
| 4.1 | 先只开放 3 个新场景（concept, comparison, analogy），验证端到端 |
| 4.2 | 验证通过后，开放剩余 5 个场景 |
| 4.3 | 清除旧缓存，回归测试 |

---

## 8. 向后兼容性

| 方面 | 兼容性 | 说明 |
|------|--------|------|
| PaperSummary JSON | ✅ 完全兼容 | 新字段有默认值 |
| SceneType enum | ✅ 完全兼容 | 仅新增引用，未修改枚举值 |
| pipeline.py | ✅ 完全兼容 | 新场景按 skip_aux_figures 决定 |
| 前端 Remotion | ✅ 无需改动 | 组件已全部就绪 |
| 降级 fallback | ✅ 有保障 | 校验失败回退到 7 场景确定性蓝图 |
| 缓存 | ⚠️ 建议清除 | 新候选池逻辑会改变脚本结构 |
| LLM 模型依赖 | ⚠️ 需注意 | 15 种场景的 prompt 更长，确保模型 context 足够 |

---

## 9. 扩展指南

### 新增场景类型（一站式流程）

1. **scene_registry.py**：添加一个 `SceneSpec`（包含所有元信息）
2. **schemas.py**：在 `SceneType` 枚举中添加值
3. **story_architect.py**：在 `_build_scene_pool()` 中添加触发条件
4. **前端**：创建场景组件 → 注册到 `sceneComponentMap`
5. **前端 types/script.ts**：添加 Zod schema

> 步骤 2~6 的 Prompt/模板/约束会自动从 registry 生成，无需手动添加。

### 调整推荐策略

修改 `_build_scene_pool()` 中的 score 计算：

| 分数区间 | 标签 | 含义 |
|----------|------|------|
| >= 0.8 | 强烈推荐 | Story Architect 几乎总会选择 |
| 0.6~0.8 | 推荐 | 根据内容丰富度决定 |
| < 0.6 | 可选 | 仅在内容特别匹配时选择 |

### 调整场景预算

在 `scene_registry.py` 中修改：

```python
SCENE_BUDGET: dict[str, tuple[int, int]] = {
    "academic": (5, 10),
    "popsci": (7, 12),
}
```

---

## 10. 与 v1 方案的关键差异

| 维度 | v1 | v2 |
|------|----|----|
| 改动入口 | `scriptwriter.py` 单文件 | 分散到 4 个 Agent + 2 个 Prompt |
| SCRIPT_SYSTEM_PROMPT | 单一巨大 prompt | 拆分到 story_architect + scene_writer |
| scene_registry | 独立查询表 | Single Source of Truth，驱动所有模块 |
| Visual Director | 未提及 | 完整的 8 种新模板 |
| Pacing Reviewer | 未提及 | 扩展时长约束 |
| 校验位置 | Layer 3 校验所有内容 | 蓝图校验（结构）+ Pacing Reviewer（内容） |
| 降级策略 | 回退到 `_plan_scenes_legacy()` | 回退到确定性 7 场景蓝图 |
| popsci 上限 | 13 个场景 | 12 个（避免超时长） |
