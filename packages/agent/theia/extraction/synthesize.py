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
