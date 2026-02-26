"""基于 MediaCrawler 的知乎文章抓取模块。

使用 MediaCrawler (https://github.com/NanmiCoder/MediaCrawler) 的签名算法
和内容提取逻辑来获取知乎专栏文章。

前置条件:
- Node.js 运行时 (用于执行签名 JS)
- ``ZHIHU_COOKIE`` 环境变量（包含 ``d_c0`` 的完整 Cookie 字符串）

使用方法::

    from theia.parsing.zhihu import fetch_zhihu_article

    title, author, html_content = fetch_zhihu_article(
        "https://zhuanlan.zhihu.com/p/123456789"
    )
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode, urlparse

import execjs
import requests
from parsel import Selector

logger = logging.getLogger(__name__)

_VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor" / "MediaCrawler"
_ZHIHU_JS_PATH = _VENDOR_DIR / "libs" / "zhihu.js"

_ZHIHU_URL = "https://www.zhihu.com"
_ZHIHU_ZHUANLAN_URL = "https://zhuanlan.zhihu.com"

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

_COMPILED_JS: execjs.ExternalRuntime.Context | None = None  # type: ignore[name-defined]


# ---------------------------------------------------------------------------
# 签名
# ---------------------------------------------------------------------------


def _get_js_ctx() -> execjs.ExternalRuntime.Context:  # type: ignore[name-defined]
    """延迟编译 zhihu.js，首次调用时加载。"""
    global _COMPILED_JS  # noqa: PLW0603
    if _COMPILED_JS is None:
        if not _ZHIHU_JS_PATH.exists():
            raise FileNotFoundError(
                f"未找到 MediaCrawler 签名脚本: {_ZHIHU_JS_PATH}\n"
                "请确认 vendor/MediaCrawler 已正确克隆。"
            )
        _COMPILED_JS = execjs.compile(_ZHIHU_JS_PATH.read_text(encoding="utf-8-sig"))
    return _COMPILED_JS


def _sign(uri: str, cookie_str: str) -> Dict[str, str]:
    """调用 MediaCrawler 的 zhihu.js 计算请求签名。

    返回包含 ``x-zst-81`` 和 ``x-zse-96`` 的字典。
    """
    ctx = _get_js_ctx()
    return ctx.call("get_sign", uri, cookie_str)


def _build_headers(uri: str, cookie_str: str) -> Dict[str, str]:
    """构建一组完整的已签名请求头。"""
    sign_result = _sign(uri, cookie_str)
    return {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "cookie": cookie_str,
        "referer": f"{_ZHIHU_ZHUANLAN_URL}{uri}",
        "user-agent": _USER_AGENT,
        "x-api-version": "3.0.91",
        "x-app-za": "OS=Web",
        "x-requested-with": "fetch",
        "x-zse-93": "101_3_3.0",
        "x-zst-81": sign_result["x-zst-81"],
        "x-zse-96": sign_result["x-zse-96"],
    }


# ---------------------------------------------------------------------------
# 内容提取（移植自 MediaCrawler ZhihuExtractor）
# ---------------------------------------------------------------------------


def _extract_article_from_html(html: str) -> Optional[Tuple[str, str, str]]:
    """从知乎文章页面 HTML 的 SSR 数据中提取文章内容。

    返回 (title, author, content_html) 或 None。
    """
    js_init_data = (
        Selector(text=html)
        .xpath("//script[@id='js-initialData']/text()")
        .get(default="")
        .strip()
    )
    if not js_init_data:
        return None

    try:
        data = json.loads(js_init_data)
    except json.JSONDecodeError:
        return None

    articles: Dict = (
        data.get("initialState", {}).get("entities", {}).get("articles", {})
    )
    if not articles:
        return None

    article = next(iter(articles.values()))
    title = _strip_html(article.get("title", ""))
    author_info = article.get("author", {})
    author = author_info.get("name", "") if isinstance(author_info, dict) else ""
    content_html = article.get("content", "")

    if not content_html:
        return None

    return title, author, content_html


def _strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL)
    return re.sub(r"<[^>]+>", "", clean).strip()


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------


def fetch_zhihu_article(url: str) -> Tuple[str, str, str]:
    """抓取知乎专栏文章，返回 (title, author, content_html)。

    需要在环境变量 ``ZHIHU_COOKIE`` 中设置包含 ``d_c0`` 的完整 Cookie。

    Raises:
        RuntimeError: Cookie 未配置或抓取失败。
        FileNotFoundError: MediaCrawler 签名脚本不存在。
    """
    cookie_str = os.getenv("ZHIHU_COOKIE", "").strip()
    if not cookie_str:
        raise RuntimeError(
            "ZHIHU_COOKIE 环境变量未设置。\n"
            "请在浏览器中登录知乎，打开 DevTools → Application → Cookies，"
            "复制完整 Cookie 字符串并设置到 .env 文件中。"
        )

    if "d_c0" not in cookie_str:
        raise RuntimeError(
            "ZHIHU_COOKIE 中缺少 d_c0 字段，签名将失败。\n"
            "请确保从浏览器中复制了完整的 Cookie 字符串。"
        )

    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")
    article_id = path_parts[-1] if path_parts else ""
    uri = f"/p/{article_id}"

    logger.info("使用 MediaCrawler 签名机制抓取知乎文章: %s", url)

    headers = _build_headers(uri, cookie_str)

    resp = requests.get(
        f"{_ZHIHU_ZHUANLAN_URL}{uri}",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()

    if resp.status_code == 403:
        raise RuntimeError(
            "知乎返回 403，Cookie 可能已过期。请重新获取 ZHIHU_COOKIE。"
        )

    result = _extract_article_from_html(resp.text)
    if not result:
        if len(resp.text) < 2000:
            raise RuntimeError(
                f"未能从页面提取文章内容。响应可能是反爬页面 "
                f"(长度={len(resp.text)})。Cookie 可能已过期。"
            )
        raise RuntimeError("页面已获取但未找到文章 SSR 数据，页面结构可能已变更。")

    title, author, content_html = result
    logger.info("MediaCrawler 抓取成功: '%s' by %s", title, author or "未知")
    return title, author, content_html
