"""故事架构师 (Story Architect): 全局叙事规划。

Agent 1: 根据论文摘要规划视频的场景编排、叙事弧线和节奏目标。
替代原 scriptwriter 中的 _plan_scenes() 确定性函数，用 LLM 做更智能的规划。
"""

from __future__ import annotations

import json
import logging
from typing import Callable

from ..llm.client import robust_completion
from ..prompts.story_architect import STORY_ARCHITECT_SYSTEM_PROMPT
from ..schemas import PaperSummary, ScenePlan, StoryBlueprint

logger = logging.getLogger(__name__)


def plan_story(
    summary: PaperSummary,
    *,
    model: str = "kimi-k2-0905-preview",
    api_key: str | None = None,
    api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
) -> StoryBlueprint:
    """根据论文摘要生成故事蓝图。

    参数:
        summary: 提取的论文信息。
        model: LiteLLM 模型标识符。
        api_key: API 密钥（可选，覆盖环境变量）。
        api_base: API base URL（可选，覆盖环境变量）。
        on_token: 流式 token 回调。

    返回:
        :class:`StoryBlueprint` 全片叙事规划。
    """
    summary_json = summary.model_dump_json(indent=2)

    content_hints = _build_content_hints(summary)

    user_content = f"论文摘要：\n\n{summary_json}"
    if content_hints:
        user_content = f"{content_hints}\n\n{user_content}"

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
    return blueprint


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
