"""故事架构师 (Story Architect): 全局叙事规划。

Agent 1: 根据论文摘要规划视频的场景编排、叙事弧线和节奏目标。
替代原 scriptwriter 中的 _plan_scenes() 确定性函数，用 LLM 做更智能的规划。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Callable

from ..llm.client import robust_completion
from ..prompts.story_architect import STORY_ARCHITECT_SYSTEM_PROMPT
from ..schemas import PaperSummary, ScenePlan, StoryBlueprint
from ..scene_registry import SCENE_BUDGET

logger = logging.getLogger(__name__)


@dataclass
class SceneCandidate:
    """候选场景及其推荐信息。"""

    scene_type: str
    score: float
    max_count: int
    reason: str


@dataclass
class ScenePool:
    """规则引擎生成的候选场景池。"""

    required: list[str] = field(default_factory=lambda: ["title", "overview", "conclusion"])
    candidates: list[SceneCandidate] = field(default_factory=list)
    theme: str = "academic"
    budget: tuple[int, int] = (5, 10)


def plan_story(
    summary: PaperSummary,
    *,
    theme: str = "academic",
    scene_pool: ScenePool | None = None,
    model: str = "kimi-k2-0905-preview",
    api_key: str | None = None,
    api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
) -> tuple[StoryBlueprint, ScenePool]:
    """根据论文摘要生成故事蓝图。

    参数:
        summary: 提取的论文信息。
        theme: 视频主题 (academic/popsci)，影响场景池和预算。
        scene_pool: 候选场景池（可选）；为 None 时使用 content_hints 作为 fallback。
        model: LiteLLM 模型标识符。
        api_key: API 密钥（可选，覆盖环境变量）。
        api_base: API base URL（可选，覆盖环境变量）。
        on_token: 流式 token 回调。

    返回:
        (:class:`StoryBlueprint`, :class:`ScenePool`) 全片叙事规划与候选场景池。
    """
    summary_json = summary.model_dump_json(indent=2)

    if scene_pool is not None:
        pool_instruction = _build_pool_instruction(scene_pool)
        user_content = f"{pool_instruction}\n\n论文摘要：\n\n{summary_json}"
        pool = scene_pool
    else:
        content_hints = _build_content_hints(summary)
        user_content = f"{content_hints}\n\n论文摘要：\n\n{summary_json}" if content_hints else f"论文摘要：\n\n{summary_json}"
        pool = build_scene_pool(summary, theme)

    logger.info(
        "故事架构师: 输入论文 '%s', model=%s, api_base=%s",
        summary.title[:50],
        model,
        api_base or "(默认)",
    )

    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": STORY_ARCHITECT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 2048,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    response = robust_completion(kwargs, on_token=on_token)

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw[raw.index("\n") + 1 :]
    if raw.endswith("```"):
        raw = raw[:-3]

    data = json.loads(raw)

    scenes = []
    for s in data.get("scenes", []):
        dur_range = s.get("target_duration_range", [10.0, 30.0])
        word_range = s.get("narration_word_range", [50, 150])
        scenes.append(
            ScenePlan(
                type=s["type"],
                target_duration_range=(float(dur_range[0]), float(dur_range[1])),
                narrative_role=s.get("narrative_role", "build_up"),
                attention_strategy=s.get("attention_strategy", "synced"),
                key_moment=s.get("key_moment", False),
                narration_word_range=(int(word_range[0]), int(word_range[1])),
            )
        )

    blueprint = StoryBlueprint(
        narrative_arc=data.get("narrative_arc", ""),
        scenes=scenes,
        total_target_duration=tuple(data.get("total_target_duration", [120.0, 240.0])),
        key_moments=data.get("key_moments", []),
    )

    logger.info(
        "故事蓝图: %d 个场景, 目标 %.0f-%.0f 秒, 弧线: %s",
        len(blueprint.scenes),
        blueprint.total_target_duration[0],
        blueprint.total_target_duration[1],
        blueprint.narrative_arc[:60],
    )
    from collections import Counter

    type_counts = Counter(s.type for s in blueprint.scenes)
    logger.info("故事蓝图场景类型: %s", dict(type_counts))
    return blueprint, pool


def _build_content_hints(summary: PaperSummary) -> str:
    """根据论文内容生成提示信息，帮助架构师做出更好的规划。"""
    hints = ["### 论文内容特征（辅助规划）："]

    n_steps = len(summary.method.key_steps)
    n_formulas = len(summary.method.formulas)
    n_figures = len(summary.figures)
    n_baselines = len(summary.results.baselines)

    hints.append(f"- 方法步骤: {n_steps} 个")
    hints.append(f"- 关键公式: {n_formulas} 个")
    hints.append(f"- 图表: {n_figures} 张")
    hints.append(f"- 对比方法: {n_baselines} 个")

    if n_formulas == 0:
        hints.append("- **无关键公式，建议不安排 formula 场景**")
    if n_figures == 0:
        hints.append("- **无图表，建议不安排 figure 场景**")

    important_figs = [f for f in summary.figures if f.importance >= 3]
    if important_figs:
        hints.append(f"- 重要图表（importance≥3）: {len(important_figs)} 张")
        must_include = [f for f in summary.figures if f.importance == 5]
        if must_include:
            hints.append(f"- 必选图表（importance=5）: {len(must_include)} 张，必须安排 figure 场景")

    if n_steps >= 6:
        hints.append("- **方法步骤较多，建议拆分为 2 个 method 场景**")

    return "\n".join(hints)


def build_scene_pool(summary: PaperSummary, theme: str = "academic") -> ScenePool:
    """Layer 1 规则引擎：根据论文内容特征生成候选场景池。"""
    candidates: list[SceneCandidate] = []

    n_steps = len(summary.method.key_steps)
    n_formulas = len(summary.method.formulas)
    n_figures = len(summary.figures)
    n_baselines = len(summary.results.baselines)
    n_insights = len(summary.key_insights)
    n_contributions = len(summary.contributions)

    key_concepts = getattr(summary, "key_concepts", [])
    analogies = getattr(summary, "analogies", [])
    code_snippets = getattr(summary, "code_snippets", [])
    component_relations = getattr(summary.method, "component_relations", [])

    if n_steps > 0:
        max_count = 2 if n_steps >= 6 else 1
        candidates.append(SceneCandidate("method", 1.0, max_count, f"{n_steps} 个方法步骤"))

    if summary.results.findings:
        candidates.append(SceneCandidate("result", 1.0, 1, f"{n_baselines} 个基线, {len(summary.results.datasets)} 个数据集"))

    if n_formulas >= 1:
        candidates.append(SceneCandidate("formula", 0.9, min(n_formulas, 2), f"{n_formulas} 个关键公式"))

    important_figs = [f for f in summary.figures if f.importance >= 3]
    if important_figs:
        max_fig = min(len(important_figs), 4)
        candidates.append(SceneCandidate("figure", 0.9, max_fig, f"{len(important_figs)} 张重要图表"))

    if n_baselines >= 2:
        candidates.append(SceneCandidate("comparison", 0.8, 1, f"{n_baselines} 个基线可做对比表格"))

    if key_concepts:
        candidates.append(SceneCandidate("concept", 0.8, 1, f"{len(key_concepts)} 个核心概念"))
    elif summary.core_idea and len(summary.core_idea) > 20:
        candidates.append(SceneCandidate("concept", 0.7, 1, "有核心概念需要定义"))

    if component_relations:
        candidates.append(SceneCandidate("relationship", 0.8, 1, f"{len(component_relations)} 个组件关系"))
    elif n_steps >= 4 and summary.paper_type in ("system", "empirical"):
        candidates.append(SceneCandidate("relationship", 0.5, 1, "方法步骤较多，可能有组件关系"))

    if n_insights >= 3 or n_contributions >= 3:
        candidates.append(SceneCandidate("summary_card", 0.7, 1, f"{n_insights} 个洞察, {n_contributions} 个贡献"))

    if analogies:
        candidates.append(SceneCandidate("analogy", 0.85, 1, f"{len(analogies)} 个类比"))
    elif theme == "popsci":
        candidates.append(SceneCandidate("analogy", 0.6, 1, "科普主题，可创造类比"))

    if code_snippets:
        candidates.append(SceneCandidate("code_demo", 0.8, 1, f"{len(code_snippets)} 个代码片段"))
    elif summary.paper_type == "system":
        candidates.append(SceneCandidate("code_demo", 0.6, 1, "系统类论文，可能有代码"))

    if summary.paper_type == "system" and theme == "popsci":
        candidates.append(SceneCandidate("demo", 0.5, 1, "系统论文+科普主题"))

    if theme == "popsci":
        candidates.append(SceneCandidate("character_talk", 0.8, 1, "科普主题"))

    candidates.sort(key=lambda c: c.score, reverse=True)

    budget = SCENE_BUDGET.get(theme, SCENE_BUDGET["academic"])

    pool = ScenePool(
        candidates=candidates,
        theme=theme,
        budget=budget,
    )

    logger.info(
        "场景池构建: theme=%s, budget=%s, 必选=%d, 候选=%d",
        theme, budget, len(pool.required), len(pool.candidates),
    )
    return pool


def _build_pool_instruction(pool: ScenePool) -> str:
    """将候选池转换为注入 Story Architect prompt 的文本。"""
    lines = ["### 本次候选场景池（根据论文内容分析得出）：", ""]
    lines.append(f"**必选场景**（不可省略）：{' → '.join(pool.required)}")
    lines.append("")
    lines.append("**候选场景**（请根据内容选择合适的组合，按推荐度排列）：")

    for c in pool.candidates:
        if c.score >= 0.8:
            tag = "强烈推荐"
        elif c.score >= 0.6:
            tag = "推荐"
        else:
            tag = "可选"

        count_hint = f"（最多 {c.max_count} 个）" if c.max_count > 1 else ""
        lines.append(f"- **{c.scene_type}** [{tag}] — {c.reason}{count_hint}")

    min_s, max_s = pool.budget
    lines.append("")
    lines.append(f"场景总数控制在 **{min_s}-{max_s}** 个（含必选）。")
    lines.append("**不在候选池中的场景类型不可使用。**")

    return "\n".join(lines)
