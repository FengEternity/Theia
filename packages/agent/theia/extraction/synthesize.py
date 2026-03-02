"""融合与质量验证：将多遍提取结果合并并进行交叉验证。"""

from __future__ import annotations

import logging
import re

from ..schemas import PaperOverview, PaperSummary

logger = logging.getLogger(__name__)


def _sections_from_content_list(content_list: list[dict]) -> dict[str, str]:
    """从 MinerU content_list JSON 构建语义分段。

    content_list 中每个元素包含 type（text/image/table/discarded）、
    text、text_level（标题级别）等字段。利用这些结构化信息
    比正则匹配 Markdown 标题更精确地识别章节边界。
    """
    from ..llm.config import _classify_section

    sections: list[tuple[str, list[str]]] = []
    current_heading = "preamble"
    current_parts: list[str] = []

    for item in content_list:
        item_type = item.get("type", "")
        text = item.get("text", "").strip()

        if item_type == "discarded" or not text:
            continue

        if item_type == "text" and item.get("text_level", 0) == 1 and len(text) < 200:
            if current_parts:
                sections.append((current_heading, current_parts))
            current_heading = text
            current_parts = []
            continue

        if item_type == "image":
            captions = item.get("image_caption", [])
            caption_text = " ".join(captions) if captions else ""
            img_path = item.get("img_path", "")
            if img_path or caption_text:
                current_parts.append(f"![{caption_text}]({img_path})")
            continue

        if item_type == "table":
            table_body = item.get("table_body", text)
            current_parts.append(table_body)
            continue

        current_parts.append(text)

    if current_parts:
        sections.append((current_heading, current_parts))

    labeled: dict[str, list[str]] = {}
    for heading, parts in sections:
        label = _classify_section(heading) if heading != "preamble" else "preamble"
        content = "\n\n".join(parts)
        labeled.setdefault(label, []).append(content)

    return {label: "\n\n".join(parts) for label, parts in labeled.items()}


def _recover_full_title(title: str, original: str) -> str:
    """尝试从原文中恢复完整标题。

    当 LLM 截断了标题时，用提取标题的前缀在原文中搜索，
    找到匹配行后返回完整标题。
    """
    original_lower = original.lower()
    title_lower = title.lower().strip()

    if title_lower[:30] in original_lower:
        idx = original_lower.index(title_lower[:30])
        end = original.find("\n", idx)
        if end == -1:
            end = min(idx + 300, len(original))
        candidate = original[idx:end].strip()
        if len(candidate) > len(title) and candidate.lower().startswith(title_lower[:20]):
            logger.info("标题已从原文恢复: '%s' -> '%s'", title, candidate)
            return candidate
        return title

    if len(title) > 10:
        logger.warning("交叉验证警告：提取的标题可能不准确 '%s'", title)
    return title


def _synthesize(
    summary: PaperSummary,
    overview: PaperOverview,
    original: str,
) -> PaperSummary:
    """将 Pass 1 的概览信息融合到 Pass 2 的详细提取结果中，并做交叉验证。"""
    if not summary.paper_type and overview.paper_type:
        summary.paper_type = overview.paper_type
    if not summary.core_idea and overview.core_idea:
        summary.core_idea = overview.core_idea

    if not summary.contributions and overview.key_contributions:
        summary.contributions = overview.key_contributions

    if not summary.key_insights:
        insights = []
        if overview.core_idea:
            insights.append(overview.core_idea)
        insights.extend(overview.key_contributions[:2])
        summary.key_insights = insights

    if summary.title:
        summary.title = _recover_full_title(summary.title, original)

    for metric in summary.results.metrics:
        numbers = re.findall(r"\d+\.?\d*", metric)
        for num in numbers:
            if num not in original:
                logger.warning("交叉验证警告：指标中的数字 '%s' 未在原文中找到", num)
                break

    summary = _validate_enriched_fields(summary)
    return summary


def _merge_figure_results(
    summary: PaperSummary,
    result_table_data: list[dict],
) -> PaperSummary:
    """将图表中提取的实验数据合并到 PaperSummary.results 中。

    策略：
    - Pass 2 已有 >=3 条 baselines → 以 Pass 2 为主，不覆盖
    - Pass 2 baselines 不足 → 用图表数据补充
    - datasets 做去重追加
    """
    from ..schemas import BaselineResult

    def _dedup_key(name: str, metric: str, value: float | None = None) -> tuple:
        """Normalize name+metric for deduplication across LLM/table sources."""
        n = re.sub(r"\s*[\[\(（].*?[\]\)）]", "", name.lower().strip())
        n = re.sub(r"\s+", " ", n).strip()
        m = metric.lower().strip()
        return (n, m, value)

    existing_keys = {
        _dedup_key(b.name, b.metric or "", b.value)
        for b in summary.results.baselines
    }

    new_baselines: list[BaselineResult] = []
    new_datasets: set[str] = set(summary.results.datasets)

    for table in result_table_data:
        td = table.get("table_data", {})
        if not td:
            continue

        table_datasets = [ds.strip() for ds in td.get("datasets", []) if ds and ds.strip()]
        dataset_label = ", ".join(table_datasets) if table_datasets else ""

        for ds in table_datasets:
            new_datasets.add(ds)

        skip_metrics = {
            "training cost", "flops", "params", "parameters", "steps",
            "train", "time", "gpu", "memory", "speed",
        }

        for row in td.get("rows", []):
            method_name = row.get("method", "").strip()
            if not method_name:
                continue
            is_proposed = row.get("is_proposed", False)
            for metric_name, value in row.get("values", {}).items():
                if value is None:
                    continue
                try:
                    float_val = float(value)
                except (ValueError, TypeError):
                    continue
                metric_lower = metric_name.lower()
                if any(s in metric_lower for s in skip_metrics):
                    continue
                if metric_name.startswith("col_"):
                    continue
                key = _dedup_key(method_name, metric_name or "", float_val)
                if key not in existing_keys:
                    new_baselines.append(BaselineResult(
                        name=method_name,
                        metric=metric_name,
                        value=float_val,
                        highlight=is_proposed,
                        dataset=dataset_label,
                    ))
                    existing_keys.add(key)

        cd = table.get("chart_data", {})
        if cd and cd.get("key_comparison"):
            comparison_note = cd["key_comparison"]
            if comparison_note not in (summary.results.findings or ""):
                if summary.results.findings:
                    summary.results.findings += f" {comparison_note}"
                else:
                    summary.results.findings = comparison_note

    if new_baselines:
        summary.results.baselines.extend(new_baselines)
        logger.info(
            "从图表/表格中合并了 %d 条 baselines（总计 %d 条）",
            len(new_baselines),
            len(summary.results.baselines),
        )

    added_datasets = new_datasets - set(summary.results.datasets)
    if added_datasets:
        summary.results.datasets.extend(sorted(added_datasets))
        logger.info("从图表中补充了 %d 个 datasets", len(added_datasets))

    return summary


def _validate_enriched_fields(summary: PaperSummary) -> PaperSummary:
    """验证新增字段的基本质量，过滤无效数据。"""
    if hasattr(summary, "key_concepts"):
        summary.key_concepts = [
            kc for kc in summary.key_concepts
            if kc.term.strip() and kc.definition.strip()
        ]

    if hasattr(summary, "analogies"):
        summary.analogies = [
            a for a in summary.analogies
            if a.concept.strip() and a.analogy.strip()
        ]

    if hasattr(summary, "code_snippets"):
        summary.code_snippets = [
            cs for cs in summary.code_snippets
            if cs.strip() and len(cs.strip()) > 10
        ]

    if hasattr(summary, "audience_takeaways"):
        summary.audience_takeaways = [
            t for t in summary.audience_takeaways
            if t.strip() and len(t.strip()) > 5
        ]

    return summary


def synthesize_with_figures(
    summary: PaperSummary,
    overview: PaperOverview,
    original: str,
    result_table_data: list[dict] | None = None,
) -> PaperSummary:
    """增强版融合：Pass 1+2 融合 → Figure 数据反哺 → 新字段验证。"""
    summary = _synthesize(summary, overview, original)
    if result_table_data:
        summary = _merge_figure_results(summary, result_table_data)
    return summary


def _quality_score(summary: PaperSummary, original: str) -> float:
    """评估抽取结果的质量（0-10 分）。

    在原有长度检查的基础上增加了语义一致性验证。
    """
    score = 0.0

    if summary.title and len(summary.title) > 5:
        score += 1.0
    if len(summary.authors) >= 1:
        score += 0.5
    if summary.problem and len(summary.problem) > 20:
        score += 1.0
    if summary.method.summary and len(summary.method.summary) > 30:
        score += 1.0
    if len(summary.method.key_steps) >= 2:
        score += 0.5
    if len(summary.method.key_steps) >= 4:
        score += 0.5
    if summary.results.findings and len(summary.results.findings) > 20:
        score += 0.5
    if len(summary.results.metrics) >= 1:
        score += 0.5
    if summary.conclusion and len(summary.conclusion) > 20:
        score += 0.5

    original_lower = original.lower()

    if summary.title and summary.title.lower()[:20] in original_lower:
        score += 1.0

    if summary.method.key_steps:
        terms_found = 0
        for step in summary.method.key_steps:
            keywords = re.findall(r"[a-zA-Z]{4,}", step)
            for kw in keywords[:3]:
                if kw.lower() in original_lower:
                    terms_found += 1
                    break
        if terms_found >= len(summary.method.key_steps) * 0.5:
            score += 1.0

    if len(summary.contributions) >= 2:
        unique_enough = True
        for i, c1 in enumerate(summary.contributions):
            for c2 in summary.contributions[i + 1 :]:
                overlap = len(set(c1) & set(c2)) / max(len(set(c1) | set(c2)), 1)
                if overlap > 0.8:
                    unique_enough = False
                    break
        score += 1.0 if unique_enough else 0.3

    if summary.key_insights:
        score += 0.5
    if summary.core_idea:
        score += 0.5

    return min(score, 10.0)
