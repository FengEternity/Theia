"""三遍渐进式提取（三遍阅读法）核心逻辑。"""

from __future__ import annotations

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from pydantic import ValidationError

from .sections import _pass2_chunked_extract
from .synthesize import _sections_from_content_list, _synthesize
from .utils import _estimate_tokens
from ..quality.evaluator import ExtractionEvaluator
from ..llm.client import extract_json_from_response, robust_completion
from ..llm.config import (
    budget_truncate,
    get_section_headings,
    split_sections_with_labels,
)
from ..prompts.extraction_pass1 import PASS1_PROMPT
from ..prompts.extraction_pass2 import PASS2_PROMPT
from ..schemas import PaperOverview, PaperSummary

logger = logging.getLogger(__name__)


def _extract_multi_pass(
    markdown_content: str,
    *,
    model: str,
    scan_model: str,
    figure_model: str,
    images_dir: Path | None,
    content_list: list[dict] | None = None,
    max_tokens: int,
    temperature: float,
    max_retries: int,
    api_key: str | None = None,
    api_base: str | None = None,
    figure_api_key: str | None = None,
    figure_api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
) -> PaperSummary:
    """三遍渐进式提取：快速扫描 → 深度提取 → 图表分析 → 融合。"""
    logger.info("=" * 40)
    logger.info("多遍提取模式（三遍阅读法）")
    logger.info("=" * 40)

    if content_list:
        logger.info("使用 MinerU content_list 进行结构化分段 (%d 个内容块)", len(content_list))
        labeled_sections = _sections_from_content_list(content_list)
    else:
        labeled_sections = split_sections_with_labels(markdown_content)
    headings = get_section_headings(markdown_content)

    # --- Pass 1: 快速扫描 ---
    logger.info("--- Pass 1: 快速扫描 (model=%s) ---", scan_model)
    try:
        overview = _pass1_quick_scan(
            labeled_sections,
            headings,
            model=scan_model,
            max_retries=max_retries,
            api_key=api_key,
            api_base=api_base,
            on_token=on_token,
        )
    except Exception as exc:
        if scan_model != model:
            logger.warning("Pass 1 scan_model=%s 失败，回退到 extract_model=%s: %s", scan_model, model, exc)
            overview = _pass1_quick_scan(
                labeled_sections,
                headings,
                model=model,
                max_retries=max_retries,
                api_key=api_key,
                api_base=api_base,
                on_token=on_token,
            )
        else:
            raise
    logger.info(
        "Pass 1 完成: type=%s, contributions=%d, focus_questions=%d",
        overview.paper_type,
        len(overview.key_contributions),
        len(overview.reading_focus),
    )

    # --- Pass 2 + Pass 3 ---
    run_pass3 = images_dir and images_dir.exists()
    parallel_passes = os.getenv("THEIA_PARALLEL_PASSES", "false").lower() in ("1", "true", "yes")
    logger.info(
        "--- Pass 2: 深度提取 + Pass 3: 图表分析 (run_pass3=%s, parallel=%s) ---",
        run_pass3,
        parallel_passes,
    )

    def _do_pass2():
        return _pass2_deep_extract(
            labeled_sections,
            overview,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            max_retries=max_retries,
            api_key=api_key,
            api_base=api_base,
            on_token=on_token,
        )

    def _do_pass3():
        from .._utils import extract_figures_from_markdown
        from .figure_analyzer import analyze_figures

        raw_figures = extract_figures_from_markdown(markdown_content)
        if not raw_figures:
            logger.info("Pass 3 跳过: 未检测到图片引用")
            return None
        return analyze_figures(
            raw_figures,
            images_dir,
            overview,
            model=figure_model,
            api_key=figure_api_key or api_key,
            api_base=figure_api_base or api_base,
            on_token=on_token,
        )

    analyzed_figures = None

    if run_pass3 and parallel_passes:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_p2 = executor.submit(_do_pass2)
            future_p3 = executor.submit(_do_pass3)
            summary = future_p2.result()
            logger.info("Pass 2 完成: '%s', key_steps=%d", summary.title, len(summary.method.key_steps))
            try:
                analyzed_figures = future_p3.result()
            except Exception as exc:
                logger.warning("Pass 3 图表分析失败（不影响主流程）: %s", exc)
    else:
        summary = _do_pass2()
        logger.info("Pass 2 完成: '%s', key_steps=%d", summary.title, len(summary.method.key_steps))
        if run_pass3:
            try:
                analyzed_figures = _do_pass3()
            except Exception as exc:
                logger.warning("Pass 3 图表分析失败（不影响主流程）: %s", exc)

    if analyzed_figures:
        summary.figures = analyzed_figures
        logger.info("Pass 3 完成: %d 张图表已分析", len(analyzed_figures))

    # --- 融合验证 ---
    summary = _synthesize(summary, overview, markdown_content)

    evaluator = ExtractionEvaluator(markdown_content, labeled_sections)
    result = evaluator.evaluate_fast(summary)
    logger.info(
        "最终质量评分: %.1f/%.1f (L1=%.1f L2=%.1f)",
        result.fast_total,
        result.max_total,
        result.l1.total,
        result.l2.total,
    )

    return summary


def _pass1_quick_scan(
    labeled_sections: dict[str, str],
    headings: list[str],
    *,
    model: str,
    max_retries: int = 3,
    api_key: str | None = None,
    api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
) -> PaperOverview:
    """Pass 1：用轻量模型快速扫描摘要、引言、结论和章节结构。"""
    scan_parts: list[str] = []

    scan_parts.append("=== 章节结构 ===")
    scan_parts.append("\n".join(headings) if headings else "(无结构化标题)")

    for label in ("preamble", "abstract", "introduction"):
        content = labeled_sections.get(label, "")
        if content:
            scan_parts.append(f"\n=== {label.upper()} ===\n{content[:8000]}")

    conclusion = labeled_sections.get("conclusion", "")
    if conclusion:
        scan_parts.append(f"\n=== CONCLUSION ===\n{conclusion[:5000]}")

    scan_text = "\n".join(scan_parts)
    scan_limit = 20_000
    if len(scan_text) > scan_limit:
        scan_text = scan_text[:scan_limit] + "\n\n[... 已截断 ...]"

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            user_content = PASS1_PROMPT.format(scan_text=scan_text)
            kwargs: dict = {
                "model": model,
                "messages": [
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 4096,
            }
            if api_key:
                kwargs["api_key"] = api_key
            if api_base:
                kwargs["api_base"] = api_base
            response = robust_completion(kwargs, on_token=on_token)
            raw = extract_json_from_response(response)
            data = json.loads(raw)
            return PaperOverview(**data)
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            last_error = exc
            logger.warning("Pass 1 第 %d/%d 次尝试失败: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(2**attempt)

    logger.warning("Pass 1 失败，使用默认 PaperOverview: %s", last_error)
    return PaperOverview(
        paper_type="empirical",
        core_idea="",
        key_contributions=[],
        important_sections=[],
        reading_focus=["这篇论文的核心方法是什么？", "主要实验结果如何？"],
    )


def _pass2_deep_extract(
    labeled_sections: dict[str, str],
    overview: PaperOverview,
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    max_retries: int,
    api_key: str | None = None,
    api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
) -> PaperSummary:
    """Pass 2：带着问题对重点章节进行深度提取。

    自动检测文本长度：
    - 文本较短时使用一次性提取（质量更高）
    - 文本过长时使用分段提取（兼容小上下文窗口模型）
    - 一次性提取因 token 限制失败时自动降级到分段提取
    """
    truncated_sections = budget_truncate(dict(labeled_sections), max_chars=80_000)
    focused_text = "\n\n".join(truncated_sections.values())

    chunk_threshold = int(os.getenv("THEIA_CHUNK_THRESHOLD", "50000"))
    estimated_tokens = _estimate_tokens(focused_text)

    if len(focused_text) > chunk_threshold:
        logger.info(
            "文本过长 (%d chars, ~%d tokens)，切换到分段提取模式",
            len(focused_text),
            estimated_tokens,
        )
        chunk_chars = int(os.getenv("THEIA_CHUNK_CHARS", "6000"))
        return _pass2_chunked_extract(
            labeled_sections,
            overview,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            max_retries=max_retries,
            api_key=api_key,
            api_base=api_base,
            chunk_chars=chunk_chars,
            on_token=on_token,
        )

    overview_json = json.dumps(
        {"paper_type": overview.paper_type, "core_idea": overview.core_idea},
        ensure_ascii=False,
    )
    focus_list = (
        "\n".join(f"- {q}" for q in overview.reading_focus) if overview.reading_focus else "- 提取核心方法和实验结果"
    )

    user_content = PASS2_PROMPT.format(
        overview_json=overview_json,
        reading_focus=focus_list,
        focused_text=focused_text,
    )

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            kwargs: dict = {
                "model": model,
                "messages": [
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": max_tokens,
            }
            if api_key:
                kwargs["api_key"] = api_key
            if api_base:
                kwargs["api_base"] = api_base
            response = robust_completion(kwargs, on_token=on_token)
            raw = extract_json_from_response(response)
            data = json.loads(raw)
            return PaperSummary(**data)
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            last_error = exc
            logger.warning("Pass 2 第 %d/%d 次尝试失败: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                temperature = min(temperature + 0.1, 0.5)
                time.sleep(2**attempt)
        except Exception as exc:
            msg = str(exc).lower()
            if any(
                kw in msg
                for kw in (
                    "too large",
                    "tokens_limit",
                    "context_length",
                    "413",
                    "429",
                    "rate limit",
                    "ratelimit",
                    "quota",
                )
            ):
                logger.warning("检测到 API 限制错误，降级到分段提取: %s", exc)
                return _pass2_chunked_extract(
                    labeled_sections,
                    overview,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    max_retries=max_retries,
                    api_key=api_key,
                    api_base=api_base,
                    chunk_chars=int(os.getenv("THEIA_CHUNK_CHARS", "6000")),
                )
            raise

    logger.warning("一次性提取失败，降级到分段提取模式: %s", last_error)
    try:
        return _pass2_chunked_extract(
            labeled_sections,
            overview,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            max_retries=max_retries,
            api_key=api_key,
            api_base=api_base,
            chunk_chars=int(os.getenv("THEIA_CHUNK_CHARS", "6000")),
        )
    except Exception:
        pass

    raise ValueError(f"Pass 2 深度提取在 {max_retries} 次尝试后仍失败") from last_error
