"""多模态 LLM 图表分析。

使用 GPT-4o 的 vision 能力分析论文中的图表，
生成结构化描述、分类和重要性评分。
"""

from __future__ import annotations

import base64
import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from ..llm.client import robust_completion, strip_json_fences
from ..schemas import Figure, PaperOverview

logger = logging.getLogger(__name__)

_TEXT_ONLY_MODEL_PATTERNS = [
    "moonshot-v1",
    "kimi-k2-0905",
    "kimi-k2-0711",
    "kimi-k2-turbo",
    "kimi-k2-thinking",
    "deepseek-chat",
    "deepseek-coder",
    "qwen-turbo",
    "qwen-plus",
    "qwen-max",
    "glm-3",
    "glm-4",
    "yi-",
]


_KNOWN_VISION_MODELS = [
    "kimi-k2.5",
    "gpt-4o",
    "gpt-4-vision",
    "gpt-5",
    "claude-3",
    "gemini",
]


def _is_vision_model(model: str) -> bool:
    """启发式判断模型是否支持视觉输入。

    已知支持视觉的模型: kimi-k2.5, gpt-4o, claude-3, gemini 等。
    已知不支持的: moonshot-v1, deepseek-chat, qwen-turbo 等纯文本模型。
    名称中含 vision/vl 或在白名单中的优先视为视觉模型。
    """
    model_lower = model.lower().replace("openai/", "").replace("anthropic/", "")

    if any(kw in model_lower for kw in ("vision", "-vl-", "-vl", "vl-")):
        return True

    if any(known in model_lower for known in _KNOWN_VISION_MODELS):
        return True

    for pattern in _TEXT_ONLY_MODEL_PATTERNS:
        if pattern in model_lower:
            return False
    return True


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

RESULT_TABLE_EXTRACTION_PROMPT = """\
你是一位数据提取专家。给定一张包含实验结果或对比数据的论文图表，请提取其中的结构化数据。

图片类型：{figure_type}
图片描述：{description}
图片标题：{caption}

请以有效的 JSON 响应（不加 Markdown 围栏）：

{{
  "has_numerical_data": true,
  "table_data": {{
    "column_headers": ["方法名", "指标1", "指标2"],
    "rows": [
      {{"method": "方法A", "values": {{"指标1": 85.3, "指标2": 92.1}}, "is_proposed": false}},
      {{"method": "本文方法", "values": {{"指标1": 91.2, "指标2": 95.8}}, "is_proposed": true}}
    ],
    "datasets": ["数据集名称"],
    "best_result_summary": "简要对比结论"
  }},
  "chart_data": {{
    "chart_type": "bar|line|scatter|heatmap|other",
    "data_points": [
      {{"label": "系列名", "values": [{{"x": "类别", "y": 数字}}]}}
    ],
    "key_comparison": "关键对比结论"
  }}
}}

指南：
- has_numerical_data: 图中是否包含可提取的数值
- 如果是表格，填写 table_data；如果是图表，填写 chart_data；可以两者都填
- 数值必须是图中真实可见的数字，不要编造
- is_proposed 标记哪个是本文提出的方法
- 图片模糊无法准确读数时，对应值填 null
- 没有数值数据时 has_numerical_data 设为 false，其他字段留空对象
"""

_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/png",
}


def analyze_figures(
    figures: list[dict],
    images_dir: Path,
    paper_overview: PaperOverview,
    *,
    model: str = "kimi-k2.5",
    max_figures: int = 8,
    api_key: str | None = None,
    api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
) -> tuple[list[Figure], list[dict]]:
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
        (按重要性排序的 Figure 列表, 结果类图表的数值提取数据列表)
    """
    if not figures:
        return [], []

    logger.info("图表分析: 共 %d 张图, 将分析最多 %d 张, model=%s", len(figures), max_figures, model)

    if not _is_vision_model(model):
        logger.warning(
            "图表分析跳过：模型 %s 不支持图片输入。请设置 THEIA_FIGURE_MODEL 为支持视觉的模型（如 kimi-k2.5）",
            model,
        )
        return _fallback_figures(figures[:max_figures]), []

    resolved = _resolve_figure_paths(figures, images_dir)
    if not resolved:
        logger.info("未找到可读取的图片文件")
        return _fallback_figures(figures[:max_figures]), []

    candidates = sorted(resolved, key=lambda x: _presort_score(x["fig"]), reverse=True)
    if len(candidates) > max_figures:
        logger.info(
            "有效图片 %d 张，取评分最高的 %d 张进行分析",
            len(candidates), max_figures,
        )
    candidates = candidates[:max_figures]

    def _process_one(args: tuple[int, dict]) -> Figure:
        idx, item = args
        fig_data = item["fig"]
        figure_name = Path(fig_data.get("path", "unknown")).name
        logger.info("分析图表 %d/%d: %s", idx + 1, len(candidates), figure_name)
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
                on_token=on_token,
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
        analyzed = list(executor.map(_process_one, enumerate(candidates)))

    analyzed.sort(key=lambda f: f.importance, reverse=True)
    importance_counts: dict[int, int] = {}
    for f in analyzed:
        importance_counts[f.importance] = importance_counts.get(f.importance, 0) + 1
    dist_str = ", ".join(f"importance {k}: {importance_counts[k]}" for k in sorted(importance_counts, reverse=True))
    logger.info("图表分析完成: %d/%d 张 (并行 workers=%d), 重要性分布: %s", len(analyzed), len(candidates), workers, dist_str)

    result_table_data: list[dict] = []
    result_figures = [
        (fig, item["path"])
        for fig, item in zip(analyzed, candidates)
        if fig.figure_type in ("result", "table", "comparison") and fig.importance >= 3
    ]

    if result_figures:
        logger.info("Step 3b: %d 张结果类图表需要提取数值数据", len(result_figures))
        for fig, img_path in result_figures:
            try:
                table_data = _extract_result_data(
                    img_path,
                    fig,
                    model=model,
                    api_key=api_key,
                    api_base=api_base,
                    on_token=on_token,
                )
                if table_data.get("has_numerical_data"):
                    result_table_data.append({
                        "figure_path": fig.path,
                        "figure_type": fig.figure_type,
                        "caption": fig.caption,
                        **table_data,
                    })
                    logger.info("Step 3b: 从 %s 提取到结构化数据", Path(fig.path).name)
            except Exception as exc:
                logger.warning("Step 3b: 结果图表数据提取失败 %s: %s", fig.path, exc)

    return analyzed, result_table_data


def reanalyze_single_figure(
    figure_path: str,
    images_dir: Path,
    core_idea: str,
    *,
    caption: str = "",
    model: str = "kimi-k2.5",
    api_key: str | None = None,
    api_base: str | None = None,
) -> Figure:
    """重新分析单张图片并返回更新后的 Figure。

    用于前端手动触发对单张图片的重新分析。
    """
    if not _is_vision_model(model):
        raise ValueError(
            f"模型 {model} 不支持图片输入。请设置 THEIA_FIGURE_MODEL 为支持视觉的模型（如 kimi-k2.5）"
        )

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
    """将图片相对路径解析为实际文件路径，过滤无效图片。"""
    resolved: list[dict] = []
    skipped: list[str] = []
    not_found: list[str] = []
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

        found = False
        for cand in candidates:
            if cand.exists() and cand.suffix.lower() in _SUPPORTED_EXTENSIONS:
                found = True
                if _validate_image(cand.read_bytes()):
                    resolved.append({"fig": fig, "path": cand})
                else:
                    skipped.append(cand.name)
                break
        if not found:
            not_found.append(name)

    total = len(figures)
    valid = len(resolved)
    if skipped:
        logger.info(
            "图片筛选: %d/%d 有效, %d 无效被跳过 (%s)",
            valid, total, len(skipped), ", ".join(skipped[:5]),
        )
    elif total != valid:
        logger.info("图片筛选: %d/%d 有效", valid, total)
    if not_found:
        logger.debug("未找到 %d 张图片: %s", len(not_found), ", ".join(not_found[:5]))

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
    """将大尺寸图片缩放至 _MAX_DIMENSION 并压缩为 JPEG。

    无法识别的图片格式（如 SVG）直接返回原始字节。
    """
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
    except Exception:
        return img_bytes, _MIME_MAP.get(suffix, "image/png")


_MIN_DIMENSION = 80
_MIN_FILE_SIZE = 2048


def _is_svg(img_bytes: bytes) -> bool:
    """检测字节是否为 SVG 格式。"""
    header = img_bytes[:200].lstrip()
    return header[:4] == b"<svg" or header[:5] == b"<?xml" and b"<svg" in img_bytes[:500]


def _svg_to_png(img_bytes: bytes, *, scale_width: int | None = None) -> bytes | None:
    """将 SVG 转为 PNG。需要 cairosvg 库。

    参数:
        scale_width: 输出宽度。None 表示按 SVG 原始尺寸渲染。
    """
    try:
        import cairosvg

        kwargs: dict = {"bytestring": img_bytes}
        if scale_width is not None:
            kwargs["output_width"] = scale_width
        return cairosvg.svg2png(**kwargs)
    except ImportError:
        logger.debug("cairosvg 未安装，无法转换 SVG")
        return None
    except Exception as exc:
        logger.debug("SVG 转 PNG 失败: %s", exc)
        return None


def _validate_image(img_bytes: bytes) -> bool:
    """检测字节是否为有价值的图片（包括 SVG）。

    排除条件:
    - 纯 HTML 页面
    - 太小的文件（< 2KB，通常是 1x1 透明像素或小图标）
    - 尺寸太小的光栅图片（< 80x80，通常是头像、emoji、装饰图标）
    """
    header = img_bytes[:200].lstrip()
    if header[:14] == b"<!DOCTYPE html" or header[:5] == b"<html":
        return False

    if _is_svg(img_bytes):
        png_bytes = _svg_to_png(img_bytes)
        if png_bytes is None:
            return False
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(png_bytes))
            w, h = img.size
            if w < _MIN_DIMENSION or h < _MIN_DIMENSION:
                return False
        except Exception:
            return False
        return True

    if len(img_bytes) < _MIN_FILE_SIZE:
        return False

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(img_bytes))
        img.verify()
        img = Image.open(io.BytesIO(img_bytes))
        w, h = img.size
        if w < _MIN_DIMENSION or h < _MIN_DIMENSION:
            return False
        return True
    except Exception:
        return False


def _analyze_single_figure(
    img_path: Path,
    *,
    caption: str,
    context: str,
    core_idea: str,
    model: str,
    api_key: str | None = None,
    api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
) -> dict:
    """用多模态 LLM 分析单张图片（支持 SVG 自动转换）。"""
    raw_bytes = img_path.read_bytes()
    if not _validate_image(raw_bytes):
        raise ValueError(f"无法识别的图片格式: {img_path.name}")

    if _is_svg(raw_bytes):
        png_bytes = _svg_to_png(raw_bytes, scale_width=_MAX_DIMENSION)
        if png_bytes is None:
            raise ValueError(f"SVG 转换失败（需安装 cairosvg）: {img_path.name}")
        raw_bytes = png_bytes
        suffix = ".png"
    else:
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
        "max_tokens": 2048,
        "temperature": 0.1,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    try:
        response = robust_completion(kwargs, on_token=on_token)
    except Exception as exc:
        msg = str(exc).lower()
        if "image input not supported" in msg or "does not support image" in msg:
            raise ValueError(f"模型 {model} 不支持图片输入，请更换为视觉模型") from exc
        raise

    raw = response.choices[0].message.content.strip()
    raw = strip_json_fences(raw)
    return json.loads(raw)


def _extract_result_data(
    img_path: Path,
    figure: Figure,
    *,
    model: str,
    api_key: str | None = None,
    api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
) -> dict:
    """从结果类图表中提取结构化数值数据（Step 3b）。"""
    raw_bytes = img_path.read_bytes()
    if _is_svg(raw_bytes):
        png_bytes = _svg_to_png(raw_bytes, scale_width=_MAX_DIMENSION)
        if png_bytes is None:
            return {"has_numerical_data": False}
        raw_bytes = png_bytes
        suffix = ".png"
    else:
        suffix = img_path.suffix.lower()

    img_bytes, mime = _compress_image(raw_bytes, suffix)
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt = RESULT_TABLE_EXTRACTION_PROMPT.format(
        figure_type=figure.figure_type,
        description=figure.description[:500] if figure.description else "（无描述）",
        caption=figure.caption or "（无标题）",
    )

    kwargs: dict = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                ],
            }
        ],
        "max_tokens": 2048,
        "temperature": 0.1,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    response = robust_completion(kwargs, on_token=on_token)
    raw = response.choices[0].message.content.strip()
    raw = strip_json_fences(raw)
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
