"""ReAct 式质量门控。

在 extract → script 之间插入，通过「评估 → 分析弱点 → 针对性修复 → 再评估」
循环提升提取质量。最多 3 轮，达到阈值或无法继续改进时退出。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from .evaluator import ExtractionEvaluator, _extract_key_terms
from ..llm.client import extract_json_from_response, robust_completion
from ..llm.config import split_sections_with_labels
from ..schemas import PaperSummary

logger = logging.getLogger(__name__)

QUALITY_THRESHOLD = 5.5
MAX_REPAIR_ROUNDS = 3


def run_quality_gate(
    summary: PaperSummary,
    markdown: str,
    state: dict,
    *,
    content_list_json: str | None = None,
) -> PaperSummary:
    """ReAct 式质量控制。

    流程: evaluate → identify weaknesses → targeted repair → re-evaluate
    可作为独立函数在 extract_node 内部调用。

    返回修复后的 PaperSummary（如果无需修复则返回原对象）。
    """
    labeled_sections = None
    if content_list_json:
        from ..extraction.synthesize import _sections_from_content_list

        content_list = json.loads(content_list_json)
        labeled_sections = _sections_from_content_list(content_list)

    evaluator = ExtractionEvaluator(markdown, labeled_sections)

    prev_score = -1.0
    failed_dims: set[str] = set()

    for attempt in range(MAX_REPAIR_ROUNDS):
        result = evaluator.evaluate_fast(summary)
        score = result.fast_total

        logger.info(
            "质量门控评估: %.1f/%.1f (L1: schema=%.2f field=%.2f num=%.2f | "
            "L2: ground=%.2f entity=%.2f section=%.2f div=%.2f density=%.2f)",
            score,
            result.max_total,
            result.l1.schema_compliance,
            result.l1.field_completeness,
            result.l1.numeric_verifiability,
            result.l2.grounding,
            result.l2.entity_match,
            result.l2.section_coverage,
            result.l2.diversity,
            result.l2.information_density,
        )

        if score >= QUALITY_THRESHOLD:
            logger.info(
                "质量门控通过: %.1f/%.1f (阈值 %.1f)", score, result.max_total, QUALITY_THRESHOLD,
            )
            break

        if abs(score - prev_score) < 0.01 and attempt > 0:
            logger.info("质量评分 %.1f 未改善，停止修复循环", score)
            break

        weak_dims = _identify_weaknesses(result)
        weak_dims = [d for d in weak_dims if d not in failed_dims]
        if not weak_dims:
            logger.info("质量评分 %.1f 但无可修复弱点（已跳过: %s），停止", score, failed_dims or "无")
            break

        # 按 ROI 排序：field_completeness > section_coverage > grounding > entity_match
        priority = {"field_completeness": 0, "section_coverage": 1, "grounding": 2, "entity_match": 3}
        weak_dims.sort(key=lambda d: priority.get(d, 99))

        logger.warning(
            "质量评分 %.1f/%.1f (阈值 %.1f)，弱项: %s，第 %d 轮修复",
            score,
            result.max_total,
            QUALITY_THRESHOLD,
            weak_dims,
            attempt + 1,
        )

        prev_score = score
        prev_summary_json = summary.model_dump_json()

        from ..pipeline import _make_on_token

        on_token = _make_on_token(state.get("workspace", ""), "quality_gate")
        summary = _targeted_repair(summary, weak_dims, markdown, state, on_token=on_token)

        if summary.model_dump_json() == prev_summary_json:
            failed_dims.update(weak_dims)
            logger.info("第 %d 轮修复未产生变化，标记 %s 为无效维度", attempt + 1, weak_dims)
    else:
        result = evaluator.evaluate_fast(summary)
        logger.info(
            "质量门控: %d 轮修复后评分 %.1f/%.1f", MAX_REPAIR_ROUNDS, result.fast_total, result.max_total,
        )

    return summary


def quality_gate_node(state: dict) -> dict:
    """LangGraph 节点包装器（向后兼容）。"""
    summary = PaperSummary.model_validate_json(state["paper_summary_json"])
    markdown = state["markdown_content"]
    cl_json = state.get("content_list_json")

    summary = run_quality_gate(summary, markdown, state, content_list_json=cl_json)
    return {"paper_summary_json": summary.model_dump_json(indent=2)}


def _identify_weaknesses(result) -> list[str]:
    """分析评估结果，找出薄弱维度。

    覆盖 L1 和 L2 所有子维度，阈值按各维度满分比例设置。
    总分不达标但无具体弱项时，回退到覆盖率修复（兜底）。
    """
    weak = []

    # L1 (满分 2.0)
    if result.l1.schema_compliance < 0.4:       # 满分 0.5
        weak.append("field_completeness")
    if result.l1.field_completeness < 0.7:      # 满分 1.0
        weak.append("field_completeness")
    if result.l1.numeric_verifiability < 0.25:  # 满分 0.5
        weak.append("field_completeness")

    # L2 (满分 4.5)
    if result.l2.grounding < 1.0:               # 满分 1.5
        weak.append("grounding")
    if result.l2.entity_match < 0.5:            # 满分 1.0
        weak.append("entity_match")
    if result.l2.section_coverage < 0.6:        # 满分 1.0
        weak.append("section_coverage")
    if result.l2.diversity < 0.2:               # 满分 0.5
        weak.append("section_coverage")
    if result.l2.information_density < 0.3:     # 满分 0.5
        weak.append("section_coverage")

    weak = list(dict.fromkeys(weak))

    if not weak and result.fast_total < QUALITY_THRESHOLD:
        weak.append("section_coverage")

    return weak


def _targeted_repair(
    summary: PaperSummary,
    weak_dims: list[str],
    markdown: str,
    state: dict,
    *,
    on_token: Callable[[str], None] | None = None,
) -> PaperSummary:
    """针对薄弱维度进行精准修复。"""
    model = state.get("extract_model") or state.get("llm_model", "gpt-4o")
    api_key = state.get("extract_api_key")
    api_base = state.get("extract_api_base")

    if "field_completeness" in weak_dims:
        summary = _fill_missing_fields(summary, markdown, model, api_key=api_key, api_base=api_base, on_token=on_token)

    if "grounding" in weak_dims or "entity_match" in weak_dims:
        summary = _verify_and_fix_entities(summary, markdown, model, api_key=api_key, api_base=api_base, on_token=on_token)

    if "section_coverage" in weak_dims:
        summary = _improve_section_coverage(summary, markdown, model, api_key=api_key, api_base=api_base, on_token=on_token)

    return summary


def _fill_missing_fields(
    summary: PaperSummary,
    markdown: str,
    model: str,
    *,
    api_key: str | None = None,
    api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
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
        resp = robust_completion(kwargs, on_token=on_token)
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
    on_token: Callable[[str], None] | None = None,
) -> PaperSummary:
    """验证关键实体和声明是否在原文中有依据，修复不一致。

    同时检查：实体（标题、作者、数据集）和声明（key_steps、contributions）。
    """
    import re

    md_lower = markdown.lower()

    # 检查实体
    ungrounded_entities = []
    if summary.title and summary.title.lower() not in md_lower:
        ungrounded_entities.append(f"title: {summary.title}")
    for author in summary.authors[:5]:
        if author.lower() not in md_lower:
            ungrounded_entities.append(f"author: {author}")
    for ds in summary.results.datasets[:3]:
        if ds.lower() not in md_lower:
            ungrounded_entities.append(f"dataset: {ds}")

    # 检查声明中的关键术语是否在原文对应章节中（与评估器使用相同逻辑）
    labeled_sections = split_sections_with_labels(markdown)
    method_section = labeled_sections.get("method", "")
    method_lower = (method_section or markdown).lower()

    ungrounded_claims = []
    for i, step in enumerate(summary.method.key_steps):
        terms = _extract_key_terms(step)
        if terms and not any(t.lower() in method_lower for t in terms):
            ungrounded_claims.append(f"method.key_steps[{i}]: {step[:80]}")

    for i, metric in enumerate(summary.results.metrics):
        terms = _extract_key_terms(metric)
        if terms and not any(t.lower() in md_lower for t in terms):
            ungrounded_claims.append(f"results.metrics[{i}]: {metric[:80]}")

    for i, contrib in enumerate(summary.contributions):
        terms = _extract_key_terms(contrib)
        if terms and not any(t.lower() in md_lower for t in terms):
            ungrounded_claims.append(f"contributions[{i}]: {contrib[:80]}")

    all_issues = ungrounded_entities + ungrounded_claims
    if not all_issues:
        return summary

    logger.info(
        "发现 %d 个溯源问题 (%d 实体 + %d 声明)，尝试修复",
        len(all_issues), len(ungrounded_entities), len(ungrounded_claims),
    )

    truncated_md = markdown[:15000] if len(markdown) > 15000 else markdown

    affected_fields: dict[str, Any] = {}
    if ungrounded_entities:
        if any("title" in u for u in ungrounded_entities):
            affected_fields["title"] = summary.title
        if any("author" in u for u in ungrounded_entities):
            affected_fields["authors"] = summary.authors
        if any("dataset" in u for u in ungrounded_entities):
            affected_fields["results"] = {"datasets": summary.results.datasets}

    if any("key_steps" in u for u in ungrounded_claims):
        affected_fields["method"] = {"key_steps": summary.method.key_steps}
    if any("metrics" in u for u in ungrounded_claims):
        affected_fields.setdefault("results", {})["metrics"] = summary.results.metrics
    if any("contributions" in u for u in ungrounded_claims):
        affected_fields["contributions"] = summary.contributions

    prompt = (
        "以下提取内容在论文原文中找不到对应依据:\n"
        + "\n".join(f"- {u}" for u in all_issues)
        + f"\n\n论文原文片段:\n{truncated_md}\n\n"
        f"需要修正的字段:\n{json.dumps(affected_fields, ensure_ascii=False, indent=2)}\n\n"
        "请根据原文修正上述字段，确保每条声明都能在原文中找到依据。\n"
        "仅返回修正后的字段 JSON（与上面相同的键名），不要返回完整摘要。"
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
        resp = robust_completion(kwargs, on_token=on_token)
        raw = extract_json_from_response(resp)
        if raw:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            merged = summary.model_dump()
            for key, val in parsed.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
                    merged[key].update(val)
                else:
                    merged[key] = val
            return PaperSummary(**merged)
    except Exception as exc:
        logger.warning("溯源修复失败: %s", exc)

    return summary


def _improve_section_coverage(
    summary: PaperSummary,
    markdown: str,
    model: str,
    *,
    api_key: str | None = None,
    api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
) -> PaperSummary:
    """补充章节覆盖不足的信息。"""
    min_len = 100
    gaps = []
    if not summary.problem or len(summary.problem) < min_len:
        gaps.append("problem（研究问题/动机，来自 Introduction，至少 3-5 句）")
    if not summary.method.summary or len(summary.method.summary) < min_len:
        gaps.append("method.summary（方法概要，来自 Method 章节，至少 3-5 句）")
    if not summary.results.findings or len(summary.results.findings) < min_len:
        gaps.append("results.findings（实验发现，来自 Experiments 章节，至少 3-5 句）")
    if not summary.conclusion or len(summary.conclusion) < min_len:
        gaps.append("conclusion（结论，来自 Conclusion 章节，至少 3-5 句）")

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
        resp = robust_completion(kwargs, on_token=on_token)
        raw = extract_json_from_response(resp)
        if raw:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            return PaperSummary(**{**summary.model_dump(), **parsed})
    except Exception as exc:
        logger.warning("章节覆盖修复失败: %s", exc)

    return summary
