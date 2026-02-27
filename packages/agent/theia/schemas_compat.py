"""向后兼容工具：从已有 VideoScript 反推 StoryBlueprint。

用于视觉导演节点在 TTS 之后重建蓝图上下文。
"""

from __future__ import annotations

from .schemas import ScenePlan, StoryBlueprint, VideoScript


def _rebuild_blueprint_from_script(script: VideoScript) -> StoryBlueprint:
    """从已有的 VideoScript 反推出一个近似的 StoryBlueprint。"""
    scenes: list[ScenePlan] = []
    fps = script.meta.fps

    for s in script.scenes:
        duration_s = s.duration_in_frames / fps
        scene_type = s.type.value

        scenes.append(
            ScenePlan(
                type=scene_type,
                target_duration_range=(max(3.0, duration_s * 0.8), duration_s * 1.2),
                narrative_role="build_up",
                attention_strategy="synced",
                narration_word_range=(
                    max(10, len(s.narration) - 20),
                    len(s.narration) + 20,
                ),
            )
        )

    total_s = script.total_duration_seconds
    return StoryBlueprint(
        narrative_arc="(从已有脚本反推)",
        scenes=scenes,
        total_target_duration=(total_s * 0.8, total_s * 1.2),
    )
