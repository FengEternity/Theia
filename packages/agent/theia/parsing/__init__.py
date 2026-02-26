"""输入解析：PDF 文档和网页文章的内容提取。"""

from .pdf import ParseResult, parse_pdf
from .web import article_stem, is_article_url, parse_article

__all__ = [
    "ParseResult",
    "article_stem",
    "is_article_url",
    "parse_article",
    "parse_pdf",
]
