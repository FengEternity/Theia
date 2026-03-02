# 信息提取优化方案 — 技术设计文档

> 版本: v1.0 | 日期: 2026-02-28  
> 关联: HYBRID_SCENE_SELECTION_v2.md（混合场景选择系统）

---

## 1. 问题分析

### 1.1 提取内容过于简洁

当前 Pass 2 的输出格式紧耦合于 7 场景模型。15 种场景需要更丰富的素材：

| 下游场景 | 需要的素材 | 当前提取状态 |
|----------|-----------|-------------|
| concept | 核心概念的术语 + 定义 + 关联词 | ❌ 不提取 |
| analogy | 技术概念 vs 日常类比 | ❌ 不提取 |
| code_demo | 代码片段（伪代码/算法） | ❌ 不提取 |
| comparison | 结构化的对比表格数据 | ⚠️ baselines 经常不完整 |
| relationship | 组件间依赖/调用关系 | ⚠️ key_steps 只有线性顺序 |
| summary_card | 面向观众的精炼要点 | ⚠️ key_insights 偏学术化 |
| character_talk | 科普友好的简化解释 | ❌ 不提取 |

### 1.2 实验结果图表提取缺失（Bug）

**根因**：Pass 3 图表分析只输出 `description` / `importance` / `figure_type`（自然语言描述），不提取结构化的实验数据。而 Pass 2 的文本提取在表格以图片形式嵌入时无法读到数字。

**数据流缺口**：

```
Pass 2 (文本) → results.baselines    只从文字中提取 → 图中数据丢失
Pass 3 (图片) → Figure.description    只输出描述文本 → 数值未结构化
_synthesize()                         不从 Figure 反哺 results
```

**影响**：result / comparison 场景展示空数据或不准确数据。

---

## 2. 设计目标

1. **从"学术信息提取"转向"视频素材提取"**：提取出来的信息应该直接可用于 15 种场景
2. **图表中的实验数据必须结构化提取**：figure_type 为 result/table/comparison 的图片需要提取数值
3. **保持向后兼容**：所有新字段 Optional，旧数据可直接加载
4. **不大幅增加 token 消耗**：通过精准的 prompt 引导而非增加 pass 数量来提升丰富度

---

## 3. 方案概览

```
Pass 1: 快速扫描（不变）
  ↓
  PaperOverview
  ↓
Pass 2: 深度提取（扩展输出字段 + 调整提取导向）
  ↓                                    ↘
  PaperSummary (enriched)         Pass 3: 图表分析（分两步走）
  ↓                                    │
  │                          ┌─────────┼─────────┐
  │                     Step 3a:    Step 3b:      │
  │                   所有图表     结果类图表      │
  │                 (描述+分类)   (数值提取)       │
  │                          └─────────┼──────────┘
  │                                    ↓
  │                              AnalyzedFigures
  │                              + ResultTableData
  ↓                                    ↓
  ┌────────────────────────────────────┐
  │ _synthesize_v2()                   │
  │  ① Pass 1 → Pass 2 融合（已有）    │
  │  ② Figure 数据反哺 results（新增） │
  │  ③ 新字段交叉验证（新增）           │
  └────────────────────────────────────┘
  ↓
  PaperSummary (final)
```

---

## 4. 具体改动

### 4.1 PaperSummary 数据模型扩展

```python
# schemas.py

class KeyConcept(BaseModel):
    """可用于 concept 场景的核心术语。"""
    term: str = Field(description="术语（如 Multi-Head Attention）")
    definition: str = Field(description="一句话通俗定义")
    related_terms: list[str] = Field(default_factory=list, description="关联术语")

class Analogy(BaseModel):
    """可用于 analogy 场景的技术类比。"""
    concept: str = Field(description="技术概念")
    analogy: str = Field(description="日常类比")
    mapping: str = Field(default="", description="为什么这个类比成立")

class ComponentRelation(BaseModel):
    """可用于 relationship 场景的组件关系。"""
    source: str = Field(description="源组件")
    target: str = Field(description="目标组件")
    relation: str = Field(description="关系描述（如 '输出传入', '依赖于'）")

class MethodDetail(BaseModel):
    summary: str
    key_steps: list[str] = Field(default_factory=list)
    formulas: list[str] = Field(default_factory=list)
    # 新增
    component_relations: list[ComponentRelation] = Field(
        default_factory=list,
        description="组件间依赖关系（用于 relationship 场景）",
    )

class PaperSummary(BaseModel):
    # ... 已有字段 ...

    # 新增字段（全部 Optional，向后兼容）
    key_concepts: list[KeyConcept] = Field(
        default_factory=list,
        description="核心概念列表（用于 concept 场景）",
    )
    analogies: list[Analogy] = Field(
        default_factory=list,
        description="技术类比列表（用于 analogy 场景）",
    )
    code_snippets: list[str] = Field(
        default_factory=list,
        description="代码片段/伪代码列表（用于 code_demo 场景）",
    )
    audience_takeaways: list[str] = Field(
        default_factory=list,
        description="面向普通观众的精炼要点（用于 summary_card / character_talk 场景）",
    )
```

### 4.2 Pass 2 Prompt 重构

**核心改变**：从"提取论文信息"转向"提取视频素材"。

#### 4.2.1 新增提取指令

在 `PASS2_PROMPT` 末尾追加新字段定义：

```
  "key_concepts": [
    {
      "term": "核心术语",
      "definition": "一句话通俗定义（假设观众没有专业背景）",
      "related_terms": ["关联术语1", "关联术语2"]
    }
  ],
  "analogies": [
    {
      "concept": "论文中的技术概念",
      "analogy": "日常生活中的类比（如'注意力机制就像聚光灯'）",
      "mapping": "为什么这个类比成立"
    }
  ],
  "code_snippets": ["算法伪代码或关键代码片段"],
  "audience_takeaways": [
    "面向普通观众的一句话要点（不使用术语）",
    "另一个直觉性的理解要点"
  ],
  "method": {
    "summary": "...",
    "key_steps": ["..."],
    "formulas": ["..."],
    "component_relations": [
      {"source": "组件A", "target": "组件B", "relation": "A的输出传入B"}
    ]
  }
```

#### 4.2.2 调整指导语风格

**Before**（当前，学术导向）：
```
- method.key_steps 至少 3-5 步，每步应自包含且信息丰富。
- 指标只提取论文中明确出现的数值，不要编造。
```

**After**（视频导向）：
```
- method.key_steps 至少 3-5 步。每步写成"动作+效果"格式，
  便于视频中逐步展示（如"将输入序列分成多个头 → 每个头独立计算注意力"）。
- method.component_relations：提取方法中组件间的数据流或依赖关系。
  只在方法有清晰的模块化结构时填写（如 Encoder → Decoder → Output Layer）。
  线性流程不需要填写（用 key_steps 表达即可）。
- key_concepts：提取 3-5 个论文中的核心术语并给出通俗定义。
  定义面向没有专业背景的观众，要直觉化而非学术化。
  如果论文本身就是定义新概念，务必提取。
- analogies：提取 1-3 个技术概念的日常类比。
  优先使用论文自己提出的类比；如果论文没有，则基于方法本质创造。
  只在类比确实恰当时填写，不要强行类比。
- code_snippets：如果论文包含算法伪代码或关键代码片段，原样提取。
  不要编造代码。system 类型论文优先提取。
- audience_takeaways：用 3-5 句"妈妈也能听懂"的话总结这篇论文。
  不使用术语，用直觉和类比表达。
- results.baselines：**从文字中提取所有可找到的对比数据**。
  如果文字中提到"详见 Table X"但没有给出具体数字，在 findings 中注明
  "关键数据在 Table X 图表中"，以提示后续图表分析步骤补充。
```

#### 4.2.3 字段优先级分层

为防止 token 不足时 LLM 省略新字段，设置优先级：

```
### 字段优先级（token 不足时按此顺序省略）：

**必填**（缺失视为提取失败）：
title, authors, problem, method.summary, method.key_steps, 
results.findings, conclusion

**重要**（尽量填写）：
results.baselines, results.metrics, results.datasets, 
contributions, key_insights, method.formulas

**增强**（有则提取，无则留空数组）：
key_concepts, analogies, audience_takeaways,
method.component_relations, code_snippets
```

### 4.3 Pass 3 图表分析增强（结果类图表数据提取）

#### 4.3.1 架构调整

当前 Pass 3 对所有图片统一用 `FIGURE_ANALYSIS_PROMPT` 分析。改为两步：

- **Step 3a**：所有图片走现有 `FIGURE_ANALYSIS_PROMPT`（保持不变）
- **Step 3b**：`figure_type` 为 `result` / `table` / `comparison` 的图片，追加一次 **数据提取调用**

```python
# figure_analyzer.py

RESULT_TABLE_EXTRACTION_PROMPT = """\
你是一位数据提取专家。给定一张包含实验结果或对比数据的论文图表，
请提取其中的结构化数据。

图片类型：{figure_type}
图片描述：{description}
图片标题：{caption}

请以有效的 JSON 响应（不加 Markdown 围栏）：

{{
  "has_numerical_data": true/false,
  "table_data": {{
    "column_headers": ["方法名", "指标1", "指标2"],
    "rows": [
      {{"method": "方法A", "values": {{"指标1": 85.3, "指标2": 92.1}}, "is_proposed": false}},
      {{"method": "本文方法", "values": {{"指标1": 91.2, "指标2": 95.8}}, "is_proposed": true}}
    ],
    "datasets": ["数据集名称"],
    "best_result_summary": "本文方法在指标1上达到 91.2，超出最优基线 5.9 个百分点"
  }},
  "chart_data": {{
    "chart_type": "bar|line|scatter|heatmap|other",
    "data_points": [
      {{"label": "系列名", "values": [{{"x": "类别/横轴值", "y": 数字}}]}}
    ],
    "key_comparison": "关键对比结论"
  }}
}}

指南：
- has_numerical_data: 图中是否包含可提取的数值（表格、柱状图、折线图等）
- 如果是表格，填写 table_data；如果是图表，填写 chart_data；可以两者都填
- 数值必须是图中真实可见的数字，不要编造
- is_proposed 标记哪个是本文提出的方法
- 如果图片模糊无法准确读数，在对应值填 null 并在 key_comparison 中说明
- 没有数值数据时 has_numerical_data 设为 false，table_data 和 chart_data 留空对象
"""
```

#### 4.3.2 提取流程

```python
def analyze_figures(figures, images_dir, paper_overview, ...) -> tuple[list[Figure], list[dict]]:
    """返回 (figures, result_table_data)"""

    # Step 3a: 所有图片基础分析（已有逻辑）
    analyzed = [_analyze_single_figure(...) for fig in figures]

    # Step 3b: 结果类图表追加数据提取
    result_table_data = []
    for fig in analyzed:
        if fig.figure_type in ("result", "table", "comparison"):
            try:
                table_data = _extract_result_data(
                    img_path, fig, model=model, api_key=api_key, api_base=api_base
                )
                if table_data.get("has_numerical_data"):
                    result_table_data.append({
                        "figure_path": fig.path,
                        "figure_type": fig.figure_type,
                        "caption": fig.caption,
                        **table_data,
                    })
            except Exception as exc:
                logger.warning("结果图表数据提取失败 %s: %s", fig.path, exc)

    return analyzed, result_table_data
```

#### 4.3.3 成本控制

Step 3b 只对满足以下条件的图片触发：
- `figure_type` 是 `result` / `table` / `comparison`
- `importance` >= 3（低重要性的结果图不值得额外调用）
- 预计每篇论文 0~3 张结果图需要追加提取
- 额外 token 消耗约 500~1000 tokens/图

### 4.4 Synthesis 增强：Figure 数据反哺

```python
# synthesize.py

def _synthesize_v2(
    summary: PaperSummary,
    overview: PaperOverview,
    original: str,
    result_table_data: list[dict] | None = None,
) -> PaperSummary:
    """增强版融合：
    1. Pass 1 → Pass 2 融合（已有）
    2. Figure 结果数据 → results 反哺（新增）
    3. 新字段交叉验证（新增）
    """
    # --- 已有逻辑 ---
    summary = _synthesize(summary, overview, original)

    # --- 新增：Figure 数据反哺 ---
    if result_table_data:
        summary = _merge_figure_results(summary, result_table_data)

    # --- 新增：新字段验证 ---
    summary = _validate_enriched_fields(summary)

    return summary


def _merge_figure_results(
    summary: PaperSummary,
    result_table_data: list[dict],
) -> PaperSummary:
    """将图表中提取的实验数据合并到 PaperSummary.results 中。

    策略：
    - 如果 Pass 2 已经提取了 baselines 且数据丰富（>=3 条），以 Pass 2 为主
    - 如果 Pass 2 的 baselines 为空或不完整（<3 条），用图表数据补充
    - 合并时做去重（按 method name + metric name）
    """
    existing_baselines = {
        (b.name.lower(), b.metric.lower())
        for b in summary.results.baselines
    }

    new_baselines = []
    new_datasets = set(summary.results.datasets)
    new_metrics_strs = set(summary.results.metrics)

    for table in result_table_data:
        td = table.get("table_data", {})
        if not td:
            continue

        # 提取 datasets
        for ds in td.get("datasets", []):
            if ds and ds not in new_datasets:
                new_datasets.add(ds)

        # 提取 baselines
        for row in td.get("rows", []):
            method_name = row.get("method", "")
            is_proposed = row.get("is_proposed", False)
            for metric_name, value in row.get("values", {}).items():
                key = (method_name.lower(), metric_name.lower())
                if key not in existing_baselines:
                    from ..schemas import BaselineResult
                    new_baselines.append(BaselineResult(
                        name=method_name,
                        metric=metric_name,
                        value=value,
                        highlight=is_proposed,
                    ))
                    existing_baselines.add(key)

        # 合并 chart_data
        cd = table.get("chart_data", {})
        if cd and cd.get("key_comparison"):
            comparison_note = cd["key_comparison"]
            if comparison_note not in summary.results.findings:
                summary.results.findings += f" {comparison_note}"

    # 只在 Pass 2 提取不充分时补充
    if len(summary.results.baselines) < 3 and new_baselines:
        summary.results.baselines.extend(new_baselines)
        logger.info(
            "从图表中补充了 %d 条 baselines（总计 %d 条）",
            len(new_baselines),
            len(summary.results.baselines),
        )

    if new_datasets - set(summary.results.datasets):
        added = new_datasets - set(summary.results.datasets)
        summary.results.datasets.extend(added)
        logger.info("从图表中补充了 %d 个 datasets", len(added))

    return summary


def _validate_enriched_fields(summary: PaperSummary) -> PaperSummary:
    """验证新增字段的基本质量。"""
    # key_concepts: 确保 term 和 definition 非空
    summary.key_concepts = [
        kc for kc in summary.key_concepts
        if kc.term.strip() and kc.definition.strip()
    ]

    # analogies: 确保类比有意义
    summary.analogies = [
        a for a in summary.analogies
        if a.concept.strip() and a.analogy.strip()
    ]

    # code_snippets: 确保非空且有内容
    summary.code_snippets = [
        cs for cs in summary.code_snippets
        if cs.strip() and len(cs.strip()) > 10
    ]

    # audience_takeaways: 确保非空
    summary.audience_takeaways = [
        t for t in summary.audience_takeaways
        if t.strip() and len(t.strip()) > 5
    ]

    return summary
```

---

## 5. Pass 1 增强（可选，低优先级）

当前 Pass 1 只扫描 abstract + introduction + conclusion，这对快速判断论文类型足够，
但可以增加一个小改进来帮助 Pass 2 更精准地提取：

```python
# 在 Pass 1 的 PaperOverview 中新增（Optional）：

class PaperOverview(BaseModel):
    # ... 已有字段 ...

    has_comparison_tables: bool = Field(
        default=False,
        description="论文是否包含方法对比表格",
    )
    has_code_or_algorithm: bool = Field(
        default=False,
        description="论文是否包含代码或算法伪代码",
    )
    analogy_hints: list[str] = Field(
        default_factory=list,
        description="论文自己使用的类比或直觉解释",
    )
```

这些信号可以帮助 Pass 2 的 prompt 动态调整：
- `has_comparison_tables=True` → Pass 2 重点提取对比数据
- `has_code_or_algorithm=True` → Pass 2 提取代码片段
- `analogy_hints` 非空 → Pass 2 重点提取类比

---

## 6. 分段提取（chunked extract）适配

当前长文本会走 `_pass2_chunked_extract()`，每个 chunk 独立提取后合并。
新字段需要在合并逻辑中处理：

```python
# sections.py 的 _merge_chunk_results() 中新增：

# key_concepts: 按 term 去重
seen_terms = set()
merged.key_concepts = []
for chunk_summary in chunk_summaries:
    for kc in chunk_summary.key_concepts:
        if kc.term.lower() not in seen_terms:
            seen_terms.add(kc.term.lower())
            merged.key_concepts.append(kc)

# analogies: 按 concept 去重
seen_concepts = set()
merged.analogies = []
for chunk_summary in chunk_summaries:
    for a in chunk_summary.analogies:
        if a.concept.lower() not in seen_concepts:
            seen_concepts.add(a.concept.lower())
            merged.analogies.append(a)

# code_snippets: 全部收集
merged.code_snippets = []
for chunk_summary in chunk_summaries:
    merged.code_snippets.extend(chunk_summary.code_snippets)

# audience_takeaways: 去重后保留
merged.audience_takeaways = list(dict.fromkeys(
    t for cs in chunk_summaries for t in cs.audience_takeaways
))
```

---

## 7. ExtractionEvaluator 扩展

当前评估器只检查 7 场景相关的字段质量。新增：

```python
# quality/evaluator.py

class L3Score(BaseModel):
    """Level 3: 增强场景素材评分。"""
    key_concepts_score: float = 0.0   # 0-2: 有概念且定义清晰
    analogies_score: float = 0.0       # 0-1: 有类比且恰当
    result_completeness: float = 0.0   # 0-2: baselines 数量和质量
    takeaways_score: float = 0.0       # 0-1: 有面向观众的要点

    @property
    def total(self) -> float:
        return (self.key_concepts_score + self.analogies_score
                + self.result_completeness + self.takeaways_score)
```

评分规则：
- `key_concepts`: 0 个 = 0 分, 1-2 个 = 1 分, 3+ 个且定义 >10 字 = 2 分
- `analogies`: 0 个 = 0 分, 1+ 个且 mapping 非空 = 1 分
- `result_completeness`: baselines 0 条 = 0 分, 1-2 条 = 1 分, 3+ 条且有 value = 2 分
- `takeaways`: 0 个 = 0 分, 3+ 个 = 1 分

---

## 8. 改动文件清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `schemas.py` | 修改 | 新增 KeyConcept/Analogy/ComponentRelation 模型，PaperSummary 新字段 |
| `prompts/extraction_pass2.py` | 修改 | 扩展输出格式 + 调整指导语风格 |
| `prompts/extraction_pass1.py` | 修改（可选） | 新增 has_comparison_tables 等信号字段 |
| `extraction/figure_analyzer.py` | 修改 | 新增 RESULT_TABLE_EXTRACTION_PROMPT + Step 3b |
| `extraction/synthesize.py` | 修改 | 新增 _merge_figure_results + _validate_enriched_fields |
| `extraction/multi_pass.py` | 修改 | 适配 analyze_figures 新返回值 |
| `extraction/sections.py` | 修改 | _merge_chunk_results 处理新字段 |
| `quality/evaluator.py` | 修改 | 新增 L3 评分 |

---

## 9. 实施顺序

### Phase A: 修复结果提取 Bug（优先级最高，1 天）

1. `figure_analyzer.py`：新增 `RESULT_TABLE_EXTRACTION_PROMPT` + `_extract_result_data()`
2. `synthesize.py`：新增 `_merge_figure_results()`
3. `multi_pass.py`：适配 Step 3b 流程
4. 验证：用包含结果表格图片的论文测试

### Phase B: 扩展 Pass 2 提取（1-2 天）

1. `schemas.py`：新增数据模型
2. `prompts/extraction_pass2.py`：扩展 prompt
3. `extraction/sections.py`：适配分段合并
4. `synthesize.py`：新增 `_validate_enriched_fields()`
5. 验证：对比扩展前后的提取结果丰富度

### Phase C: 评估与调优（持续）

1. `quality/evaluator.py`：新增 L3 评分
2. 在 5-10 篇不同类型论文上回归测试
3. 调优 Pass 2 prompt 的字段优先级和指导语

---

## 10. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| Pass 2 新字段导致总输出 token 超限 | LLM 截断，必填字段丢失 | 字段优先级分层，增强字段设为最低优先级 |
| Step 3b 额外 API 调用增加延迟 | 提取耗时增加 30-60s | 只对 importance≥3 的结果图触发；并行执行 |
| 图表中的数字被 OCR 错误识别 | baselines 数据不准确 | 在 findings 中保留自然语言描述作为兜底 |
| analogies 字段 LLM 生成牵强类比 | 质量差的 analogy 影响视频 | _validate_enriched_fields 过滤 + analogy 场景 score 较低（0.5） |
| 旧缓存中无新字段 | 下游场景选择失败 | 新字段全部 Optional + 默认空列表 |

---

## 11. 与混合场景选择的协同

本方案为混合场景选择系统提供更丰富的输入数据：

```
                   提取增强
                      │
    key_concepts ─────┼──→ concept 场景 score 计算
    analogies ────────┼──→ analogy 场景 score 计算
    code_snippets ────┼──→ code_demo 场景 score 计算
    component_relations ──→ relationship 场景 score 计算
    audience_takeaways ──→ character_talk / summary_card score 计算
    enriched baselines ──→ comparison / result 场景数据质量
```

`_build_scene_pool()` 中的映射规则可以直接基于这些字段判断：

```python
# 以前：只能粗略判断
if len(summary.method.key_steps) >= 4:
    candidates.append(SceneCandidate("relationship", 0.5, ...))

# 现在：精确判断
if summary.method.component_relations:
    candidates.append(SceneCandidate("relationship", 0.8, ...))
```
