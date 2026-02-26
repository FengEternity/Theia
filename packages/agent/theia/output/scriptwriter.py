"""视频脚本生成：将论文摘要转化为旁白和场景。

将 PaperSummary 转换为带有逐场景旁白文本和视觉元素的 VideoScript。
默认使用更轻量/便宜的模型，因为旁白生成是较简单的创意任务。
支持多风格旁白模板：default（默认口语化）、academic（学术严谨）、story（故事叙述）。
"""

from __future__ import annotations

import json
import logging
from typing import Callable

from ..llm.client import robust_completion
from ..prompts.scriptwriter import NARRATION_STYLE_OVERRIDES, SCRIPT_SYSTEM_PROMPT
from ..schemas import (
    PaperSummary,
    Scene,
    SceneType,
    VideoMeta,
    VideoScript,
)

logger = logging.getLogger(__name__)

CHARS_PER_SECOND_ZH = 3.5
CHARS_PER_SECOND_EN = 12.0


def _plan_scenes(summary: PaperSummary) -> list[str]:
    """根据论文内容丰富度动态规划场景列表。

    丰富度因子决定场景数量:
    - 方法步骤多 → 可拆分多个 method 场景
    - 公式多 → 可多个 formula 场景
    - 图片多 → 更多 figure 场景
    - baselines 多 → 更多 result 场景
    """
    scenes = ["title", "overview"]

    n_steps = len(summary.method.key_steps)
    if n_steps >= 6:
        scenes.extend(["method", "method"])
    else:
        scenes.append("method")

    n_formulas = len(summary.method.formulas)
    if n_formulas >= 3:
        scenes.extend(["formula", "formula"])
    elif n_formulas >= 1:
        scenes.append("formula")

    has_figures = bool(summary.figures)
    if has_figures:
        must_include = [f for f in summary.figures if f.importance == 5]
        important = [f for f in summary.figures if f.importance >= 3]
        n_must = len(must_include)
        n_important = len(important) if important else len(summary.figures)
        n_figure_scenes = max(n_must, max(1, min(n_important, 4)))
        n_figure_scenes = min(n_figure_scenes, 6)
        for _ in range(n_figure_scenes):
            scenes.append("figure")

    scenes.append("result")

    n_baselines = len(summary.results.baselines)
    n_datasets = len(summary.results.datasets)
    n_metrics = len(summary.results.metrics)
    if n_baselines >= 4 or n_datasets >= 3 or n_metrics >= 6:
        scenes.append("result")

    scenes.append("conclusion")

    logger.info(
        "动态场景规划: %s (steps=%d, formulas=%d, figures=%d, baselines=%d)",
        " → ".join(scenes),
        n_steps,
        n_formulas,
        len(summary.figures),
        n_baselines,
    )
    return scenes


def _build_scene_plan_instruction(plan: list[str]) -> str:
    """将动态场景规划转为 prompt 补充说明。"""
    if set(plan) == {"title", "overview", "method", "formula", "figure", "result", "conclusion"}:
        return ""

    lines = ["### 本次场景编排（根据论文内容动态决定）："]
    lines.append(f"请严格按以下顺序生成 {len(plan)} 个场景：")
    lines.append(" → ".join(plan))
    lines.append("")

    plan_set = set(plan)
    if "formula" not in plan_set:
        lines.append(
            "- 本论文无关键公式，跳过 formula 场景。如果方法中有公式相关内容，请在 method 场景旁白中简要提及。"
        )
    if "figure" not in plan_set:
        lines.append("- 本论文未提取到图表，跳过 figure 场景。")
    if plan.count("figure") > 1:
        lines.append("- 本论文图表丰富，安排了多个 figure 场景，请为每个 figure 场景选择不同的图表。")
    if plan.count("result") > 1:
        lines.append("- 本论文实验数据丰富，安排了多个 result 场景，请按数据集分别展示。")

    return "\n".join(lines)


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
) -> VideoScript:
    """将论文摘要转换为带有时间标注的视频脚本。

    参数:
        summary: 提取的论文信息。
        model: LiteLLM 模型标识符。
        fps: 视频帧率。
        language: 主要语言提示（``"zh"`` 或 ``"en"``）。
        narration_style: 旁白风格：``"default"``（口语化）、``"academic"``（学术）、``"story"``（故事）。

    返回:
        带有估算时长的 :class:`VideoScript`。
    """
    summary_json = summary.model_dump_json(indent=2)
    scene_plan = _plan_scenes(summary)
    plan_instruction = _build_scene_plan_instruction(scene_plan)

    logger.info(
        "正在生成视频脚本 model=%s, scenes=%d, style=%s, theme=%s",
        model,
        len(scene_plan),
        narration_style,
        theme,
    )

    style_block = NARRATION_STYLE_OVERRIDES.get(narration_style, NARRATION_STYLE_OVERRIDES["default"])
    system_prompt = SCRIPT_SYSTEM_PROMPT.replace(
        NARRATION_STYLE_OVERRIDES["default"],
        style_block,
    )

    figure_priority_note = ""
    if summary.figures:
        must_include = [f for f in summary.figures if f.importance == 5]
        if must_include:
            names = [f.caption or f.path for f in must_include]
            figure_priority_note = (
                "\n\n### 用户标记的必选图表（importance=5，必须在 figure 场景中使用）：\n"
                + "\n".join(f"- {n}" for n in names)
            )

    user_content = f"论文摘要：\n\n{summary_json}"
    if plan_instruction:
        user_content = f"{plan_instruction}\n\n{user_content}"
    if figure_priority_note:
        user_content = f"{figure_priority_note}\n\n{user_content}"

    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 4096,
        "temperature": 0.5,
        "response_format": {"type": "json_object"},
    }

    response = robust_completion(kwargs, on_token=on_token)

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw[raw.index("\n") + 1 :]
    if raw.endswith("```"):
        raw = raw[:-3]

    data = json.loads(raw)
    raw_scenes = data.get("scenes", [])

    cps = CHARS_PER_SECOND_ZH if language == "zh" else CHARS_PER_SECOND_EN

    scenes: list[Scene] = []
    for s in raw_scenes:
        narration = s.get("narration", "")
        est_seconds = max(len(narration) / cps, 3.0)
        duration_frames = int(est_seconds * fps)
        duration_frames = max(duration_frames, fps * 3)

        scenes.append(
            Scene(
                type=SceneType(s["type"]),
                duration_in_frames=duration_frames,
                narration=narration,
                audio_file=None,
                data=s.get("data", {}),
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
