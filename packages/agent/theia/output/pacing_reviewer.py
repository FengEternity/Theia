"""节奏审核员 (Pacing Reviewer): 检查视频脚本的节奏和注意力平衡。

Agent 4: 基于规则检查（Phase 1）和可选的 LLM 审核（Phase 3），
确保生成的视频脚本满足时长约束、节奏均衡和注意力管理要求。
"""

from __future__ import annotations

import logging

from ..scene_registry import get_duration_bounds, get_visual_pauses
from ..schemas import (
    AnimationPhase,
    ReviewResult,
    SceneNarration,
    StoryBlueprint,
    VisualChoreography,
)

logger = logging.getLogger(__name__)

SCENE_DURATION_BOUNDS: dict[str, tuple[float, float]] = get_duration_bounds()

CHARS_PER_SECOND_ZH = 3.5

MAX_SCENE_RATIO = 3.0
TOTAL_DURATION_RANGE = (120.0, 300.0)
MAX_REVIEW_ROUNDS = 2


def review_pacing(
    blueprint: StoryBlueprint,
    narrations: list[SceneNarration],
    choreographies: list[VisualChoreography],
    *,
    fps: int = 30,
    language: str = "zh",
) -> ReviewResult:
    """审核脚本的节奏、时长和注意力平衡。

    参数:
        blueprint: 故事蓝图。
        narrations: 各场景旁白。
        choreographies: 各场景视觉编排。
        fps: 视频帧率。
        language: 旁白语言。

    返回:
        :class:`ReviewResult` 审核结果。
    """
    issues: list[str] = []
    suggestions: list[str] = []

    cps = CHARS_PER_SECOND_ZH if language == "zh" else 12.0

    visual_pause = get_visual_pauses()

    scene_durations: list[float] = []
    for i, (plan, narr) in enumerate(zip(blueprint.scenes, narrations)):
        narr_seconds = max(len(narr.narration) / cps, 3.0)
        vp = visual_pause.get(plan.type, 0.0)
        est_seconds = narr_seconds + vp
        scene_durations.append(est_seconds)

        bounds = SCENE_DURATION_BOUNDS.get(plan.type, (10.0, 30.0))
        current_chars = len(narr.narration)
        if est_seconds < bounds[0]:
            target_chars = int((bounds[0] - vp) * cps)
            deficit = target_chars - current_chars
            issues.append(
                f"场景 {i} ({plan.type}): 预估时长 {est_seconds:.1f}s 低于下限 {bounds[0]}s，"
                f"当前旁白 {current_chars} 字"
            )
            suggestions.append(
                f"场景 {i} ({plan.type}): 旁白至少增加到 {target_chars} 字"
                f"（当前 {current_chars} 字，需补充约 {deficit} 字）"
            )
        elif est_seconds > bounds[1]:
            target_chars = int((bounds[1] - vp) * cps)
            excess = current_chars - target_chars
            issues.append(
                f"场景 {i} ({plan.type}): 预估时长 {est_seconds:.1f}s 超出上限 {bounds[1]}s，"
                f"当前旁白 {current_chars} 字"
            )
            suggestions.append(
                f"场景 {i} ({plan.type}): 旁白缩减到约 {target_chars} 字"
                f"（当前 {current_chars} 字，需删减约 {excess} 字）"
            )

    _check_word_count(blueprint, narrations, issues, suggestions)
    _check_duration_ratio(scene_durations, issues, suggestions)
    _check_total_duration(scene_durations, issues, suggestions)
    _check_attention_conflicts(choreographies, narrations, issues, suggestions)

    has_narration_issues = any("旁白" in s or "字" in s for s in suggestions)
    has_choreography_issues = any("编排" in s or "动画" in s for s in suggestions)

    if not issues:
        logger.info("节奏审核通过: %d 个场景, 总时长 %.0f 秒", len(narrations), sum(scene_durations))
        return ReviewResult(approved=True)

    revision_target = "both"
    if has_narration_issues and not has_choreography_issues:
        revision_target = "narration"
    elif has_choreography_issues and not has_narration_issues:
        revision_target = "choreography"

    logger.warning("节奏审核未通过: %d 个问题, 修改目标=%s", len(issues), revision_target)
    for issue in issues:
        logger.warning("  - %s", issue)

    return ReviewResult(
        approved=False,
        revision_target=revision_target,
        issues=issues,
        suggestions=suggestions,
    )


def _check_word_count(
    blueprint: StoryBlueprint,
    narrations: list[SceneNarration],
    issues: list[str],
    suggestions: list[str],
) -> None:
    """检查各场景旁白字数是否在蓝图指定范围内。"""
    for i, (plan, narr) in enumerate(zip(blueprint.scenes, narrations)):
        word_count = len(narr.narration)
        min_w, max_w = plan.narration_word_range
        if word_count < min_w:
            issues.append(
                f"场景 {i} ({plan.type}): 旁白仅 {word_count} 字，低于目标下限 {min_w} 字"
            )
            suggestions.append(
                f"场景 {i} ({plan.type}): 请将旁白扩充到至少 {min_w} 字"
                f"（当前 {word_count} 字，需再写 {min_w - word_count} 字），"
                f"可从论文摘要中补充更多细节"
            )
        elif word_count > max_w * 1.2:
            issues.append(
                f"场景 {i} ({plan.type}): 旁白 {word_count} 字，超出目标上限 {max_w} 字的 120%"
            )
            suggestions.append(
                f"场景 {i} ({plan.type}): 请将旁白精简到约 {max_w} 字"
                f"（当前 {word_count} 字，需删减约 {word_count - max_w} 字）"
            )


def _check_duration_ratio(
    durations: list[float],
    issues: list[str],
    suggestions: list[str],
) -> None:
    """检查最长/最短场景时长比。"""
    if len(durations) < 2:
        return
    max_d = max(durations)
    min_d = min(durations)
    if min_d > 0 and max_d / min_d > MAX_SCENE_RATIO:
        ratio = max_d / min_d
        issues.append(f"场景时长比 {ratio:.1f}x 超出 {MAX_SCENE_RATIO}x 上限")
        suggestions.append("缩短最长场景或扩充最短场景的旁白")


def _check_total_duration(
    durations: list[float],
    issues: list[str],
    suggestions: list[str],
) -> None:
    """检查总时长范围。"""
    total = sum(durations)
    min_total, max_total = TOTAL_DURATION_RANGE
    if total < min_total:
        deficit = min_total - total
        per_scene = deficit / max(len(durations), 1)
        issues.append(f"总时长 {total:.0f}s 低于 {min_total:.0f}s（差 {deficit:.0f}s）")
        suggestions.append(
            f"总时长不足，请每个场景平均增加约 {per_scene:.0f}s 的旁白内容"
            f"（约 {int(per_scene * 3.5)} 字/场景）"
        )
    elif total > max_total:
        excess = total - max_total
        issues.append(f"总时长 {total:.0f}s 超出 {max_total:.0f}s（超出 {excess:.0f}s）")
        suggestions.append("整体精简旁白内容，重点缩减最长的场景")


def _check_attention_conflicts(
    choreographies: list[VisualChoreography],
    narrations: list[SceneNarration],
    issues: list[str],
    suggestions: list[str],
) -> None:
    """检查是否存在注意力冲突（旁白和画面同时信息爆炸）。"""
    for choreo in choreographies:
        if not choreo.phases:
            continue
        for phase in choreo.phases:
            if phase.attention_mode == "visual_primary" and len(phase.elements_to_show) > 3:
                issues.append(
                    f"场景 {choreo.scene_index}: visual_primary 阶段 "
                    f"({phase.start_ms}-{phase.end_ms}ms) 同时展示 {len(phase.elements_to_show)} 个元素，过多"
                )
                suggestions.append(
                    f"场景 {choreo.scene_index}: 减少 visual_primary 阶段的同时可见元素数"
                )
