"""流水线节点共享的内部工具函数。"""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def pdf_stem(pdf_input: str) -> str:
    """从本地路径或 URL 中提取文件名（不含扩展名）。

    对于网页文章 URL（微信公众号、知乎），使用 ``web_parser.article_stem``
    生成稳定的短标识符。
    """
    if pdf_input.startswith("http://") or pdf_input.startswith("https://"):
        from .parsing.web import article_stem, is_article_url

        if is_article_url(pdf_input):
            return article_stem(pdf_input)
        return Path(urlparse(pdf_input).path).stem or "document"
    return Path(pdf_input).stem


def extract_figures_from_markdown(markdown: str) -> list[dict]:
    """从 Markdown 中提取图片引用及其上下文信息。

    返回包含 path、caption、context 的字典列表，
    context 用于将图片匹配到对应的视频场景。
    """
    figures: list[dict] = []
    lines = markdown.split("\n")

    img_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    for i, line in enumerate(lines):
        for match in img_pattern.finditer(line):
            alt_text = match.group(1)
            img_path = match.group(2)

            context_start = max(0, i - 10)
            context_end = min(len(lines), i + 5)
            context = "\n".join(lines[context_start:context_end]).lower()

            scene_type = _guess_scene_type(context)

            caption = alt_text or _extract_caption(lines, i)

            figures.append(
                {
                    "path": img_path,
                    "caption": caption,
                    "context": context[:200],
                    "scene_type": scene_type,
                    "line_number": i,
                }
            )

    return figures


def _extract_caption(lines: list[str], img_line: int) -> str:
    """从图片附近的文本提取标题说明。

    查找图片上下 3 行中包含 'Figure'、'Fig.'、'图' 等关键词的行。
    """
    caption_pattern = re.compile(r"(?:Figure|Fig\.|图)\s*\d+", re.IGNORECASE)
    for offset in range(1, 4):
        for idx in [img_line + offset, img_line - offset]:
            if 0 <= idx < len(lines):
                line = lines[idx].strip()
                if caption_pattern.search(line) and len(line) > 10:
                    return line[:200]
    return ""


def _guess_scene_type(context: str) -> str:
    """根据图片周围的文本上下文推测其所属场景类型。"""
    method_keywords = [
        "method",
        "approach",
        "model",
        "architecture",
        "network",
        "encoder",
        "decoder",
        "方法",
        "模型",
        "架构",
        "网络",
        "编码器",
        "解码器",
    ]
    result_keywords = [
        "result",
        "experiment",
        "table",
        "performance",
        "accuracy",
        "bleu",
        "结果",
        "实验",
        "性能",
        "准确率",
    ]
    overview_keywords = ["abstract", "introduction", "overview", "background", "摘要", "引言", "概述", "背景"]

    for kw in method_keywords:
        if kw in context:
            return "method"
    for kw in result_keywords:
        if kw in context:
            return "result"
    for kw in overview_keywords:
        if kw in context:
            return "overview"
    return "method"


# ---------------------------------------------------------------------------
# HTML <table> → 结构化数据
# ---------------------------------------------------------------------------

class _TableHTMLParser(HTMLParser):
    """解析 MinerU 输出的 <table> HTML，正确处理 colspan/rowspan。"""

    def __init__(self) -> None:
        super().__init__()
        self._raw_rows: list[list[tuple[str, int, int]]] = []
        self._current_row: list[tuple[str, int, int]] = []
        self._current_cell: list[str] = []
        self._in_cell = False
        self._cell_colspan = 1
        self._cell_rowspan = 1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in ("td", "th"):
            self._in_cell = True
            self._current_cell = []
            self._cell_colspan = 1
            self._cell_rowspan = 1
            for attr_name, attr_val in attrs:
                if attr_name == "colspan" and attr_val:
                    try:
                        self._cell_colspan = int(attr_val)
                    except ValueError:
                        pass
                elif attr_name == "rowspan" and attr_val:
                    try:
                        self._cell_rowspan = int(attr_val)
                    except ValueError:
                        pass

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th"):
            self._in_cell = False
            text = "".join(self._current_cell).strip()
            self._current_row.append((text, self._cell_colspan, self._cell_rowspan))
        elif tag == "tr":
            if self._current_row:
                self._raw_rows.append(self._current_row)

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)

    def resolve_grid(self) -> list[list[str]]:
        """将含 colspan/rowspan 的原始行展开为规则的二维网格。"""
        if not self._raw_rows:
            return []

        max_cols = max(
            sum(cs for _, cs, _ in row) for row in self._raw_rows
        )
        n_rows = len(self._raw_rows)

        grid: list[list[str | None]] = [[None] * max_cols for _ in range(n_rows + 10)]

        for row_idx, raw_row in enumerate(self._raw_rows):
            col_cursor = 0
            for text, colspan, rowspan in raw_row:
                while col_cursor < max_cols and grid[row_idx][col_cursor] is not None:
                    col_cursor += 1
                for dr in range(rowspan):
                    for dc in range(colspan):
                        r, c = row_idx + dr, col_cursor + dc
                        if r < len(grid) and c < max_cols:
                            grid[r][c] = text
                col_cursor += colspan

        result: list[list[str]] = []
        for row_idx in range(n_rows):
            row = [cell if cell is not None else "" for cell in grid[row_idx][:max_cols]]
            result.append(row)
        return result


def _parse_html_table(html: str) -> list[list[str]]:
    """将 HTML <table> 解析为二维字符串数组，正确处理 colspan/rowspan。"""
    parser = _TableHTMLParser()
    parser.feed(html)
    return parser.resolve_grid()
