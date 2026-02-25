"""分段提取（Chunked Pass 2）：将论文按章节分段提取后融合。"""

from __future__ import annotations

import json
import logging
import time

from pydantic import ValidationError

from ._extract_utils import (
    _HIGH_VALUE_SECTIONS,
    _SECTION_LABELS_ZH,
    _SECTION_PROCESS_ORDER,
    _estimate_tokens,
)
from .llm_client import extract_json_from_response, robust_completion
from .prompts.extraction_section import PASS2_MERGE_PROMPT, PASS2_SECTION_PROMPT
from .schemas import (
    BaselineResult,
    MethodDetail,
    PaperOverview,
    PaperSummary,
    ResultDetail,
)

logger = logging.getLogger(__name__)


def _pass2_chunked_extract(
    labeled_sections: dict[str, str],
    overview: PaperOverview,
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    max_retries: int,
    api_key: str | None = None,
    api_base: str | None = None,
    chunk_chars: int = 6000,
) -> PaperSummary:
    """分段提取：将论文按章节分段，逐段提取后融合。

    适用于上下文窗口较小的模型。每个章节独立提取，
    通过渐进式上下文传递确保后续章节能获取此前的信息。

    参数:
        chunk_chars: 每个章节块的最大字符数（默认 6000，约 2000 tokens）。
    """
    logger.info("使用分段提取模式 (chunk_chars=%d)", chunk_chars)

    section_results: list[dict] = []
    context_parts: list[str] = []

    for label in _SECTION_PROCESS_ORDER:
        content = labeled_sections.get(label)
        if not content or not content.strip():
            continue

        effective_limit = chunk_chars * 2 if label in _HIGH_VALUE_SECTIONS else chunk_chars
        if len(content) > effective_limit:
            content = content[:effective_limit] + "\n\n[... 章节已截断 ...]"

        label_zh = _SECTION_LABELS_ZH.get(label, label)

        context_block = ""
        if context_parts:
            context_block = "\n已阅读章节的关键信息：\n" + "\n".join(f"- {c}" for c in context_parts[-5:])

        try:
            result = _extract_single_section(
                section_text=content,
                section_label=label_zh,
                overview=overview,
                context_block=context_block,
                model=model,
                max_tokens=min(max_tokens, 2048),
                temperature=temperature,
                max_retries=max_retries,
                api_key=api_key,
                api_base=api_base,
            )
        except Exception as exc:
            logger.warning("章节 [%s] 提取异常，跳过: %s", label_zh, exc)
            result = None

        if result:
            result["_label"] = label
            section_results.append(result)
            summary_text = result.get("section_summary", "")
            if summary_text:
                context_parts.append(f"[{label_zh}] {summary_text}")
            logger.info("  章节 [%s] 提取完成", label_zh)

    if not section_results:
        raise ValueError("分段提取未获得任何结果")

    return _merge_section_results(
        section_results,
        overview=overview,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        max_retries=max_retries,
        api_key=api_key,
        api_base=api_base,
    )


def _extract_single_section(
    *,
    section_text: str,
    section_label: str,
    overview: PaperOverview,
    context_block: str,
    model: str,
    max_tokens: int,
    temperature: float,
    max_retries: int,
    api_key: str | None = None,
    api_base: str | None = None,
) -> dict | None:
    """对单个章节进行信息提取，返回结构化 dict。"""
    user_content = PASS2_SECTION_PROMPT.format(
        section_label=section_label,
        paper_type=overview.paper_type,
        core_idea=overview.core_idea,
        context_block=context_block,
        section_text=section_text,
    )

    for attempt in range(1, max_retries + 1):
        try:
            kwargs: dict = {
                "model": model,
                "messages": [{"role": "user", "content": user_content}],
                "max_tokens": max_tokens,
            }
            if api_key:
                kwargs["api_key"] = api_key
            if api_base:
                kwargs["api_base"] = api_base
            response = robust_completion(kwargs)
            raw = extract_json_from_response(response)
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "章节 [%s] 第 %d/%d 次提取失败: %s",
                section_label,
                attempt,
                max_retries,
                exc,
            )
            if attempt < max_retries:
                time.sleep(2**attempt)
        except Exception as exc:
            msg = str(exc).lower()
            if any(kw in msg for kw in ("too large", "tokens_limit", "413")):
                logger.warning("章节 [%s] 超出 token 限制，截断后重试", section_label)
                half = len(section_text) // 2
                user_content = PASS2_SECTION_PROMPT.format(
                    section_label=section_label,
                    paper_type=overview.paper_type,
                    core_idea=overview.core_idea,
                    context_block=context_block,
                    section_text=section_text[:half] + "\n\n[... 已截断 ...]",
                )
                continue
            if any(kw in msg for kw in ("429", "rate limit", "ratelimit", "quota")):
                logger.warning("章节 [%s] 遇到频率限制，跳过: %s", section_label, exc)
                return None
            raise

    logger.warning("章节 [%s] 提取失败，跳过", section_label)
    return None


def _merge_section_results(
    section_results: list[dict],
    *,
    overview: PaperOverview,
    model: str,
    max_tokens: int,
    temperature: float,
    max_retries: int,
    api_key: str | None = None,
    api_base: str | None = None,
) -> PaperSummary:
    """将多个章节的提取结果融合为完整的 PaperSummary。

    优先使用 LLM 融合以保证连贯性；LLM 失败时降级到规则合并。
    """
    compressed = []
    for r in section_results:
        c = {k: v for k, v in r.items() if v and v != [] and v != "" and k != "_label"}
        compressed.append(c)
    results_text = json.dumps(compressed, ensure_ascii=False, indent=1)

    if _estimate_tokens(results_text) > 3000:
        for c in compressed:
            if "section_summary" in c and len(c["section_summary"]) > 100:
                c["section_summary"] = c["section_summary"][:100] + "..."
        results_text = json.dumps(compressed, ensure_ascii=False, indent=1)

    user_content = PASS2_MERGE_PROMPT.format(section_results=results_text)

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            kwargs: dict = {
                "model": model,
                "messages": [{"role": "user", "content": user_content}],
                "max_tokens": max_tokens,
            }
            if api_key:
                kwargs["api_key"] = api_key
            if api_base:
                kwargs["api_base"] = api_base
            response = robust_completion(kwargs)
            raw = extract_json_from_response(response)
            data = json.loads(raw)
            return PaperSummary(**data)
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            last_error = exc
            logger.warning("融合第 %d/%d 次尝试失败: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(2**attempt)

    logger.warning("LLM 融合失败，使用规则融合: %s", last_error)
    return _manual_merge(section_results, overview)


def _manual_merge(
    section_results: list[dict],
    overview: PaperOverview,
) -> PaperSummary:
    """当 LLM 融合失败时，使用规则手动合并章节结果。"""
    title = ""
    authors: list[str] = []
    year = None
    problem = ""
    method_summary = ""
    method_steps: list[str] = []
    formulas: list[str] = []
    datasets: list[str] = []
    metrics: list[str] = []
    baselines: list[BaselineResult] = []
    findings = ""
    conclusion = ""
    contributions: list[str] = []
    key_insights: list[str] = []

    for r in section_results:
        if r.get("title") and not title:
            title = r["title"]
        if r.get("authors") and not authors:
            authors = r["authors"]
        if r.get("year") and year is None:
            year = r["year"]
        if r.get("problem") and not problem:
            problem = r["problem"]
        if r.get("method_summary"):
            method_summary = r["method_summary"]
        method_steps.extend(r.get("method_steps", []))
        formulas.extend(r.get("formulas", []))
        datasets.extend(r.get("datasets", []))
        metrics.extend(r.get("metrics", []))
        if r.get("findings"):
            findings = r["findings"]
        if r.get("conclusion"):
            conclusion = r["conclusion"]
        contributions.extend(r.get("contributions", []))
        key_insights.extend(r.get("key_insights", []))

        for b in r.get("baselines", []):
            if isinstance(b, dict):
                try:
                    baselines.append(BaselineResult(**b))
                except Exception:
                    pass

    method_steps = list(dict.fromkeys(method_steps))
    formulas = list(dict.fromkeys(formulas))
    datasets = list(dict.fromkeys(datasets))
    contributions = list(dict.fromkeys(contributions))
    key_insights = list(dict.fromkeys(key_insights))

    return PaperSummary(
        title=title or overview.core_idea,
        authors=authors,
        year=year,
        problem=problem or overview.core_idea,
        method=MethodDetail(
            summary=method_summary or overview.core_idea,
            key_steps=method_steps[:5],
            formulas=formulas[:3],
        ),
        results=ResultDetail(
            datasets=datasets,
            metrics=metrics,
            baselines=baselines,
            findings=findings,
        ),
        conclusion=conclusion,
        contributions=contributions or overview.key_contributions,
        key_insights=key_insights,
        paper_type=overview.paper_type,
        core_idea=overview.core_idea,
    )
