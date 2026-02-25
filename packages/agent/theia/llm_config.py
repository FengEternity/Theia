"""LLM 配置与多模型策略。

允许流水线不同步骤使用不同模型，以优化成本与性能。
重型提取任务使用强模型，轻量任务（旁白生成）可使用更便宜的模型。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """各步骤的模型配置。

    默认值可通过环境变量或 CLI 参数覆盖。
    ``scan_model`` 用于 Pass 1 快速扫描（轻量），
    ``extract_model`` 用于 Pass 2 深度提取和 Pass 3 图表分析（强模型），
    ``script_model`` 用于旁白生成（较简单的创意任务）。
    """

    extract_model: str = field(default_factory=lambda: os.getenv("THEIA_EXTRACT_MODEL", "gpt-4o"))
    scan_model: str = field(
        default_factory=lambda: os.getenv(
            "THEIA_SCAN_MODEL",
            os.getenv("THEIA_EXTRACT_MODEL", "gpt-4o"),
        )
    )
    script_model: str = field(default_factory=lambda: os.getenv("THEIA_SCRIPT_MODEL", "gpt-4o-mini"))
    figure_model: str = field(default_factory=lambda: os.getenv("THEIA_FIGURE_MODEL", "gpt-4o"))

    extract_api_key: str | None = field(default_factory=lambda: os.getenv("THEIA_EXTRACT_API_KEY"))
    extract_api_base: str | None = field(default_factory=lambda: os.getenv("THEIA_EXTRACT_API_BASE"))
    script_api_key: str | None = field(default_factory=lambda: os.getenv("THEIA_SCRIPT_API_KEY"))
    script_api_base: str | None = field(default_factory=lambda: os.getenv("THEIA_SCRIPT_API_BASE"))
    figure_api_key: str | None = field(
        default_factory=lambda: os.getenv(
            "THEIA_FIGURE_API_KEY",
            os.getenv("THEIA_EXTRACT_API_KEY"),
        )
    )
    figure_api_base: str | None = field(
        default_factory=lambda: os.getenv(
            "THEIA_FIGURE_API_BASE",
            os.getenv("THEIA_EXTRACT_API_BASE"),
        )
    )

    @classmethod
    def from_single_model(cls, model: str) -> LLMConfig:
        """所有步骤使用同一模型。"""
        return cls(scan_model=model, extract_model=model, script_model=model)


def detect_language(text: str) -> str:
    """检测文本主要语言是中文还是英文。

    使用简单的 CJK 字符比例启发式方法——快速且无外部依赖。
    """
    if not text:
        return "en"

    sample = text[:5000]
    cjk_count = sum(1 for ch in sample if _is_cjk(ch))
    alpha_count = sum(1 for ch in sample if ch.isascii() and ch.isalpha())
    total = cjk_count + alpha_count

    if total == 0:
        return "en"
    return "zh" if cjk_count / total > 0.15 else "en"


def _is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF  # CJK 统一表意文字
        or 0x3400 <= cp <= 0x4DBF  # CJK 扩展 A
        or 0xF900 <= cp <= 0xFAFF  # CJK 兼容表意文字
    )


def smart_truncate(text: str, max_chars: int = 80_000) -> str:
    """智能截断论文文本，保留高价值章节。

    优先保留：摘要、引言、方法、结果、结论。
    优先丢弃：参考文献、附录、致谢。
    """
    if len(text) <= max_chars:
        return text

    sections = _split_sections(text)
    low_value = {"references", "bibliography", "appendix", "acknowledgements", "acknowledgments"}

    kept: list[str] = []
    total = 0

    for title, content in sections:
        title_lower = title.lower().strip("# ").strip()
        if any(lv in title_lower for lv in low_value):
            continue
        if total + len(content) > max_chars:
            remaining = max_chars - total
            if remaining > 500:
                kept.append(content[:remaining] + "\n\n[... 章节已截断 ...]")
            break
        kept.append(content)
        total += len(content)

    result = "\n\n".join(kept)
    if not result:
        half = max_chars // 2
        result = text[:half] + "\n\n[... 内容已截断 ...]\n\n" + text[-half:]

    return result


def _split_sections(text: str) -> list[tuple[str, str]]:
    """按顶级标题拆分 Markdown 文本。"""
    heading_pattern = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
    positions = [(m.start(), m.group(1)) for m in heading_pattern.finditer(text)]

    if not positions:
        return [("", text)]

    sections = []
    for i, (pos, title) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        sections.append((title, text[pos:end]))

    if positions[0][0] > 0:
        sections.insert(0, ("preamble", text[: positions[0][0]]))

    return sections


# ---------------------------------------------------------------------------
# 语义章节分割（供多遍提取使用）
# ---------------------------------------------------------------------------

_SECTION_LABEL_MAP: dict[str, list[str]] = {
    "abstract": [
        "abstract",
        "摘要",
        "summary",
    ],
    "introduction": [
        "introduction",
        "引言",
        "背景",
        "background",
        "intro",
    ],
    "related_work": [
        "related work",
        "related works",
        "相关工作",
        "literature review",
        "prior work",
        "previous work",
    ],
    "method": [
        "method",
        "methods",
        "methodology",
        "approach",
        "model",
        "framework",
        "architecture",
        "proposed",
        "our approach",
        "方法",
        "模型",
        "框架",
        "技术方案",
    ],
    "experiments": [
        "experiment",
        "experiments",
        "results",
        "evaluation",
        "empirical",
        "analysis",
        "ablation",
        "comparison",
        "实验",
        "结果",
        "评估",
        "分析",
        "消融",
    ],
    "discussion": [
        "discussion",
        "讨论",
        "limitation",
        "limitations",
        "局限",
    ],
    "conclusion": [
        "conclusion",
        "conclusions",
        "concluding remarks",
        "future work",
        "结论",
        "总结",
        "展望",
    ],
}

_LOW_VALUE_LABELS = {"references", "appendix", "acknowledgements"}

SECTION_BUDGET: dict[str, float] = {
    "abstract": 0.10,
    "introduction": 0.15,
    "method": 0.35,
    "experiments": 0.25,
    "conclusion": 0.10,
    "other": 0.05,
}


def _classify_section(title: str) -> str:
    """将章节标题映射到语义标签。"""
    normalized = title.lower().strip("# ").strip()
    for label, keywords in _SECTION_LABEL_MAP.items():
        for kw in keywords:
            if kw in normalized:
                return label

    low_kws = [
        "reference",
        "bibliography",
        "appendix",
        "acknowledgement",
        "acknowledgment",
        "参考文献",
        "附录",
        "致谢",
    ]
    for kw in low_kws:
        if kw in normalized:
            return "references" if "refer" in normalized or "biblio" in normalized else "appendix"

    return "other"


def split_sections_with_labels(text: str) -> dict[str, str]:
    """按语义标签分割 Markdown 文本。

    返回 ``{label: content}``，同一标签的多个章节会合并。
    支持中英文标题匹配。
    """
    raw_sections = _split_sections(text)
    labeled: dict[str, list[str]] = {}

    for title, content in raw_sections:
        if not title or title == "preamble":
            label = "preamble"
        else:
            label = _classify_section(title)
        labeled.setdefault(label, []).append(content)

    return {label: "\n\n".join(parts) for label, parts in labeled.items()}


def get_section_headings(text: str) -> list[str]:
    """提取所有章节标题（保留原始格式）。"""
    heading_pattern = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
    return [m.group(1) for m in heading_pattern.finditer(text)]


def _adaptive_budget(total_text_chars: int) -> int:
    """根据论文总长度自适应调整截断上限。

    短论文（<30k）: 全量保留
    中等论文（30k-80k）: 80k 上限
    长论文（80k-150k）: 100k 上限（更多空间给方法和实验）
    超长论文（>150k）: 120k 上限
    """
    if total_text_chars <= 30_000:
        return total_text_chars
    if total_text_chars <= 80_000:
        return 80_000
    if total_text_chars <= 150_000:
        return 100_000
    return 120_000


def _adaptive_section_budget(total_text_chars: int) -> dict[str, float]:
    """根据论文长度调整各章节预算比例。

    长论文给方法和实验更多空间。
    """
    if total_text_chars > 100_000:
        return {
            "abstract": 0.08,
            "introduction": 0.12,
            "method": 0.38,
            "experiments": 0.30,
            "conclusion": 0.08,
            "other": 0.04,
        }
    return dict(SECTION_BUDGET)


def budget_truncate(
    labeled_sections: dict[str, str],
    max_chars: int = 80_000,
) -> dict[str, str]:
    """按预算比例截断各章节，保留高价值内容。

    会根据论文实际长度自适应调整截断上限和各章节比例。
    """
    for label in _LOW_VALUE_LABELS:
        labeled_sections.pop(label, None)

    total_text_chars = sum(len(c) for c in labeled_sections.values())
    total_available = _adaptive_budget(total_text_chars)
    ratios = _adaptive_section_budget(total_text_chars)

    result: dict[str, str] = {}
    for label, content in labeled_sections.items():
        budget_ratio = ratios.get(label, ratios.get("other", 0.05))
        budget_chars = int(total_available * budget_ratio)
        if len(content) <= budget_chars:
            result[label] = content
        else:
            result[label] = content[:budget_chars] + "\n\n[... 章节已截断 ...]"

    return result
