"""三层论文提取质量评估框架。

L1: 规则检查（确定性，< 1ms）
L2: NLP 指标（文本分析，< 100ms）
L3: LLM-as-Judge（API 调用，~10s）

正常流水线仅运行 L1+L2（免费快速，满分 6.0）。
对比测试运行 L1+L2+L3（满分 10.0）。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from ..llm.client import robust_completion
from ..prompts.evaluator_judge import JUDGE_PROMPT, JUDGE_SYSTEM
from ..schemas import PaperSummary

logger = logging.getLogger(__name__)


# ===================================================================
# 分数数据结构
# ===================================================================


@dataclass
class L1Score:
    schema_compliance: float = 0.0
    field_completeness: float = 0.0
    numeric_verifiability: float = 0.0

    @property
    def total(self) -> float:
        return self.schema_compliance + self.field_completeness + self.numeric_verifiability

    @property
    def max_total(self) -> float:
        return 2.0

    def detail(self) -> dict[str, float]:
        return {
            "schema_compliance": round(self.schema_compliance, 3),
            "field_completeness": round(self.field_completeness, 3),
            "numeric_verifiability": round(self.numeric_verifiability, 3),
            "l1_total": round(self.total, 3),
        }


@dataclass
class L2Score:
    grounding: float = 0.0
    entity_match: float = 0.0
    section_coverage: float = 0.0
    diversity: float = 0.0
    information_density: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.grounding
            + self.entity_match
            + self.section_coverage
            + self.diversity
            + self.information_density
        )

    @property
    def max_total(self) -> float:
        return 4.5

    def detail(self) -> dict[str, float]:
        return {
            "grounding": round(self.grounding, 3),
            "entity_match": round(self.entity_match, 3),
            "section_coverage": round(self.section_coverage, 3),
            "diversity": round(self.diversity, 3),
            "information_density": round(self.information_density, 3),
            "l2_total": round(self.total, 3),
        }


@dataclass
class L3Score:
    faithfulness: float = 0.0
    coverage: float = 0.0
    insight: float = 0.0
    video_ready: float = 0.0
    issues: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def total(self) -> float:
        return self.faithfulness + self.coverage + self.insight + self.video_ready

    @property
    def max_total(self) -> float:
        return 4.0

    def detail(self) -> dict[str, Any]:
        return {
            "faithfulness": round(self.faithfulness, 3),
            "coverage": round(self.coverage, 3),
            "insight": round(self.insight, 3),
            "video_ready": round(self.video_ready, 3),
            "l3_total": round(self.total, 3),
            "issues": self.issues,
            "missing": self.missing,
            "notes": self.notes,
        }


@dataclass
class EvalResult:
    l1: L1Score
    l2: L2Score
    l3: L3Score | None = None

    @property
    def fast_total(self) -> float:
        return self.l1.total + self.l2.total

    @property
    def full_total(self) -> float:
        return self.l1.total + self.l2.total + (self.l3.total if self.l3 else 0.0)

    @property
    def max_total(self) -> float:
        base = self.l1.max_total + self.l2.max_total
        return base + self.l3.max_total if self.l3 else base

    def detail(self) -> dict[str, Any]:
        d: dict[str, Any] = {**self.l1.detail(), **self.l2.detail()}
        if self.l3:
            d.update(self.l3.detail())
        d["fast_total"] = round(self.fast_total, 2)
        if self.l3:
            d["full_total"] = round(self.full_total, 2)
        return d


# ===================================================================
# 文本工具
# ===================================================================

_STOP_WORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "are",
        "was",
        "were",
        "been",
        "have",
        "has",
        "had",
        "not",
        "but",
        "also",
        "can",
        "our",
        "their",
        "which",
        "each",
        "into",
        "more",
        "than",
        "other",
        "based",
        "using",
        "used",
        "proposed",
        "method",
        "model",
        "results",
        "show",
        "paper",
        "approach",
        "performance",
        "data",
        "task",
    }
)

_CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_EN_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9\-]{3,}")
_NUMBER_RE = re.compile(r"-?\d+\.?\d*%?")


def _extract_key_terms(text: str) -> list[str]:
    """提取中英文关键术语。"""
    en_words = [w for w in _EN_WORD_RE.findall(text) if w.lower() not in _STOP_WORDS]
    cn_phrases = _CJK_RE.findall(text)
    return en_words + cn_phrases


def _extract_numbers(text: str) -> list[str]:
    """提取文本中的数值（含百分号）。"""
    return _NUMBER_RE.findall(text)


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(len(a | b), 1)


def _ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    """生成 n-gram 集合。"""
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _soft_grounding(claim_text: str, section_text: str) -> float:
    """基于 bigram 重叠的软溯源评分 (0.0-1.0)。

    综合考虑：
    - unigram 精确匹配（权重 0.4）
    - bigram 重叠率（权重 0.6，捕获短语级别一致性）
    """
    claim_terms = [t.lower() for t in _extract_key_terms(claim_text)]
    if not claim_terms:
        return 0.0

    section_lower = section_text.lower()
    section_words = [w.lower() for w in _EN_WORD_RE.findall(section_text)]

    uni_found = sum(1 for t in claim_terms if t in section_lower)
    uni_ratio = uni_found / len(claim_terms) if claim_terms else 0.0

    claim_bigrams = _ngrams(claim_terms, 2)
    section_bigrams = _ngrams(section_words, 2)
    if claim_bigrams:
        bi_overlap = len(claim_bigrams & section_bigrams)
        bi_ratio = bi_overlap / len(claim_bigrams)
    else:
        bi_ratio = uni_ratio

    return 0.4 * uni_ratio + 0.6 * bi_ratio


# ===================================================================
# ExtractionEvaluator
# ===================================================================


class ExtractionEvaluator:
    """三层论文提取质量评估器。"""

    def __init__(
        self,
        original_text: str,
        labeled_sections: dict[str, str] | None = None,
    ):
        self._original = original_text
        self._original_lower = original_text.lower()
        if labeled_sections is None:
            from ..llm.config import split_sections_with_labels

            labeled_sections = split_sections_with_labels(original_text)
        self._sections = labeled_sections

    def _get_section(self, hint: str) -> str:
        """获取指定语义标签的章节文本，hint="any" 返回全文。"""
        if hint == "any":
            return self._original
        return self._sections.get(hint, "")

    # ---------------------------------------------------------------
    # L1: 规则检查 (满分 2.0)
    # ---------------------------------------------------------------

    def evaluate_l1(self, summary: PaperSummary) -> L1Score:
        s = L1Score()

        # Schema 合规 (0-0.5): 必填字段类型正确
        checks = [
            isinstance(summary.title, str) and len(summary.title) > 0,
            isinstance(summary.problem, str) and len(summary.problem) > 0,
            isinstance(summary.method.summary, str) and len(summary.method.summary) > 0,
            isinstance(summary.conclusion, str) and len(summary.conclusion) > 0,
            isinstance(summary.method.key_steps, list),
            isinstance(summary.results.metrics, list),
            isinstance(summary.results.baselines, list),
            all(isinstance(b.value, (int, float)) for b in summary.results.baselines),
        ]
        s.schema_compliance = 0.5 * (sum(checks) / max(len(checks), 1))

        # 字段完整性 (0-1.0)
        comp = 0.0
        if summary.title and len(summary.title) > 5:
            comp += 0.1
        if len(summary.authors) >= 1:
            comp += 0.05
        if summary.problem and len(summary.problem) > 20:
            comp += 0.1
        if summary.method.summary and len(summary.method.summary) > 40:
            comp += 0.15
        if len(summary.method.key_steps) >= 3:
            comp += 0.1
        if len(summary.method.key_steps) >= 5:
            comp += 0.05
        if len(summary.method.formulas) >= 1:
            comp += 0.05
        if len(summary.results.datasets) >= 1:
            comp += 0.05
        if len(summary.results.metrics) >= 1:
            comp += 0.1
        if len(summary.results.baselines) >= 1:
            comp += 0.05
        if summary.results.findings and len(summary.results.findings) > 30:
            comp += 0.1
        if summary.conclusion and len(summary.conclusion) > 20:
            comp += 0.05
        if len(summary.contributions) >= 2:
            comp += 0.05
        s.field_completeness = min(comp, 1.0)

        # 数值可验证性 (0-0.5): 提取的数字是否出现在原文中
        all_numbers: list[str] = []
        for m in summary.results.metrics:
            all_numbers.extend(_extract_numbers(m))
        for b in summary.results.baselines:
            all_numbers.append(str(b.value))
            clean = str(b.value).rstrip("0").rstrip(".")
            if clean != str(b.value):
                all_numbers.append(clean)

        if all_numbers:
            found = sum(1 for n in all_numbers if n in self._original)
            s.numeric_verifiability = 0.5 * (found / len(all_numbers))
        else:
            s.numeric_verifiability = 0.15

        return s

    # ---------------------------------------------------------------
    # L2: NLP 指标 (满分 4.5)
    # ---------------------------------------------------------------

    def evaluate_l2(self, summary: PaperSummary) -> L2Score:
        s = L2Score()

        s.grounding = self._grounding_score(summary)
        s.entity_match = self._entity_match_score(summary)
        s.section_coverage = self._section_coverage_score(summary)
        s.diversity = self._diversity_score(summary)
        s.information_density = self._information_density_score(summary)

        return s

    def _grounding_score(self, summary: PaperSummary) -> float:
        """事实锚定率 (0-1.5): 声明是否在原文对应章节有依据。

        使用 bigram 重叠的软匹配，比精确术语匹配更鲁棒。
        每条声明获得 0-1 的连续溯源分数（而非二元判定），
        最终取所有声明的平均分。
        """
        claims: list[tuple[str, str]] = []

        for step in summary.method.key_steps:
            claims.append(("method", step))

        for metric in summary.results.metrics:
            claims.append(("experiments", metric))

        for c in summary.contributions:
            claims.append(("any", c))

        if not claims:
            return 0.0

        total_score = 0.0
        for section_hint, claim_text in claims:
            search_text = self._get_section(section_hint)
            if not search_text:
                search_text = self._original
            total_score += _soft_grounding(claim_text, search_text)

        avg = total_score / len(claims)
        return round(1.5 * avg, 3)

    def _entity_match_score(self, summary: PaperSummary) -> float:
        """实体匹配度 (0-1.0): 命名实体是否出现在原文。"""
        entities: list[str] = []

        if summary.title:
            first_words = summary.title.split()[:5]
            entities.append(" ".join(first_words).lower())

        for a in summary.authors[:5]:
            normalized = a.strip().split()[-1].lower() if a.strip() else ""
            if len(normalized) > 2:
                entities.append(normalized)

        for ds in summary.results.datasets:
            entities.append(ds.lower())

        for b in summary.results.baselines:
            if len(b.name) > 2:
                entities.append(b.name.lower())

        if not entities:
            return 0.3

        found = sum(1 for e in entities if e in self._original_lower)
        ratio = found / len(entities)
        return round(1.0 * ratio, 3)

    def _section_coverage_score(self, summary: PaperSummary) -> float:
        """章节覆盖率 (0-1.0): 提取结果是否从各章节捕获信息。"""
        coverage_checks: list[tuple[str, str]] = [
            ("introduction", summary.problem),
            ("method", summary.method.summary),
            ("experiments", summary.results.findings),
            ("conclusion", summary.conclusion),
        ]

        covered = 0
        total = 0
        for section_label, extracted_text in coverage_checks:
            section_text = self._get_section(section_label)
            if not section_text:
                continue
            total += 1
            if not extracted_text:
                continue
            extracted_terms = set(t.lower() for t in _extract_key_terms(extracted_text))
            section_terms = set(t.lower() for t in _extract_key_terms(section_text[:8000]))
            overlap = len(extracted_terms & section_terms)
            min_overlap = 1 if len(extracted_terms) < 8 else 2
            if overlap >= min_overlap:
                covered += 1

        if total == 0:
            return 0.5
        return round(1.0 * (covered / total), 3)

    def _diversity_score(self, summary: PaperSummary) -> float:
        """多样性检查 (0-0.5): 贡献与步骤的多样性。"""
        score = 0.0

        if len(summary.contributions) >= 2:
            word_sets = [set(c.lower().split()) for c in summary.contributions]
            overlaps = []
            for i, s1 in enumerate(word_sets):
                for s2 in word_sets[i + 1 :]:
                    overlaps.append(_jaccard(s1, s2))
            avg_overlap = sum(overlaps) / max(len(overlaps), 1)
            score += 0.25 * (1.0 - min(avg_overlap / 0.5, 1.0))

        if len(summary.method.key_steps) >= 2:
            step_sets = [set(s.lower().split()) for s in summary.method.key_steps]
            overlaps = []
            for i, s1 in enumerate(step_sets):
                for s2 in step_sets[i + 1 :]:
                    overlaps.append(_jaccard(s1, s2))
            avg_overlap = sum(overlaps) / max(len(overlaps), 1)
            score += 0.25 * (1.0 - min(avg_overlap / 0.5, 1.0))

        return round(min(score, 0.5), 3)

    def _information_density_score(self, summary: PaperSummary) -> float:
        """信息密度 (0-0.5): 检测字段内容是否有实质性信息。

        评估标准：
        - 关键字段长度是否达到最低阈值（过短=空泛）
        - key_steps 中的步骤是否包含技术术语（排除纯自然语言描述）
        - method.summary 中是否包含领域特定名词
        """
        score = 0.0

        # 关键字段最低长度检查 (0-0.2)
        length_checks = [
            (summary.problem, 80),
            (summary.method.summary, 80),
            (summary.results.findings, 60),
            (summary.conclusion, 60),
        ]
        passed = sum(1 for text, min_len in length_checks if text and len(text) >= min_len)
        score += 0.2 * (passed / max(len(length_checks), 1))

        # key_steps 技术术语密度 (0-0.15)
        if summary.method.key_steps:
            steps_with_terms = 0
            for step in summary.method.key_steps:
                terms = _extract_key_terms(step)
                if len(terms) >= 2:
                    steps_with_terms += 1
            ratio = steps_with_terms / len(summary.method.key_steps)
            score += 0.15 * ratio

        # contributions 信息量 (0-0.15)
        if summary.contributions:
            informative = 0
            for c in summary.contributions:
                terms = _extract_key_terms(c)
                if len(terms) >= 3 and len(c) >= 40:
                    informative += 1
            ratio = informative / len(summary.contributions)
            score += 0.15 * ratio

        return round(min(score, 0.5), 3)

    # ---------------------------------------------------------------
    # L3: LLM-as-Judge (满分 4.0)
    # ---------------------------------------------------------------

    def evaluate_l3(
        self,
        summary: PaperSummary,
        *,
        judge_model: str = "openai/gpt-5.2-chat",
        judge_api_key: str | None = None,
        judge_api_base: str | None = None,
        on_token: Callable[[str], None] | None = None,
    ) -> L3Score:
        """使用 LLM 做深度评估。同步调用。"""
        context = self._build_judge_context()
        extraction_json = summary.model_dump_json(indent=2)

        prompt = JUDGE_PROMPT.format(
            paper_context=context,
            extraction_json=extraction_json,
        )

        kwargs: dict[str, Any] = {
            "model": judge_model,
            "messages": [
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        }
        if judge_api_key:
            kwargs["api_key"] = judge_api_key
        if judge_api_base:
            kwargs["api_base"] = judge_api_base

        try:
            resp = robust_completion(kwargs, on_token=on_token)
        except Exception as exc:
            logger.warning("L3 Judge 调用失败: %s", exc)
            return L3Score(notes=f"Judge 调用失败: {exc}")

        return self._parse_judge_response(resp.choices[0].message.content or "")

    def _build_judge_context(self) -> str:
        """从原文中抽取关键章节给 Judge，控制在 ~15K 字符。"""
        parts: list[str] = []
        budget_per_section = 3500

        for label in ("abstract", "introduction", "method", "experiments", "conclusion"):
            text = self._get_section(label)
            if text:
                truncated = text[:budget_per_section]
                if len(text) > budget_per_section:
                    truncated += "\n[...已截断...]"
                parts.append(f"=== {label.upper()} ===\n{truncated}")

        return "\n\n".join(parts)

    def _parse_judge_response(self, raw: str) -> L3Score:
        """宽容解析 Judge 的 JSON 输出。"""
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        raw = raw.strip()
        if raw.startswith("```"):
            first_nl = raw.index("\n") if "\n" in raw else 3
            raw = raw[first_nl + 1 :]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Judge 返回了无效 JSON")
            return L3Score(notes="Judge 返回了无效 JSON")

        def _get_dim_score(key: str) -> float:
            v = data.get(key, {})
            if isinstance(v, dict):
                return float(v.get("score", 0))
            if isinstance(v, (int, float)):
                return float(v)
            return 0.0

        s = L3Score()
        s.faithfulness = min(_get_dim_score("faithfulness"), 1.0)
        s.coverage = min(_get_dim_score("coverage"), 1.0)
        s.insight = min(_get_dim_score("insight"), 1.0)
        s.video_ready = min(_get_dim_score("video_ready"), 1.0)

        if isinstance(data.get("faithfulness"), dict):
            s.issues = data["faithfulness"].get("issues", [])
        if isinstance(data.get("coverage"), dict):
            s.missing = data["coverage"].get("missing", [])
        notes_parts = []
        for key in ("insight", "video_ready"):
            v = data.get(key, {})
            if isinstance(v, dict) and v.get("notes"):
                notes_parts.append(f"{key}: {v['notes']}")
        s.notes = "; ".join(notes_parts)

        return s

    # ---------------------------------------------------------------
    # 组合 API
    # ---------------------------------------------------------------

    def evaluate_fast(self, summary: PaperSummary) -> EvalResult:
        """L1 + L2 快速评估（免费，< 100ms），用于正常流水线。"""
        return EvalResult(
            l1=self.evaluate_l1(summary),
            l2=self.evaluate_l2(summary),
        )

    def evaluate_full(
        self,
        summary: PaperSummary,
        *,
        judge_model: str = "openai/gpt-5.2-chat",
        judge_api_key: str | None = None,
        judge_api_base: str | None = None,
    ) -> EvalResult:
        """L1 + L2 + L3 全量评估，用于对比测试。"""
        l1 = self.evaluate_l1(summary)
        l2 = self.evaluate_l2(summary)
        l3 = self.evaluate_l3(
            summary,
            judge_model=judge_model,
            judge_api_key=judge_api_key,
            judge_api_base=judge_api_base,
        )
        return EvalResult(l1=l1, l2=l2, l3=l3)
