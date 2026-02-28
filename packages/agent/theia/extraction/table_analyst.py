"""Table Analyst Agent: 用 LLM 语义理解分析论文表格。

将 MinerU 解析出的 HTML <table> 转为文本网格后交给 LLM，
由 LLM 判断表格类型、提取结构化数据，再做规则后处理确保质量。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Callable

from .._utils import _parse_html_table
from ..llm.client import extract_json_from_response, robust_completion
from ..prompts.table_analyst import TABLE_ANALYST_SYSTEM, TABLE_ANALYST_USER

logger = logging.getLogger(__name__)


def _grid_to_text(grid: list[list[str]], max_col_width: int = 35) -> str:
    """把 2D 字符串网格转为 Markdown 风格的纯文本表格。"""
    if not grid:
        return ""

    n_cols = max(len(row) for row in grid)
    col_widths = [0] * n_cols
    for row in grid:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], min(len(cell), max_col_width))

    col_widths = [max(w, 3) for w in col_widths]

    lines: list[str] = []
    for row_idx, row in enumerate(grid):
        cells = []
        for i in range(n_cols):
            cell = row[i] if i < len(row) else ""
            if len(cell) > max_col_width:
                cell = cell[: max_col_width - 2] + ".."
            cells.append(cell.ljust(col_widths[i]))
        lines.append("| " + " | ".join(cells) + " |")

        if row_idx == 0:
            lines.append("| " + " | ".join("-" * w for w in col_widths) + " |")

    return "\n".join(lines)


def _prefilter_table(grid: list[list[str]], caption: str) -> bool:
    """快速预过滤：跳过明显不含实验数据的表格。

    返回 True 表示应该发给 LLM 分析，False 表示跳过。
    """
    if len(grid) < 2:
        return False

    has_any_number = False
    for row in grid[1:]:
        for cell in row:
            cleaned = cell.strip().replace("%", "").replace(",", "")
            for token in cleaned.split():
                try:
                    float(token.split("·")[0].split("×")[0])
                    has_any_number = True
                    break
                except ValueError:
                    continue
            if has_any_number:
                break
        if has_any_number:
            break

    return has_any_number


def _postprocess_analysis(analysis: dict, paper_title: str) -> dict | None:
    """对 LLM 输出做规则后处理，确保数据质量。

    返回 result_table_data 格式的字典，或 None 表示此表不需要。
    """
    if analysis.get("skip", False):
        logger.debug("LLM 判断跳过表格: %s", analysis.get("description", ""))
        return None

    table_type = analysis.get("table_type", "other")
    if table_type in ("ablation", "complexity", "hyperparameter", "other"):
        logger.debug("跳过 %s 类型表格", table_type)
        return None

    rows = analysis.get("rows", [])
    if not rows:
        return None

    skip_metrics = {
        "training cost", "flops", "params", "parameters", "steps",
        "train", "time", "gpu", "memory", "speed",
    }

    clean_rows: list[dict] = []
    for row in rows:
        method = row.get("method", "").strip()
        if not method:
            continue
        method = re.sub(r"\s*\[\d+\]", "", method)
        method = re.sub(r"\s*\(\d{4}\)", "", method)
        method = method.strip()

        values = row.get("values", {})
        filtered_values: dict[str, float | None] = {}
        for metric_name, val in values.items():
            metric_lower = metric_name.lower()
            if any(s in metric_lower for s in skip_metrics):
                continue
            if val is not None:
                try:
                    filtered_values[metric_name] = float(val)
                except (ValueError, TypeError):
                    filtered_values[metric_name] = None
            else:
                filtered_values[metric_name] = None

        has_any_value = any(v is not None for v in filtered_values.values())
        if not has_any_value:
            continue

        clean_rows.append({
            "method": method,
            "values": {k: v for k, v in filtered_values.items() if v is not None},
            "is_proposed": row.get("is_proposed", False),
        })

    if not clean_rows:
        return None

    datasets = analysis.get("datasets", [])
    metrics = [
        m for m in analysis.get("metrics", [])
        if not any(s in m.lower() for s in skip_metrics)
    ]

    best_methods = [r["method"] for r in clean_rows if r["is_proposed"]]
    best_summary = f"本文方法（{', '.join(best_methods)}）" if best_methods else ""

    return {
        "figure_path": "",
        "figure_type": "table",
        "caption": analysis.get("description", ""),
        "has_numerical_data": True,
        "table_data": {
            "column_headers": metrics,
            "rows": clean_rows,
            "datasets": datasets,
            "best_result_summary": best_summary,
        },
    }


def analyze_tables(
    content_list: list[dict],
    *,
    paper_title: str = "",
    model: str,
    api_key: str | None = None,
    api_base: str | None = None,
    max_retries: int = 2,
    on_token: Callable[[str], None] | None = None,
) -> list[dict]:
    """用 LLM 分析 content_list 中的所有表格。

    返回 result_table_data 列表，格式与 _merge_figure_results 兼容。
    """
    tables_to_analyze: list[tuple[int, str, str]] = []

    for idx, item in enumerate(content_list):
        if item.get("type") != "table":
            continue

        table_body = item.get("table_body", "")
        if not table_body:
            continue

        captions = item.get("table_caption", [])
        caption = captions[0].strip() if captions else f"Table (page {item.get('page_idx', '?')})"

        grid = _parse_html_table(table_body)
        if not _prefilter_table(grid, caption):
            logger.debug("预过滤跳过（无数值）: %s", caption[:60])
            continue

        table_text = _grid_to_text(grid)
        tables_to_analyze.append((idx, caption, table_text))

    if not tables_to_analyze:
        logger.info("content_list 中无需分析的表格")
        return []

    logger.info("Table Analyst: 准备分析 %d 个表格", len(tables_to_analyze))

    result_table_data: list[dict] = []

    for table_idx, (content_idx, caption, table_text) in enumerate(tables_to_analyze):
        logger.info("分析表格 %d/%d: %s", table_idx + 1, len(tables_to_analyze), caption[:50])

        user_content = TABLE_ANALYST_USER.format(
            paper_title=paper_title,
            table_index=table_idx + 1,
            caption=caption,
            table_text=table_text,
        )

        kwargs: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": TABLE_ANALYST_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 4096,
            "temperature": 0.0,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if api_base:
            kwargs["api_base"] = api_base

        try:
            response = robust_completion(kwargs, max_retries=max_retries, on_token=on_token)
            raw_json = extract_json_from_response(response)
            analysis = json.loads(raw_json)
        except Exception as exc:
            logger.warning("表格 %d LLM 分析失败，跳过: %s", table_idx + 1, exc)
            continue

        processed = _postprocess_analysis(analysis, paper_title)
        if processed:
            processed["caption"] = caption
            result_table_data.append(processed)
            row_count = len(processed["table_data"]["rows"])
            logger.info(
                "表格 %d 提取成功: type=%s, %d 行, datasets=%s",
                table_idx + 1,
                analysis.get("table_type"),
                row_count,
                analysis.get("datasets"),
            )
        else:
            logger.info(
                "表格 %d 被跳过: type=%s, skip=%s",
                table_idx + 1,
                analysis.get("table_type"),
                analysis.get("skip"),
            )

    logger.info(
        "Table Analyst 完成: %d/%d 个表格提取了数据",
        len(result_table_data),
        len(tables_to_analyze),
    )
    return result_table_data
