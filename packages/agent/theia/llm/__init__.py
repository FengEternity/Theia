"""LLM 交互层：统一调用接口与多模型配置。"""

from .client import extract_json_from_response, robust_completion, strip_json_fences
from .config import LLMConfig, budget_truncate, detect_language, get_section_headings, split_sections_with_labels

__all__ = [
    "LLMConfig",
    "budget_truncate",
    "detect_language",
    "extract_json_from_response",
    "get_section_headings",
    "robust_completion",
    "split_sections_with_labels",
    "strip_json_fences",
]
