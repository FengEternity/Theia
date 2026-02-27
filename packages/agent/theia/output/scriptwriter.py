"""视频脚本生成：多 Agent 协作模式。

将 PaperSummary 通过 4 个协作 Agent 转换为带有动画编排的 VideoScript：
  Agent 1: Story Architect（故事架构师）— 全局叙事规划
  Agent 2: Scene Writer（场景编剧）— 旁白撰写 + 注意力标注
  Agent 3: Visual Director（视觉导演）— 基于规则的动画编排
  Agent 4: Pacing Reviewer（节奏审核员）— 时长/节奏/注意力检查

Agent 3 在 TTS 后由 pipeline 的 visual_director_node 再次调用（使用真实 word_timings）。
"""

from __future__ import annotations

import logging
import re as _re
from typing import Callable

from ..schemas import (
    PaperSummary,
    Scene,
    SceneNarration,
    SceneType,
    VideoMeta,
    VideoScript,
)

logger = logging.getLogger(__name__)

CHARS_PER_SECOND_ZH = 3.5
CHARS_PER_SECOND_EN = 12.0

VISUAL_PAUSE_SECONDS: dict[str, float] = {
    "formula": 5.0,
    "figure": 4.0,
    "method": 2.0,
    "result": 2.0,
}

MIN_SCENE_SECONDS: dict[str, float] = {
    "title": 5.0,
    "overview": 15.0,
    "method": 15.0,
    "formula": 15.0,
    "figure": 12.0,
    "result": 15.0,
    "conclusion": 10.0,
}


def generate_video_script(
    summary: PaperSummary,
    *,
    model: str = "gpt-4o-mini",
    fps: int = 30,
    language: str = "zh",
    width: int = 1920,
    height: int = 1080,
    narration_style: str = "default",
    theme: str = "academic",
    on_token: Callable[[str], None] | None = None,
    on_agent_step: Callable[[str, str], None] | None = None,
) -> VideoScript:
    """多 Agent 协作生成视频脚本。

    流程:
      1. Story Architect → StoryBlueprint
      2. Scene Writer → SceneNarrations（可能多轮，受 Pacing Reviewer 驱动）
      3. Visual Director → 初步 VisualChoreography（无 word_timings）
      4. Pacing Reviewer → 审核 → 通过或驳回

    TTS 和精细视觉编排在 pipeline 层面完成（visual_director_node）。

    参数:
        summary: 提取的论文信息。
        model: LiteLLM 模型标识符。
        fps: 视频帧率。
        language: 旁白语言。
        narration_style: 旁白风格。
        theme: 视频主题。
        on_token: 流式 token 回调（LLM 输出时触发）。
        on_agent_step: Agent 步骤回调 ``(agent_name, message)``，用于前端展示进度。

    返回:
        带有估算时长和初步动画编排的 :class:`VideoScript`。
    """
    from .pacing_reviewer import review_pacing
    from .scene_writer import write_scenes
    from .story_architect import plan_story
    from .visual_director import choreograph_scenes

    def _report(agent: str, msg: str) -> None:
        logger.info("[%s] %s", agent, msg)
        if on_agent_step:
            on_agent_step(agent, msg)

    _report("story_architect", "正在规划叙事结构...")

    # --- Agent 1: Story Architect ---
    blueprint = plan_story(summary, model=model, on_token=on_token)
    _report(
        "story_architect",
        f"叙事规划完成: {len(blueprint.scenes)} 个场景, 弧线: {blueprint.narrative_arc[:40]}",
    )

    # --- Agent 2 + 3 + 4: 编写-编排-审核循环 ---
    cps = CHARS_PER_SECOND_ZH if language == "zh" else CHARS_PER_SECOND_EN
    max_rounds = 2
    narrations = None
    choreographies = None
    review_feedback: str | None = None

    for round_num in range(max_rounds + 1):
        _report("scene_writer", f"正在撰写旁白 (第 {round_num + 1} 轮)...")

        narrations = write_scenes(
            blueprint,
            summary,
            model=model,
            narration_style=narration_style,
            on_token=on_token,
            review_feedback=review_feedback,
        )
        total_chars = sum(len(n.narration) for n in narrations)
        _report("scene_writer", f"旁白撰写完成: {len(narrations)} 个场景, 共 {total_chars} 字")

        lang_issues: list[tuple[int, float]] = []
        if language == "zh":
            lang_issues = _check_narration_language(narrations)
            if lang_issues:
                _report("scene_writer", f"检测到 {len(lang_issues)} 个场景文本含过多英文")

        scene_durations_ms = []
        for j, n in enumerate(narrations):
            p = blueprint.scenes[j] if j < len(blueprint.scenes) else None
            st = p.type if p else "overview"
            ns = max(len(n.narration) / cps, 3.0)
            vp = VISUAL_PAUSE_SECONDS.get(st, 0.0)
            mf = MIN_SCENE_SECONDS.get(st, 5.0)
            scene_durations_ms.append(int(max(ns + vp, mf) * 1000))

        _report("visual_director", "正在生成动画编排...")
        choreographies = choreograph_scenes(
            blueprint,
            narrations,
            [[] for _ in narrations],
            scene_durations_ms,
        )
        total_phases = sum(len(c.phases) for c in choreographies)
        _report("visual_director", f"动画编排完成: {total_phases} 个动画阶段")

        _report("pacing_reviewer", "正在审核节奏...")
        review = review_pacing(
            blueprint,
            narrations,
            choreographies,
            fps=fps,
            language=language,
        )

        if review.approved and not lang_issues:
            _report("pacing_reviewer", f"审核通过 (第 {round_num + 1} 轮)")
            break

        if review.approved and lang_issues:
            _report(
                "pacing_reviewer",
                f"节奏审核通过但检测到语言问题 (第 {round_num + 1} 轮)，触发重写",
            )

        if round_num >= max_rounds:
            _report(
                "pacing_reviewer",
                f"审核未通过但已达最大轮次 ({max_rounds}), 使用当前结果",
            )
            break

        feedback_parts = [f"- {issue}" for issue in review.issues]
        feedback_parts += [f"建议: {s}" for s in review.suggestions]

        if language == "zh":
            lang_issues = _check_narration_language(narrations)
            for idx, ratio in lang_issues:
                feedback_parts.append(
                    f"- ⚠️ 场景 {idx} 语言错误：中文比例仅 {ratio:.0%}。"
                    f"narration 和 data 中的 problem/contributions/summary/steps/"
                    f"explanation/description/findings/conclusion 字段"
                    f"必须全部使用中文！请重写！"
                )

        review_feedback = "\n".join(feedback_parts)

        _report(
            "pacing_reviewer",
            f"审核未通过 (第 {round_num + 1} 轮): {'; '.join(review.issues[:2])}",
        )

    # --- 组装 VideoScript ---
    scenes: list[Scene] = []
    for i, narr in enumerate(narrations):
        plan = blueprint.scenes[i] if i < len(blueprint.scenes) else None
        scene_type_str = plan.type if plan else "overview"

        narration_seconds = max(len(narr.narration) / cps, 3.0)
        visual_pause = VISUAL_PAUSE_SECONDS.get(scene_type_str, 0.0)
        min_floor = MIN_SCENE_SECONDS.get(scene_type_str, 5.0)
        est_seconds = max(narration_seconds + visual_pause, min_floor)
        duration_frames = int(est_seconds * fps)

        choreo_phases = []
        if choreographies and i < len(choreographies):
            choreo_phases = choreographies[i].phases

        scenes.append(
            Scene(
                type=SceneType(scene_type_str),
                duration_in_frames=duration_frames,
                narration=narr.narration,
                audio_file=None,
                data=narr.data,
                choreography=choreo_phases,
            )
        )

    script = VideoScript(
        meta=VideoMeta(fps=fps, width=width, height=height, theme=theme),
        scenes=scenes,
    )

    logger.info(
        "脚本生成完成: %d 个场景, 约 %.0f 秒",
        len(scenes),
        script.total_duration_seconds,
    )
    return script


_CJK_RE = _re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff"
    r"\U00020000-\U0002a6df\U0002a700-\U0002ebef]"
)

_MIN_CHINESE_RATIO = 0.3


_DATA_FIELDS_MUST_BE_CHINESE = {
    "problem", "contributions", "summary", "steps",
    "explanation", "description", "findings", "conclusion",
}


def _chinese_ratio_of(text: str) -> float:
    non_ws = _re.sub(r"\s+", "", text)
    if not non_ws:
        return 1.0
    cjk = len(_CJK_RE.findall(non_ws))
    return cjk / len(non_ws)


def _check_narration_language(
    narrations: list[SceneNarration],
) -> list[tuple[int, float]]:
    """返回中文比例低于阈值的 (scene_index, ratio) 列表。包括旁白和 data 字段。"""
    issues: list[tuple[int, float]] = []
    for i, narr in enumerate(narrations):
        text = narr.narration
        if text and len(text) >= 10:
            ratio = _chinese_ratio_of(text)
            if ratio < _MIN_CHINESE_RATIO:
                logger.warning(
                    "场景 %d 旁白中文比例 %.0f%%: %s...",
                    i, ratio * 100, text[:60],
                )
                issues.append((i, ratio))

        for key, val in narr.data.items():
            if key not in _DATA_FIELDS_MUST_BE_CHINESE:
                continue
            texts_to_check: list[str] = []
            if isinstance(val, str) and len(val) >= 10:
                texts_to_check.append(val)
            elif isinstance(val, list):
                texts_to_check.extend(
                    item for item in val if isinstance(item, str) and len(item) >= 10
                )
            for t in texts_to_check:
                r = _chinese_ratio_of(t)
                if r < _MIN_CHINESE_RATIO:
                    logger.warning(
                        "场景 %d data.%s 中文比例 %.0f%%: %s...",
                        i, key, r * 100, t[:60],
                    )
                    issues.append((i, r))
                    break
    return issues
