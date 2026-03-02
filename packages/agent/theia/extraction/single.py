"""单次全文提取：用一次 LLM 调用完成论文信息提取（速度快、成本低）。"""

from __future__ import annotations

import json
import logging
import time
from typing import Callable

from pydantic import ValidationError

from ..llm.client import extract_json_from_response, robust_completion
from ..prompts.extraction_single import EXTRACTION_SYSTEM_PROMPT, FEW_SHOT_EXAMPLE
from ..schemas import PaperSummary

logger = logging.getLogger(__name__)

_MAX_CONTENT_CHARS = 80_000


def _extract_single_pass(
    markdown_content: str,
    *,
    model: str,
    max_tokens: int = 8192,
    temperature: float = 0.1,
    max_retries: int = 3,
    api_key: str | None = None,
    api_base: str | None = None,
    on_token: Callable[[str], None] | None = None,
) -> PaperSummary:
    """单次 LLM 调用完成论文信息提取。

    比三遍阅读法快约 3-5 倍，适合对速度要求高的场景。
    """
    logger.info("=" * 40)
    logger.info("单次提取模式（单轮）")
    logger.info("=" * 40)

    if len(markdown_content) > _MAX_CONTENT_CHARS:
        content = markdown_content[:_MAX_CONTENT_CHARS] + "\n\n[... 内容已截断 ...]"
        logger.info("内容已截断至 %d 字符（原始 %d 字符）", _MAX_CONTENT_CHARS, len(markdown_content))
    else:
        content = markdown_content

    user_prompt = f"{FEW_SHOT_EXAMPLE}\n\n---\n\n以下是需要提取的论文：\n\n{content}"

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            req: dict = {
                "model": model,
                "messages": [
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if api_key:
                req["api_key"] = api_key
            if api_base:
                req["api_base"] = api_base

            t0 = time.time()
            response = robust_completion(req, on_token=on_token)
            elapsed = time.time() - t0

            raw = extract_json_from_response(response)
            data = json.loads(raw)
            summary = PaperSummary.model_validate(data)
            logger.info(
                "单次提取完成 (%.1fs): '%s', authors=%d, baselines=%d, formulas=%d",
                elapsed,
                summary.title,
                len(summary.authors),
                len(summary.results.baselines) if summary.results else 0,
                len(summary.method.formulas) if summary.method else 0,
            )
            return summary

        except (ValidationError, ValueError, KeyError) as exc:
            last_error = exc
            logger.warning("提取尝试 %d/%d 失败: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"单次提取失败（已重试 {max_retries} 次）: {last_error}") from last_error
