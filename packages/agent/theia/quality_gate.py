"""ReAct 式质量门控。

在 extract → script 之间插入，通过「评估 → 分析弱点 → 针对性修复 → 再评估」
循环提升提取质量。最多 3 轮，达到阈值或无法继续改进时退出。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .evaluator import ExtractionEvaluator
from .llm_client import extract_json_from_response, robust_completion
from .schemas import PaperSummary

logger = logging.getLogger(__name__)

QUALITY_THRESHOLD = 5.0
MAX_REPAIR_ROUNDS = 3


def quality_gate_node(state: dict) -> dict:
    """ReAct 式质量控制节点。

    流程: evaluate → identify weaknesses → targeted repair → re-evaluate
    """
    summary = PaperSummary.model_validate_json(state["paper_summary_json"])
    markdown = state["markdown_content"]
    evaluator = ExtractionEvaluator(markdown)

    prev_score = -1.0
    for attempt in range(MAX_REPAIR_ROUNDS):
        result = evaluator.evaluate_fast(summary)
        score = result.fast_total

        if score >= QUALITY_THRESHOLD:
            logger.info("质量门控通过: %.1f/6.0 (阈值 %.1f)", score, QUALITY_THRESHOLD)
            break

        if abs(score - prev_score) < 0.01 and attempt > 0:
            logger.info("质量评分 %.1f/6.0 未改善，停止修复循环", score)
            break

        weak_dims = _identify_weaknesses(result)
        if not weak_dims:
            logger.info("质量评分 %.1f/6.0 但无明确弱点，跳过修复", score)
            break

        logger.warning(
            "质量评分 %.1f/6.0 (阈值 %.1f)，弱项: %s，第 %d 轮修复",
            score,
            QUALITY_THRESHOLD,
            weak_dims,
            attempt + 1,
        )

        prev_score = score
        summary = _targeted_repair(summary, weak_dims, markdown, state)
    else:
        result = evaluator.evaluate_fast(summary)
        logger.info("质量门控: %d 轮修复后评分 %.1f/6.0", MAX_REPAIR_ROUNDS, result.fast_total)

    return {"paper_summary_json": summary.model_dump_json(indent=2)}


def _identify_weaknesses(result) -> list[str]:
    """分析评估结果，找出薄弱维度。"""
    weak = []

    if result.l1.field_completeness < 0.7:
        weak.append("field_completeness")
    if result.l2.grounding < 1.0:
        weak.append("grounding")
    if result.l2.entity_match < 0.5:
        weak.append("entity_match")
    if result.l2.section_coverage < 0.6:
        weak.append("section_coverage")

    return weak


def _targeted_repair(
    summary: PaperSummary,
    weak_dims: list[str],
    markdown: str,
    state: dict,
) -> PaperSummary:
    """针对薄弱维度进行精准修复。"""
    model = state.get("extract_model") or state.get("llm_model", "gpt-4o")
    api_key = state.get("extract_api_key")
    api_base = state.get("extract_api_base")

    if "field_completeness" in weak_dims:
        summary = _fill_missing_fields(summary, markdown, model, api_key=api_key, api_base=api_base)

    if "grounding" in weak_dims or "entity_match" in weak_dims:
        summary = _verify_and_fix_entities(summary, markdown, model, api_key=api_key, api_base=api_base)

    if "section_coverage" in weak_dims:
        summary = _improve_section_coverage(summary, markdown, model, api_key=api_key, api_base=api_base)

    return summary


def _fill_missing_fields(
    summary: PaperSummary,
    markdown: str,
    model: str,
    *,
    api_key: str | None = None,
    api_base: str | None = None,
) -> PaperSummary:
    """找到缺失字段，针对性补全。"""
    missing = []
    if not summary.title:
        missing.append("title")
    if not summary.authors:
        missing.append("authors")
    if not summary.problem:
        missing.append("problem")
    if not summary.method.summary:
        missing.append("method.summary")
    if not summary.method.key_steps:
        missing.append("method.key_steps")
    if not summary.results.findings:
        missing.append("results.findings")
    if not summary.conclusion:
        missing.append("conclusion")
    if not summary.contributions:
        missing.append("contributions")

    if not missing:
        return summary

    truncated_md = markdown[:15000] if len(markdown) > 15000 else markdown

    prompt = (
        f"以下论文摘要缺少这些字段: {missing}\n\n"
        f"当前摘要:\n{json.dumps(summary.model_dump(), ensure_ascii=False, indent=2)}\n\n"
        f"论文原文片段:\n{truncated_md}\n\n"
        "请仅补全缺失字段，返回完整的 JSON。保持已有字段不变。"
    )

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.1,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    try:
        resp = robust_completion(kwargs)
        raw = extract_json_from_response(resp)
        if raw:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            return PaperSummary(**{**summary.model_dump(), **parsed})
    except Exception as exc:
        logger.warning("字段补全失败: %s", exc)

    return summary


def _verify_and_fix_entities(
    summary: PaperSummary,
    markdown: str,
    model: str,
    *,
    api_key: str | None = None,
    api_base: str | None = None,
) -> PaperSummary:
    """验证关键实体是否在原文中，修复不一致。"""
    key_entities = []
    if summary.title:
        key_entities.append(("title", summary.title))
    for author in summary.authors[:5]:
        key_entities.append(("author", author))
    for ds in summary.results.datasets[:3]:
        key_entities.append(("dataset", ds))

    ungrounded = []
    md_lower = markdown.lower()
    for etype, entity in key_entities:
        if entity.lower() not in md_lower:
            ungrounded.append(f"{etype}: {entity}")

    if not ungrounded:
        return summary

    logger.info("发现 %d 个未溯源实体，尝试修复", len(ungrounded))

    truncated_md = markdown[:10000] if len(markdown) > 10000 else markdown

    prompt = (
        "以下实体在论文原文中找不到对应文本:\n"
        + "\n".join(f"- {u}" for u in ungrounded)
        + f"\n\n论文原文片段:\n{truncated_md}\n\n"
        f"当前摘要:\n{json.dumps(summary.model_dump(), ensure_ascii=False, indent=2)}\n\n"
        "请根据原文修正这些实体，返回完整的修正后 JSON。"
    )

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.1,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    try:
        resp = robust_completion(kwargs)
        raw = extract_json_from_response(resp)
        if raw:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            return PaperSummary(**parsed)
    except Exception as exc:
        logger.warning("实体修复失败: %s", exc)

    return summary


def _improve_section_coverage(
    summary: PaperSummary,
    markdown: str,
    model: str,
    *,
    api_key: str | None = None,
    api_base: str | None = None,
) -> PaperSummary:
    """补充章节覆盖不足的信息。"""
    gaps = []
    if not summary.problem:
        gaps.append("problem（研究问题/动机，来自 Introduction）")
    if not summary.method.summary:
        gaps.append("method.summary（方法概要，来自 Method 章节）")
    if not summary.results.findings:
        gaps.append("results.findings（实验发现，来自 Experiments 章节）")
    if not summary.conclusion:
        gaps.append("conclusion（结论，来自 Conclusion 章节）")

    if not gaps:
        return summary

    logger.info("章节覆盖不足，尝试从原文补充: %s", gaps)

    truncated_md = markdown[:20000] if len(markdown) > 20000 else markdown

    prompt = (
        "以下字段信息不足或缺失，请从论文原文中提取并补充:\n"
        + "\n".join(f"- {g}" for g in gaps)
        + f"\n\n论文原文:\n{truncated_md}\n\n"
        f"当前摘要:\n{json.dumps(summary.model_dump(), ensure_ascii=False, indent=2)}\n\n"
        "请补充缺失信息，返回完整的 JSON。保持已有内容不变。"
    )

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.1,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    try:
        resp = robust_completion(kwargs)
        raw = extract_json_from_response(resp)
        if raw:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            return PaperSummary(**{**summary.model_dump(), **parsed})
    except Exception as exc:
        logger.warning("章节覆盖修复失败: %s", exc)

    return summary
