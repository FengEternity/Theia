"""场景编剧 (Scene Writer): 为每个场景撰写旁白和数据。

Agent 2: 根据故事蓝图和论文摘要，为每个场景生成旁白文本、视觉数据和注意力标注。
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Callable

from ..llm.client import robust_completion
from ..prompts.scene_writer import build_scene_writer_prompt
from ..schemas import AttentionMarker, PaperSummary, SceneNarration, StoryBlueprint

logger = logging.getLogger(__name__)

_CJK_RANGES = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff"
    r"\U00020000-\U0002a6df\U0002a700-\U0002ebef]"
)


def _chinese_ratio(text: str) -> float:
    """返回文本中 CJK 字符占非空白字符的比例。"""
    non_ws = re.sub(r"\s+", "", text)
    if not non_ws:
        return 0.0
    cjk_count = len(_CJK_RANGES.findall(non_ws))
    return cjk_count / len(non_ws)


def write_scenes(
    blueprint: StoryBlueprint,
    summary: PaperSummary,
    *,
    model: str = "kimi-k2-0905-preview",
    api_key: str | None = None,
    api_base: str | None = None,
    narration_style: str = "default",
    on_token: Callable[[str], None] | None = None,
    review_feedback: str | None = None,
) -> list[SceneNarration]:
    """根据故事蓝图为所有场景撰写旁白。

    参数:
        blueprint: 故事架构师输出的叙事蓝图。
        summary: 提取的论文信息。
        model: LiteLLM 模型标识符。
        api_key: API 密钥（可选，覆盖环境变量）。
        api_base: API base URL（可选，覆盖环境变量）。
        narration_style: 旁白风格。
        on_token: 流式 token 回调。
        review_feedback: 上一轮审核的反馈（若有）。

    返回:
        每个场景的旁白和标注列表。
    """
    system_prompt = build_scene_writer_prompt(narration_style)
    user_content = _build_user_content(blueprint, summary)

    if review_feedback:
        user_content += f"\n\n### ⚠️ 上一轮审核反馈（必须修正以下问题）：\n{review_feedback}"

    logger.info(
        "场景编剧: 正在撰写 %d 个场景旁白 model=%s style=%s",
        len(blueprint.scenes),
        model,
        narration_style,
    )
    logger.info(
        "场景编剧: 输入 %d 个场景, model=%s, api_base=%s",
        len(blueprint.scenes),
        model,
        api_base or "(默认)",
    )

    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 8192,
        "temperature": 0.5,
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
    raw_scenes = data.get("scenes", [])

    narrations: list[SceneNarration] = []
    for i, s in enumerate(raw_scenes):
        markers = []
        for m in s.get("attention_markers", []):
            markers.append(
                AttentionMarker(
                    char_offset=m.get("char_offset", 0),
                    mode_switch_to=m.get("mode_switch_to", "synced"),
                    visual_hint=m.get("visual_hint", ""),
                )
            )

        narrations.append(
            SceneNarration(
                scene_index=s.get("scene_index", i),
                narration=s.get("narration", ""),
                data=s.get("data", {}),
                attention_markers=markers,
                pause_points=s.get("pause_points", []),
            )
        )

    _validate_chinese_narrations(narrations)

    for i, narr in enumerate(narrations):
        logger.debug(
            "  场景 %d: %d 字, data keys=%s",
            i,
            len(narr.narration),
            list(narr.data.keys()),
        )

    logger.info(
        "场景编剧完成: %d 个场景, 总字数 %d",
        len(narrations),
        sum(len(n.narration) for n in narrations),
    )
    return narrations


MIN_CHINESE_RATIO = 0.3


def _validate_chinese_narrations(narrations: list[SceneNarration]) -> None:
    """检测并记录旁白中英文比例过高的场景。"""
    for i, narr in enumerate(narrations):
        if not narr.narration:
            continue
        ratio = _chinese_ratio(narr.narration)
        if ratio < MIN_CHINESE_RATIO:
            logger.warning(
                "场景 %d 旁白中文比例仅 %.0f%%，可能未遵循中文要求: %s...",
                i,
                ratio * 100,
                narr.narration[:60],
            )


def _build_user_content(blueprint: StoryBlueprint, summary: PaperSummary) -> str:
    """组装场景编剧的 user prompt。"""
    parts = []

    parts.append("### 故事蓝图：")
    parts.append(f"叙事弧线: {blueprint.narrative_arc}")
    parts.append(f"关键时刻: {', '.join(blueprint.key_moments)}")
    parts.append("")

    parts.append("### 场景编排（请严格按此顺序生成）：")
    for i, scene in enumerate(blueprint.scenes):
        min_w, max_w = scene.narration_word_range
        min_d, max_d = scene.target_duration_range
        parts.append(
            f"  {i}. [{scene.type}] 角色={scene.narrative_role}, "
            f"字数={min_w}-{max_w}, 时长={min_d:.0f}-{max_d:.0f}s, "
            f"注意力={scene.attention_strategy}"
            f"{' ★关键时刻' if scene.key_moment else ''}"
        )
    parts.append("")

    parts.append("### 论文摘要：")
    parts.append(summary.model_dump_json(indent=2))

    if summary.figures:
        parts.append("\n### 可用图表列表（figure 场景请从中选择 figure_index）：")
        for idx, fig in enumerate(summary.figures):
            label = fig.caption or f"图{idx}"
            must = " ★必选" if fig.importance == 5 else ""
            parts.append(
                f"  [{idx}] type={fig.figure_type}, importance={fig.importance}{must}"
                f" | caption: {label}"
                + (f" | description: {fig.description[:80]}" if fig.description else "")
            )

    return "\n".join(parts)
