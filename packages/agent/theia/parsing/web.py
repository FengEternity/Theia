"""网页文章解析器。

支持从微信公众号和知乎文章 URL 抓取内容，转换为 Markdown + 图片，
输出与 MinerU PDF 解析器兼容的 ``ParseResult``。

支持的平台:
- **微信公众号**: ``mp.weixin.qq.com/s/...``
- **知乎专栏**: ``zhuanlan.zhihu.com/p/...``

抓取策略（知乎，按优先级）:
0. MediaCrawler 签名抓取 — 基于 MediaCrawler 开源项目的签名算法，
   需配置 ``ZHIHU_COOKIE``（含 ``d_c0``），最可靠
1. Jina Reader API — 返回 Markdown，支持 ``JINA_API_KEY`` 提高配额，无需登录
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as md

from .pdf import ParseResult

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_WECHAT_HOST = "mp.weixin.qq.com"
_ZHIHU_HOST = "zhuanlan.zhihu.com"

SUPPORTED_HOSTS = {_WECHAT_HOST, _ZHIHU_HOST}


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------


def is_article_url(url: str) -> bool:
    """判断 URL 是否为支持的文章链接。"""
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    return host in SUPPORTED_HOSTS


def parse_article(url: str, output_dir: Path) -> ParseResult:
    """抓取网页文章并返回与 PDF 解析器相同的 ParseResult。

    参数:
        url: 文章 URL（微信公众号或知乎专栏）。
        output_dir: 输出目录，用于保存 Markdown 和下载的图片。

    返回:
        :class:`ParseResult`，包含 Markdown 文本、图片目录等。
    """
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    host = urlparse(url).hostname or ""

    if _WECHAT_HOST in host:
        return _parse_wechat(url, output_dir)
    elif _ZHIHU_HOST in host:
        return _parse_zhihu(url, output_dir)
    else:
        raise ValueError(f"不支持的文章来源: {host}，目前仅支持微信公众号和知乎专栏")


def article_stem(url: str) -> str:
    """从文章 URL 生成一个稳定的短标识符，用作文件名。"""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    host = urlparse(url).hostname or "article"
    prefix = "wx" if _WECHAT_HOST in host else "zhihu" if _ZHIHU_HOST in host else "web"
    return f"{prefix}_{url_hash}"


# ---------------------------------------------------------------------------
# 微信公众号
# ---------------------------------------------------------------------------


def _parse_wechat(url: str, output_dir: Path) -> ParseResult:
    logger.info("抓取微信公众号文章: %s", url)

    html = _fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    title_el = soup.find(id="activity-name") or soup.find("h1", class_="rich_media_title")
    if title_el:
        title = title_el.get_text(strip=True)

    author = ""
    author_el = soup.find(id="js_name") or soup.find("a", class_="rich_media_meta_link")
    if author_el:
        author = author_el.get_text(strip=True)

    content_el = soup.find(id="js_content")
    if not content_el:
        content_el = soup.find("div", class_="rich_media_content")
    if not content_el:
        raise ValueError("未能提取微信文章正文，页面结构可能已变更")

    stem = article_stem(url)
    base_dir = output_dir / stem / "web"
    images_dir = base_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    _rewrite_wechat_images(content_el, images_dir, url)

    markdown = _html_element_to_markdown(content_el, title, author, url)

    md_path = base_dir / f"{stem}.md"
    md_path.write_text(markdown, encoding="utf-8")

    logger.info(
        "微信文章解析完成: '%s', %d 字符 Markdown, %d 张图片",
        title,
        len(markdown),
        len(list(images_dir.glob("*"))) if images_dir.exists() else 0,
    )

    return ParseResult(
        markdown=markdown,
        images_dir=images_dir if any(images_dir.iterdir()) else None,
        content_list=None,
        output_dir=base_dir,
    )


def _rewrite_wechat_images(content_el: Tag, images_dir: Path, page_url: str) -> None:
    """下载微信文章图片并重写 src 为本地路径。

    微信公众号的 img 标签通常使用 data-src 属性存储真实图片 URL。
    """
    for idx, img in enumerate(content_el.find_all("img")):
        src = img.get("data-src") or img.get("src") or ""
        if not src or src.startswith("data:"):
            continue

        if not src.startswith("http"):
            src = urljoin(page_url, src)

        ext = _guess_image_ext(src)
        local_name = f"img_{idx:03d}{ext}"
        local_path = images_dir / local_name

        if _download_image(src, local_path):
            img["src"] = f"images/{local_name}"
            if img.get("data-src"):
                del img["data-src"]


# ---------------------------------------------------------------------------
# 知乎专栏
# ---------------------------------------------------------------------------


def _parse_zhihu(url: str, output_dir: Path) -> ParseResult:
    logger.info("抓取知乎专栏文章: %s", url)

    stem = article_stem(url)
    base_dir = output_dir / stem / "web"
    images_dir = base_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    title, author, content, is_markdown = _fetch_zhihu_article(url)

    if not content:
        raise ValueError("未能提取知乎文章正文")

    if is_markdown:
        markdown = _download_markdown_images(content, images_dir, url)
        header = f"# {title}\n\n" if title else ""
        if author:
            header += f"**作者**: {author}\n\n"
        header += f"**来源**: {url}\n\n---\n\n"
        markdown = header + markdown
    else:
        soup = BeautifulSoup(content, "html.parser")
        _rewrite_zhihu_images(soup, images_dir, url)
        markdown = _html_element_to_markdown(soup, title, author, url)

    md_path = base_dir / f"{stem}.md"
    md_path.write_text(markdown, encoding="utf-8")

    logger.info(
        "知乎文章解析完成: '%s', %d 字符 Markdown, %d 张图片",
        title,
        len(markdown),
        len(list(images_dir.glob("*"))) if images_dir.exists() else 0,
    )

    return ParseResult(
        markdown=markdown,
        images_dir=images_dir if any(images_dir.iterdir()) else None,
        content_list=None,
        output_dir=base_dir,
    )


def _fetch_zhihu_article(url: str) -> tuple[str, str, str, bool]:
    """通过多种策略获取知乎文章内容。

    策略优先级:
    0. MediaCrawler 签名抓取（需配置 ``ZHIHU_COOKIE``，含 ``d_c0``）
    1. Jina Reader（返回 Markdown，支持 ``JINA_API_KEY``）

    返回 (title, author, content, is_markdown)。
    ``is_markdown`` 为 True 时 content 已经是 Markdown 格式。
    """
    errors: list[str] = []

    # --- 策略 0: MediaCrawler 签名抓取（最可靠） ---
    zhihu_cookie = os.getenv("ZHIHU_COOKIE", "").strip()
    if zhihu_cookie:
        try:
            from .zhihu import fetch_zhihu_article as mc_fetch
            title, author, html = mc_fetch(url)
            return title, author, html, False
        except Exception as exc:
            errors.append(f"MediaCrawler: {exc}")
            logger.warning("MediaCrawler 签名抓取失败: %s", exc)

    # --- 策略 1: Jina Reader ---
    try:
        title, author, markdown = _fetch_zhihu_via_jina(url)
        return title, author, markdown, True
    except Exception as exc:
        errors.append(f"Jina Reader: {exc}")
        logger.debug("Jina Reader 失败: %s", exc)

    hint = ""
    if not zhihu_cookie:
        hint = (
            "\n\n提示: 设置 ZHIHU_COOKIE 环境变量可大幅提高成功率。"
            "在浏览器中登录知乎，打开 DevTools → Application → Cookies，"
            "复制完整 Cookie 字符串（需包含 d_c0）并设置到 .env 文件。"
        )
    raise RuntimeError(
        "所有知乎抓取策略均失败:\n"
        + "\n".join(f"  - {e}" for e in errors)
        + hint
    )


def _fetch_zhihu_via_jina(url: str) -> tuple[str, str, str]:
    """通过 Jina Reader API 获取知乎文章 Markdown（备用方案，可绕过反爬）。

    返回 (title, author, content_html)，其中 content_html 是包裹后的 Markdown。
    Jina Reader 直接返回 Markdown，我们用 ``<div>`` 包裹以保持接口兼容。
    """
    jina_url = f"https://r.jina.ai/{url}"
    jina_headers: dict[str, str] = {
        "Accept": "text/markdown",
        "X-Return-Format": "markdown",
    }
    jina_api_key = os.getenv("JINA_API_KEY")
    if jina_api_key:
        jina_headers["Authorization"] = f"Bearer {jina_api_key}"
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.get(
                jina_url,
                headers=jina_headers,
                timeout=60,
            )
            resp.raise_for_status()
            if "returned error 403" in resp.text or "error 403: forbidden" in resp.text.lower():
                if attempt < 2:
                    wait = 10 * (attempt + 1)
                    logger.warning("Jina Reader 返回了 403 内容 (第 %d 次)，%d 秒后重试", attempt + 1, wait)
                    time.sleep(wait)
                    last_exc = RuntimeError("Jina Reader 从知乎获得 403 Forbidden")
                    continue
                raise RuntimeError("Jina Reader 从知乎获得 403 Forbidden，该文章可能需要登录或已被限制访问")
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_exc = exc
            if attempt < 2:
                wait = 5 * (attempt + 1)
                logger.warning("Jina Reader 请求失败 (第 %d 次)，%d 秒后重试: %s", attempt + 1, wait, exc)
                time.sleep(wait)
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 403:
                last_exc = exc
                if attempt < 2:
                    wait = 10 * (attempt + 1)
                    logger.warning("Jina Reader 遇到 403 (第 %d 次)，%d 秒后重试", attempt + 1, wait)
                    time.sleep(wait)
                    continue
            raise
    else:
        raise RuntimeError(f"Jina Reader 请求失败 ({last_exc})，已重试 3 次") from last_exc

    raw_md = resp.text
    title = ""
    author = ""
    lines = raw_md.split("\n")

    cleaned_lines: list[str] = []
    in_header = True
    for i, line in enumerate(lines):
        stripped = line.strip()
        if in_header:
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                title = re.sub(r"\s*-\s*知乎$", "", title)
                in_header = False
                continue
            if i + 1 < len(lines) and re.match(r"^={3,}$", lines[i + 1].strip()) and stripped:
                title = re.sub(r"\s*-\s*知乎$", "", stripped)
                in_header = False
                continue
            if re.match(r"^={3,}$", stripped):
                continue
            if not stripped or stripped.startswith(("[", "![", "[![")):
                continue
            in_header = False

        if re.match(r"^\[.*?\]\(https?://www\.zhihu\.com/(signin|people|column|follow|hot|ring|consult|education)", stripped):
            continue
        if re.match(r"^\[.*?\]\((javascript:|https?://zhida\.zhihu\.com)", stripped):
            continue
        if stripped in ("\u200b", "切换模式", "登录/注册", "发布于", "\u200b赞同\u200b\u200b添加评论", "\u200b分享\u200b收藏\u200b喜欢"):
            continue
        if re.match(r"^\d+\s*人赞同了该文章$", stripped):
            continue
        if stripped.startswith(("首发于[", "收录于")):
            continue
        if re.match(r"^专注.*欢迎关注$", stripped):
            continue
        if stripped == "[](https://www.zhihu.com/)":
            continue
        if title and stripped == title:
            continue
        if title and re.match(r"^={3,}$", stripped):
            continue

        cleaned_lines.append(line)

    cleaned_md = "\n".join(cleaned_lines).strip()

    _zhihu_footer_markers = (
        "### 推荐阅读",
        "推荐阅读\n",
        "_想来知乎工作",
        "打开知乎App",
        "\n[广告",
        "\n[热门内容",
        "\n知乎热搜",
    )
    earliest_cut = len(cleaned_md)
    for marker in _zhihu_footer_markers:
        idx = cleaned_md.find(marker)
        if 0 < idx < earliest_cut:
            earliest_cut = idx

    trending_match = re.search(r"\n\[.+?\]\(https://www\.zhihu\.com/search\?q=.+?search_source=Trending", cleaned_md)
    if trending_match and trending_match.start() < earliest_cut:
        earliest_cut = trending_match.start()

    _tail_patterns = [
        re.compile(r"\n\u200b赞同\s*\d+"),
        re.compile(r"\n编辑于\s+\d{4}-\d{2}-\d{2}"),
        re.compile(r"\n发布于\s+\d{4}-\d{2}-\d{2}"),
    ]
    for pat in _tail_patterns:
        m = pat.search(cleaned_md)
        if m and m.start() < earliest_cut:
            earliest_cut = m.start()

    for tail_marker in ("\n关于作者\n", "\n大家都在搜\n", "\n换一换\n", "\n条评论\n"):
        idx = cleaned_md.find(tail_marker)
        if 0 < idx < earliest_cut:
            block_start = cleaned_md.rfind("\n\n", 0, idx)
            if block_start > 0:
                earliest_cut = min(earliest_cut, block_start)

    if earliest_cut < len(cleaned_md):
        cleaned_md = cleaned_md[:earliest_cut].rstrip()

    cleaned_md = re.sub(r"!\[Image \d+(?::?\s*)?", "![", cleaned_md)

    cleaned_md = re.sub(
        r"\[([^\]]+)\]\(https://zhida\.zhihu\.com/search\?[^)]+\)",
        r"\1",
        cleaned_md,
    )

    cleaned_md = re.sub(
        r"\[(?:[^\]]*广告[^\]]*|[^\]]*)\]\(https?://(?:ima\.qq\.com|sugar\.zhihu\.com)[^)]*\)",
        "",
        cleaned_md,
    )
    cleaned_md = re.sub(r"\(https?://[^)]{500,}\)", "", cleaned_md)

    cleaned_md = re.sub(r"\n{4,}", "\n\n\n", cleaned_md)

    content_len = len(cleaned_md.strip())
    if content_len < 200:
        raise RuntimeError(
            f"Jina Reader 返回的知乎文章内容过少（{content_len} 字符），"
            "该文章可能需要登录访问或内容已被删除"
        )

    logger.info("通过 Jina Reader 获取知乎文章成功: '%s'", title)
    return title, author, cleaned_md


def _rewrite_zhihu_images(content_el: Tag, images_dir: Path, page_url: str) -> None:
    """下载知乎文章图片并重写 src 为本地路径。

    知乎图片通常使用 data-original 或 data-actualsrc 属性。
    """
    for idx, img in enumerate(content_el.find_all("img")):
        src = img.get("data-original") or img.get("data-actualsrc") or img.get("src") or ""
        if not src or src.startswith("data:"):
            continue

        if not src.startswith("http"):
            src = urljoin(page_url, src)

        ext = _guess_image_ext(src)
        local_name = f"img_{idx:03d}{ext}"
        local_path = images_dir / local_name

        if _download_image(src, local_path):
            img["src"] = f"images/{local_name}"
            for attr in ("data-original", "data-actualsrc"):
                if img.get(attr):
                    del img[attr]


# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------


def _download_markdown_images(markdown: str, images_dir: Path, page_url: str) -> str:
    """下载 Markdown 中的远程图片并替换为本地路径。"""
    img_pattern = re.compile(r"!\[([^\]]*)\]\((https?://[^)]+)\)")
    idx = 0

    def _replace(m: re.Match) -> str:
        nonlocal idx
        alt = m.group(1)
        src = m.group(2)
        ext = _guess_image_ext(src)
        local_name = f"img_{idx:03d}{ext}"
        local_path = images_dir / local_name
        idx += 1
        if _download_image(src, local_path):
            return f"![{alt}](images/{local_name})"
        return m.group(0)

    return img_pattern.sub(_replace, markdown)


def _fetch_html(url: str, *, max_retries: int = 3) -> str:
    """获取网页 HTML，支持重试。"""
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except Exception as exc:
            last_exc = exc
            logger.warning("第 %d/%d 次抓取失败: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(2**attempt)

    raise RuntimeError(f"抓取网页失败（{max_retries} 次尝试后）: {last_exc}") from last_exc


def _download_image(url: str, dest: Path, *, timeout: int = 15) -> bool:
    """下载单张图片到本地。"""
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT, "Referer": url},
            stream=True,
        )
        resp.raise_for_status()
        with dest.open("wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return dest.stat().st_size > 100
    except Exception as exc:
        logger.debug("图片下载失败 %s: %s", url, exc)
        if dest.exists():
            dest.unlink(missing_ok=True)
        return False


def _guess_image_ext(url: str) -> str:
    """根据 URL 推断图片扩展名。"""
    path = urlparse(url).path.lower()
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
        if ext in path:
            return ext
    return ".jpg"


def _html_element_to_markdown(content_el: Tag, title: str, author: str, source_url: str) -> str:
    """将 HTML 元素转换为 Markdown，并添加元信息头。"""
    body_md = md(str(content_el), heading_style="ATX", strip=["script", "style", "noscript"])

    body_md = re.sub(r"\n{3,}", "\n\n", body_md).strip()

    header = f"# {title}\n\n" if title else ""
    if author:
        header += f"**作者**: {author}\n\n"
    header += f"**来源**: {source_url}\n\n---\n\n"

    return header + body_md
