"""多模态 LLM 图表分析。

使用 GPT-4o 的 vision 能力分析论文中的图表，
生成结构化描述、分类和重要性评分。
"""

from __future__ import annotations

import base64
import io
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .llm_client import robust_completion, strip_json_fences
from .schemas import Figure, PaperOverview

logger = logging.getLogger(__name__)

FIGURE_ANALYSIS_PROMPT = """\
你是一位论文图表分析专家。给定一张论文中的图片及其上下文，请分析并返回结构化描述。

论文的核心思想是：{core_idea}

图片在论文中的上下文：
{context}

图片原始标题：{caption}

请以有效的 JSON 响应（不加 Markdown 围栏）：

{{
  "description": "2-3 句话描述图片展示的具体内容和关键信息",
  "figure_type": "architecture|comparison|result|visualization|table|other",
  "importance": 1-5 的整数,
  "suggested_narration_points": ["讲解此图时应该提到的要点1", "要点2"]
}}

figure_type 说明：
- architecture: 模型架构图、系统流程图、方法框图
- comparison: 对比图、柱状图、折线对比
- result: 实验结果图、热力图、混淆矩阵
- visualization: 可视化示例、生成样本、注意力图
- table: 表格截图
- other: 其他类型

importance 评分标准：
- 5: 论文核心架构图或最关键的实验对比图
- 4: 重要的方法细节图或显著的实验结果图
- 3: 辅助说明的图表
- 2: 补充性的可视化或小规模对比
- 1: 装饰性或不太重要的图
"""

_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def analyze_figures(
    figures: list[dict],
    images_dir: Path,
    paper_overview: PaperOverview,
    *,
    model: str = "gpt-4o",
    max_figures: int = 8,
    api_key: str | None = None,
    api_base: str | None = None,
) -> list[Figure]:
    """使用多模态 LLM 分析论文图表。

    参数:
        figures: ``extract_figures_from_markdown`` 返回的原始图片列表。
        images_dir: 图片文件所在目录。
        paper_overview: Pass 1 的快速扫描结果。
        model: 支持 vision 的 LiteLLM 模型标识符。
        max_figures: 最多分析的图片数量。
        api_key: LLM API 密钥。
        api_base: LLM API 基础 URL。

    返回:
        按重要性排序的 :class:`Figure` 列表。
    """
    if not figures:
        return []

    resolved = _resolve_figure_paths(figures, images_dir)
    if not resolved:
        logger.info("未找到可读取的图片文件")
        return _fallback_figures(figures[:max_figures])

    candidates = sorted(resolved, key=lambda x: _presort_score(x["fig"]), reverse=True)
    candidates = candidates[:max_figures]

    def _process_one(item: dict) -> Figure:
        fig_data = item["fig"]
        img_path: Path = item["path"]
        try:
            result = _analyze_single_figure(
                img_path,
                caption=fig_data.get("caption", ""),
                context=fig_data.get("context", ""),
                core_idea=paper_overview.core_idea,
                model=model,
                api_key=api_key,
                api_base=api_base,
            )
            return Figure(
                path=fig_data["path"],
                caption=fig_data.get("caption", ""),
                description=result.get("description", ""),
                importance=min(max(int(result.get("importance", 3)), 1), 5),
                figure_type=result.get("figure_type", "other"),
            )
        except Exception as exc:
            logger.warning("分析图片 %s 失败: %s", img_path.name, exc)
            return Figure(
                path=fig_data["path"],
                caption=fig_data.get("caption", ""),
                importance=2,
            )

    workers = min(2, len(candidates))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        analyzed = list(executor.map(_process_one, candidates))

    analyzed.sort(key=lambda f: f.importance, reverse=True)
    logger.info("图表分析完成: %d/%d 张 (并行 workers=%d)", len(analyzed), len(candidates), workers)
    return analyzed


def reanalyze_single_figure(
    figure_path: str,
    images_dir: Path,
    core_idea: str,
    *,
    caption: str = "",
    model: str = "gpt-4o",
    api_key: str | None = None,
    api_base: str | None = None,
) -> Figure:
    """重新分析单张图片并返回更新后的 Figure。

    用于前端手动触发对单张图片的重新分析。
    """
    name = Path(figure_path).name
    candidates = [
        images_dir / name,
        images_dir / figure_path,
    ]
    img_path = next((p for p in candidates if p.is_file()), None)
    if not img_path:
        raise FileNotFoundError(f"图片文件未找到: {figure_path} (搜索目录: {images_dir})")

    result = _analyze_single_figure(
        img_path,
        caption=caption,
        context="",
        core_idea=core_idea,
        model=model,
        api_key=api_key,
        api_base=api_base,
    )
    return Figure(
        path=figure_path,
        caption=caption,
        description=result.get("description", ""),
        importance=min(max(int(result.get("importance", 3)), 1), 5),
        figure_type=result.get("figure_type", "other"),
    )


def _resolve_figure_paths(
    figures: list[dict],
    images_dir: Path,
) -> list[dict]:
    """将图片相对路径解析为实际文件路径。"""
    resolved: list[dict] = []
    for fig in figures:
        raw_path = fig.get("path", "")
        if not raw_path:
            continue

        name = Path(raw_path).name
        candidates = [
            images_dir / name,
            images_dir / raw_path,
            images_dir.parent / raw_path,
        ]

        for cand in candidates:
            if cand.exists() and cand.suffix.lower() in _SUPPORTED_EXTENSIONS:
                resolved.append({"fig": fig, "path": cand})
                break

    return resolved


def _presort_score(fig: dict) -> float:
    """基于上下文关键词的预排序评分，用于在 LLM 分析前筛选。"""
    context = fig.get("context", "").lower()
    score = 0.0

    high_value = [
        "architecture",
        "framework",
        "overview",
        "model",
        "pipeline",
        "comparison",
        "ablation",
        "架构",
        "框架",
        "对比",
        "消融",
    ]
    for kw in high_value:
        if kw in context:
            score += 2.0

    medium_value = ["result", "performance", "accuracy", "figure 1", "fig. 1", "结果", "性能", "准确率", "图1", "图 1"]
    for kw in medium_value:
        if kw in context:
            score += 1.0

    if fig.get("caption"):
        score += 0.5

    return score


_MAX_DIMENSION = 1024
_JPEG_QUALITY = 85


def _compress_image(img_bytes: bytes, suffix: str) -> tuple[bytes, str]:
    """将大尺寸图片缩放至 _MAX_DIMENSION 并压缩为 JPEG。"""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(img_bytes))
        w, h = img.size
        if w <= _MAX_DIMENSION and h <= _MAX_DIMENSION:
            return img_bytes, _MIME_MAP.get(suffix, "image/png")
        ratio = min(_MAX_DIMENSION / w, _MAX_DIMENSION / h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_QUALITY)
        return buf.getvalue(), "image/jpeg"
    except ImportError:
        return img_bytes, _MIME_MAP.get(suffix, "image/png")


def _analyze_single_figure(
    img_path: Path,
    *,
    caption: str,
    context: str,
    core_idea: str,
    model: str,
    api_key: str | None = None,
    api_base: str | None = None,
) -> dict:
    """用多模态 LLM 分析单张图片。"""
    raw_bytes = img_path.read_bytes()
    suffix = img_path.suffix.lower()
    img_bytes, mime = _compress_image(raw_bytes, suffix)
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt = FIGURE_ANALYSIS_PROMPT.format(
        core_idea=core_idea or "（未知）",
        context=context[:500] if context else "（无上下文）",
        caption=caption or "（无标题）",
    )

    kwargs: dict = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{img_b64}"},
                    },
                ],
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.1,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    response = robust_completion(kwargs)
    raw = response.choices[0].message.content.strip()

    raw = strip_json_fences(raw)

    import json

    return json.loads(raw)


def _fallback_figures(figures: list[dict]) -> list[Figure]:
    """当图片文件不可读时，返回仅含路径和标题的基础 Figure 列表。"""
    return [
        Figure(
            path=fig.get("path", ""),
            caption=fig.get("caption", ""),
            importance=2,
        )
        for fig in figures
        if fig.get("path")
    ]
