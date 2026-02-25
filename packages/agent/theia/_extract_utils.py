"""提取模块共用的常量和工具函数。"""

from __future__ import annotations

_SECTION_PROCESS_ORDER = [
    "preamble",
    "abstract",
    "introduction",
    "related_work",
    "method",
    "experiments",
    "discussion",
    "conclusion",
    "other",
]

_SECTION_LABELS_ZH = {
    "preamble": "前言",
    "abstract": "摘要",
    "introduction": "引言",
    "related_work": "相关工作",
    "method": "方法",
    "experiments": "实验与结果",
    "discussion": "讨论",
    "conclusion": "结论",
    "other": "其他",
}

_HIGH_VALUE_SECTIONS = {"method", "experiments"}


def _estimate_tokens(text: str) -> int:
    """粗略估算文本 token 数（英文约4字符/token，中文约1.5字符/token）。"""
    if not text:
        return 0
    sample = text[:2000]
    cjk = sum(1 for ch in sample if 0x4E00 <= ord(ch) <= 0x9FFF)
    ratio = cjk / max(len(sample), 1)
    chars_per_token = 1.5 * ratio + 4.0 * (1 - ratio)
    return int(len(text) / max(chars_per_token, 1))
