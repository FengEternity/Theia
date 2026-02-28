"""基于 LLM 的论文信息提取。

使用 LiteLLM 实现与 LLM 提供商无关的调用，
支持 OpenAI、Azure、Anthropic、DeepSeek 及本地模型。

支持两种模式:
- ``single``: 单次全文提取（原有逻辑，速度快、成本低）。
- ``multi_pass``: 三遍渐进式提取（三遍阅读法，质量更高）。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from .multi_pass import _extract_multi_pass
from ..schemas import PaperSummary

logger = logging.getLogger(__name__)


def extract_paper_summary(
    markdown_content: str,
    *,
    model: str = "kimi-k2-0905-preview",
    scan_model: str | None = None,
    figure_model: str | None = None,
    images_dir: Path | None = None,
    content_list: list[dict] | None = None,
    max_tokens: int = 8192,
    temperature: float = 0.1,
    max_retries: int = 3,
    api_key: str | None = None,
    api_base: str | None = None,
    scan_api_key: str | None = None,
    scan_api_base: str | None = None,
    figure_api_key: str | None = None,
    figure_api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
    **_kwargs,
) -> PaperSummary:
    """从论文 Markdown 中提取结构化信息（三遍渐进式提取）。

    参数:
        markdown_content: MinerU 输出的论文全文 Markdown。
        model: LiteLLM 模型标识符（用于深度提取）。
        scan_model: Pass 1 快速扫描使用的轻量模型。
        figure_model: 图表分析的视觉语言模型（默认使用 *model*）。
        images_dir: 图片目录路径（用于 Pass 3 多模态图表分析）。
        content_list: MinerU 输出的结构化内容列表（JSON），用于更精确的分段。
        max_tokens: 最大响应 token 数。
        temperature: 采样温度（低 = 确定性更高）。
        max_retries: 失败重试次数。
        api_key: 深度提取 API 密钥。
        api_base: 深度提取 API base URL。
        scan_api_key: 快速扫描 API 密钥（默认使用 api_key）。
        scan_api_base: 快速扫描 API base URL（默认使用 api_base）。
        figure_api_key: 图表分析专用 API 密钥（默认使用 api_key）。
        figure_api_base: 图表分析专用 API base URL（默认使用 api_base）。

    返回:
        经过验证的 :class:`PaperSummary` 实例。
    """
    return _extract_multi_pass(
        markdown_content,
        model=model,
        scan_model=scan_model or model,
        figure_model=figure_model or model,
        images_dir=images_dir,
        content_list=content_list,
        max_tokens=max_tokens,
        temperature=temperature,
        max_retries=max_retries,
        api_key=api_key,
        api_base=api_base,
        scan_api_key=scan_api_key or api_key,
        scan_api_base=scan_api_base or api_base,
        figure_api_key=figure_api_key,
        figure_api_base=figure_api_base,
        on_token=on_token,
    )
