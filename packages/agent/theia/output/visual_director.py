"""视觉导演 (Visual Director): 基于规则引擎的动画编排。

Agent 3: 根据场景类型、word_timings 和注意力标注，
为每个场景生成精确的动画阶段（AnimationPhase）。

初始版本使用规则引擎（无需 LLM），后续可升级为 LLM 驱动。
"""

from __future__ import annotations

import logging

from ..schemas import (
    AnimationPhase,
    SceneNarration,
    StoryBlueprint,
    VisualChoreography,
    WordTiming,
)

logger = logging.getLogger(__name__)

SCENE_TEMPLATES: dict[str, list[dict]] = {
    "title": [
        {"pct_start": 0.0, "pct_end": 1.0, "mode": "voice_primary", "elements": ["title", "authors", "year"], "transition": "fade_in"},
    ],
    "overview": [
        {"pct_start": 0.0, "pct_end": 0.3, "mode": "voice_primary", "elements": ["problem"], "transition": "fade_in"},
        {"pct_start": 0.3, "pct_end": 1.0, "mode": "synced", "elements": ["problem", "contributions"], "transition": "slide_in"},
    ],
    "method": [
        {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["summary"], "transition": "fade_in"},
    ],
    "formula": [
        {"pct_start": 0.0, "pct_end": 0.12, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
        {"pct_start": 0.12, "pct_end": 0.35, "mode": "visual_primary", "elements": ["title", "formula"], "transition": "scale_in"},
        {"pct_start": 0.35, "pct_end": 1.0, "mode": "synced", "elements": ["title", "formula", "explanation"], "transition": "fade_in"},
    ],
    "figure": [
        {"pct_start": 0.0, "pct_end": 0.2, "mode": "visual_primary", "elements": ["image"], "transition": "scale_in"},
        {"pct_start": 0.2, "pct_end": 0.35, "mode": "visual_primary", "elements": ["image"], "transition": "none"},
        {"pct_start": 0.35, "pct_end": 1.0, "mode": "synced", "elements": ["image", "caption", "description"], "transition": "fade_in"},
    ],
    "result": [
        {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["datasets"], "transition": "fade_in"},
        {"pct_start": 0.15, "pct_end": 1.0, "mode": "synced", "elements": ["datasets", "metrics", "findings"], "transition": "slide_in"},
    ],
    "conclusion": [
        {"pct_start": 0.0, "pct_end": 0.3, "mode": "voice_primary", "elements": ["conclusion"], "transition": "fade_in"},
        {"pct_start": 0.3, "pct_end": 1.0, "mode": "synced", "elements": ["conclusion", "contributions"], "transition": "fade_in"},
    ],
}


def choreograph_scenes(
    blueprint: StoryBlueprint,
    narrations: list[SceneNarration],
    scene_word_timings: list[list[WordTiming]],
    scene_durations_ms: list[int],
) -> list[VisualChoreography]:
    """为所有场景生成视觉编排。

    参数:
        blueprint: 故事蓝图。
        narrations: 各场景旁白及标注。
        scene_word_timings: 各场景的 word_timings（来自 TTS）。
        scene_durations_ms: 各场景实际时长（毫秒）。

    返回:
        每个场景的视觉编排列表。
    """
    choreographies: list[VisualChoreography] = []

    for i, scene_plan in enumerate(blueprint.scenes):
        duration_ms = scene_durations_ms[i] if i < len(scene_durations_ms) else 10000
        word_timings = scene_word_timings[i] if i < len(scene_word_timings) else []
        narration = narrations[i] if i < len(narrations) else None

        scene_type = scene_plan.type

        if scene_type == "method":
            phases = _choreograph_method(narration, word_timings, duration_ms)
        else:
            phases = _choreograph_from_template(scene_type, duration_ms, narration)

        choreographies.append(VisualChoreography(scene_index=i, phases=phases))

    logger.info(
        "视觉编排完成: %d 个场景, 共 %d 个动画阶段",
        len(choreographies),
        sum(len(c.phases) for c in choreographies),
    )
    return choreographies


def _choreograph_from_template(
    scene_type: str,
    duration_ms: int,
    narration: SceneNarration | None,
) -> list[AnimationPhase]:
    """基于场景类型模板生成动画阶段。"""
    template = SCENE_TEMPLATES.get(scene_type, SCENE_TEMPLATES["overview"])
    phases: list[AnimationPhase] = []

    for tmpl in template:
        start_ms = int(tmpl["pct_start"] * duration_ms)
        end_ms = int(tmpl["pct_end"] * duration_ms)
        phases.append(
            AnimationPhase(
                start_ms=start_ms,
                end_ms=end_ms,
                attention_mode=tmpl["mode"],
                elements_to_show=list(tmpl["elements"]),
                transition_type=tmpl["transition"],
            )
        )

    if narration and narration.attention_markers:
        phases = _refine_with_markers(phases, narration, duration_ms)

    return phases


def _choreograph_method(
    narration: SceneNarration | None,
    word_timings: list[WordTiming],
    duration_ms: int,
) -> list[AnimationPhase]:
    """为 method 场景生成逐步揭示的动画阶段。"""
    step_count = 0
    if narration and narration.data:
        steps = narration.data.get("steps", [])
        step_count = len(steps)

    if step_count == 0:
        return _choreograph_from_template("method", duration_ms, narration)

    phases: list[AnimationPhase] = []

    summary_end_ms = int(0.15 * duration_ms)
    phases.append(
        AnimationPhase(
            start_ms=0,
            end_ms=summary_end_ms,
            attention_mode="voice_primary",
            elements_to_show=["summary"],
            transition_type="fade_in",
        )
    )

    steps_duration_ms = duration_ms - summary_end_ms
    step_duration = steps_duration_ms // step_count

    if word_timings:
        step_boundaries = _find_step_boundaries(word_timings, step_count, summary_end_ms, duration_ms)
    else:
        step_boundaries = [
            (summary_end_ms + i * step_duration, summary_end_ms + (i + 1) * step_duration)
            for i in range(step_count)
        ]

    for i, (start, end) in enumerate(step_boundaries):
        visible = ["summary"] + [f"step_{j}" for j in range(i + 1)]
        phases.append(
            AnimationPhase(
                start_ms=start,
                end_ms=end,
                attention_mode="synced",
                elements_to_show=visible,
                highlight_element=f"step_{i}",
                transition_type="slide_in",
            )
        )

    return phases


def _find_step_boundaries(
    word_timings: list[WordTiming],
    step_count: int,
    summary_end_ms: int,
    duration_ms: int,
) -> list[tuple[int, int]]:
    """利用 word_timings 找到每个步骤的时间边界。

    查找包含"第X步"、"首先"、"然后"、"接着"、"最后"等标记词的位置。
    找不到时退化为均分。
    """
    trigger_patterns = ["第一", "第二", "第三", "第四", "第五", "第六", "首先", "然后", "接着", "其次", "最后"]
    found_offsets: list[int] = []

    accumulated_text = ""
    for wt in word_timings:
        prev_len = len(accumulated_text)
        accumulated_text += wt.text
        for pattern in trigger_patterns:
            if pattern in accumulated_text[prev_len:]:
                found_offsets.append(wt.offset_ms)
                break

    if len(found_offsets) < step_count:
        step_duration = (duration_ms - summary_end_ms) // step_count
        return [
            (summary_end_ms + i * step_duration, summary_end_ms + (i + 1) * step_duration)
            for i in range(step_count)
        ]

    found_offsets = sorted(set(found_offsets))[:step_count]

    boundaries: list[tuple[int, int]] = []
    for i, offset in enumerate(found_offsets):
        start = max(offset, summary_end_ms)
        end = found_offsets[i + 1] if i + 1 < len(found_offsets) else duration_ms
        boundaries.append((start, end))

    return boundaries


def _refine_with_markers(
    phases: list[AnimationPhase],
    narration: SceneNarration,
    duration_ms: int,
) -> list[AnimationPhase]:
    """根据旁白中的注意力标注微调动画阶段。

    将标注的模式切换点映射到时间线上，切分已有阶段。
    """
    if not narration.attention_markers or not narration.narration:
        return phases

    total_chars = len(narration.narration)
    if total_chars == 0:
        return phases

    refined: list[AnimationPhase] = []

    for phase in phases:
        markers_in_range = []
        for marker in narration.attention_markers:
            marker_ms = int((marker.char_offset / total_chars) * duration_ms)
            if phase.start_ms <= marker_ms < phase.end_ms:
                markers_in_range.append((marker_ms, marker))

        if not markers_in_range:
            refined.append(phase)
            continue

        current_start = phase.start_ms
        for marker_ms, marker in sorted(markers_in_range, key=lambda x: x[0]):
            if marker_ms > current_start:
                refined.append(
                    AnimationPhase(
                        start_ms=current_start,
                        end_ms=marker_ms,
                        attention_mode=phase.attention_mode,
                        elements_to_show=phase.elements_to_show,
                        highlight_element=phase.highlight_element,
                        transition_type=phase.transition_type,
                    )
                )
            current_start = marker_ms

        refined.append(
            AnimationPhase(
                start_ms=current_start,
                end_ms=phase.end_ms,
                attention_mode=markers_in_range[-1][1].mode_switch_to,
                elements_to_show=phase.elements_to_show,
                highlight_element=phase.highlight_element,
                transition_type="none",
            )
        )

    return refined
