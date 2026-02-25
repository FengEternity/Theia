"""MinerU PDF 解析包装器。

支持两种模式：
- **本地模式**: 使用已安装的 ``mineru`` Python 包（GPU/CPU）。
- **云端模式**: 调用 mineru.net REST API（无需本地 GPU）。

在环境变量中设置 ``MINERU_API_KEY`` 即可启用云端模式。
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
import zipfile
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

BACKEND_SUBDIRS = {
    "pipeline": "pipeline",
    "hybrid-auto-engine": "hybrid_auto",
    "vlm-auto-engine": "vlm_auto",
}

CLOUD_API_BASE = "https://mineru.net/api/v4"


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------


def parse_pdf(
    pdf_path: str | Path,
    output_dir: Path,
    *,
    lang: str = "ch",
    backend: str = "pipeline",
) -> ParseResult:
    """解析 PDF 并返回结构化内容。

    当设置了 ``MINERU_API_KEY`` 时，自动使用云端 API；
    否则回退到本地 ``mineru`` 包。

    参数:
        pdf_path: 输入 PDF 文件路径，或公开 URL（云端模式）。
        output_dir: 输出目录。
        lang: OCR 语言提示（``"ch"`` / ``"en"``）。
        backend: 本地模式: ``"pipeline"``（CPU）或 ``"hybrid-auto-engine"``（GPU）。
                 云端模式: ``"pipeline"`` 或 ``"vlm"``。

    返回:
        包含 Markdown、图片和内容列表的 :class:`ParseResult`。
    """
    pdf_str = str(pdf_path)
    is_url = pdf_str.startswith("http://") or pdf_str.startswith("https://")

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("MINERU_API_KEY")

    if is_url:
        if not api_key:
            raise ValueError("URL 输入需要设置 MINERU_API_KEY 以启用云端模式")
        logger.info("使用 MinerU 云端 API（URL 输入）")
        return _parse_cloud(pdf_str, output_dir, lang=lang, backend=backend, api_key=api_key)

    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件未找到: {pdf_path}")

    if api_key:
        logger.info("使用 MinerU 云端 API (mineru.net)")
        return _parse_cloud(pdf_path, output_dir, lang=lang, backend=backend, api_key=api_key)
    else:
        logger.info("使用本地 MinerU (backend=%s)", backend)
        return _parse_local(pdf_path, output_dir, lang=lang, backend=backend)


# ---------------------------------------------------------------------------
# 解析结果
# ---------------------------------------------------------------------------


class ParseResult:
    """保存 MinerU 解析的输出。"""

    def __init__(
        self,
        markdown: str,
        images_dir: Path | None,
        content_list: list[dict] | None,
        output_dir: Path,
    ):
        self.markdown = markdown
        self.images_dir = images_dir
        self.content_list = content_list
        self.output_dir = output_dir

    @property
    def image_paths(self) -> list[Path]:
        if not self.images_dir or not self.images_dir.exists():
            return []
        return sorted(self.images_dir.glob("*.*"))


# ---------------------------------------------------------------------------
# 本地解析（mineru Python 包）
# ---------------------------------------------------------------------------


def _parse_local(
    pdf_path: Path,
    output_dir: Path,
    *,
    lang: str,
    backend: str,
) -> ParseResult:
    from mineru.demo.demo import parse_doc

    logger.info("正在解析 %s backend=%s lang=%s", pdf_path.name, backend, lang)

    parse_doc(
        path_list=[pdf_path],
        output_dir=str(output_dir),
        lang=lang,
        backend=backend,
        method="auto",
        start_page_id=0,
        end_page_id=None,
    )

    return _collect_local_results(pdf_path, output_dir, backend)


def _collect_local_results(pdf_path: Path, output_dir: Path, backend: str) -> ParseResult:
    stem = pdf_path.stem
    sub = BACKEND_SUBDIRS.get(backend, backend.replace("-", "_"))
    base = output_dir / stem / sub

    md_candidates = list(base.glob(f"{stem}*.md"))
    if not md_candidates:
        md_candidates = list(base.glob("*.md"))
    md_path = md_candidates[0] if md_candidates else None
    markdown = md_path.read_text(encoding="utf-8") if md_path else ""

    images_dir = base / "images"
    if not images_dir.exists():
        images_dir = None

    cl_candidates = list(base.glob("*content_list.json"))
    content_list = None
    if cl_candidates:
        content_list = json.loads(cl_candidates[0].read_text(encoding="utf-8"))

    logger.info(
        "解析完成: %d 字符 Markdown, %d 张图片",
        len(markdown),
        len(list(images_dir.glob("*"))) if images_dir else 0,
    )

    return ParseResult(
        markdown=markdown,
        images_dir=images_dir,
        content_list=content_list,
        output_dir=base,
    )


# ---------------------------------------------------------------------------
# 云端解析（mineru.net REST API）
# ---------------------------------------------------------------------------


def _parse_cloud(
    pdf_path: str | Path,
    output_dir: Path,
    *,
    lang: str,
    backend: str,
    api_key: str,
) -> ParseResult:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    pdf_str = str(pdf_path)
    is_url = pdf_str.startswith("http://") or pdf_str.startswith("https://")
    cloud_backend = "vlm" if "vlm" in backend else ("pipeline" if backend == "pipeline" else "vlm")

    if is_url:
        from urllib.parse import urlparse

        url_path = urlparse(pdf_str).path
        stem = Path(url_path).stem or "document"

        logger.info("创建云端任务（URL 模式）: model_version=%s", cloud_backend)
        resp = requests.post(
            f"{CLOUD_API_BASE}/extract/task",
            headers=headers,
            json={
                "url": pdf_str,
                "model_version": cloud_backend,
                "enable_formula": True,
                "enable_table": True,
                "language": lang,
                "is_ocr": False,
            },
            timeout=30,
        )
        resp.raise_for_status()
        resp_data = resp.json()
        if resp_data.get("code") != 0:
            raise RuntimeError(f"MinerU 任务创建失败: {resp_data.get('msg', '未知错误')}")
        task_id = resp_data["data"]["task_id"]
        logger.info("云端任务已创建: %s", task_id)
        zip_url = _poll_task(task_id, headers)
    else:
        stem = Path(pdf_path).stem
        batch_id = _upload_batch(Path(pdf_path), api_key, model_version=cloud_backend)
        zip_url = _poll_batch(batch_id, headers)

    return _download_results(zip_url, output_dir, stem)


def _upload_batch(pdf_path: Path, api_key: str, *, model_version: str = "pipeline", max_retries: int = 3) -> str:
    """通过 file-urls/batch 端点上传 PDF 并返回 batch_id。

    遵循官方文档流程：
    1. POST /file-urls/batch → 获取上传 URL + batch_id
    2. PUT 上传文件（无 Content-Type）
    3. 系统自动提交解析任务，通过 batch_id 轮询结果
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    resp = requests.post(
        f"{CLOUD_API_BASE}/file-urls/batch",
        headers=headers,
        json={
            "files": [{"name": pdf_path.name}],
            "model_version": model_version,
        },
        timeout=30,
    )
    resp.raise_for_status()
    resp_data = resp.json()
    if resp_data.get("code") != 0:
        raise RuntimeError(f"MinerU 文件上传 API 错误: {resp_data.get('msg', '未知错误')}")

    data = resp_data.get("data", {})
    batch_id = data["batch_id"]
    upload_urls = data.get("file_urls", [])
    if not upload_urls:
        raise RuntimeError("未能获取 MinerU 云端上传 URL")

    upload_url = upload_urls[0] if isinstance(upload_urls[0], str) else upload_urls[0].get("url", "")

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            with open(pdf_path, "rb") as f:
                put_resp = requests.put(upload_url, data=f, timeout=180)
            put_resp.raise_for_status()
            logger.info("已上传 %s 到云端（第 %d 次尝试），batch_id=%s", pdf_path.name, attempt, batch_id)
            return batch_id
        except Exception as exc:
            last_exc = exc
            logger.warning("上传尝试 %d/%d 失败: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(2**attempt)

    raise RuntimeError(f"上传 PDF 到云端失败（{max_retries} 次尝试后）: {last_exc}")


def _poll_batch(batch_id: str, headers: dict, *, timeout: int = 300, interval: int = 5) -> str:
    """通过 batch_id 轮询解析结果（file-urls/batch 上传后自动触发解析）。"""
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(
            f"{CLOUD_API_BASE}/extract-results/batch/{batch_id}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        results = data.get("extract_result", [])

        if results:
            result = results[0]
            state = result.get("state", "")

            if state == "done":
                zip_url = result.get("full_zip_url", "")
                if zip_url:
                    logger.info("批量解析完成: batch_id=%s", batch_id)
                    return zip_url
                raise RuntimeError("解析完成但未返回 zip_url")

            if state == "failed":
                raise RuntimeError(f"云端解析失败: {result.get('err_msg', '未知错误')}")

            logger.debug("batch %s 状态: %s, 等待中...", batch_id, state)

        time.sleep(interval)

    raise TimeoutError(f"批量解析 {batch_id} 超时 ({timeout}s)")


def _poll_task(task_id: str, headers: dict, *, timeout: int = 300, interval: int = 5) -> str:
    """轮询直到云端任务完成并返回 ZIP 下载 URL。"""
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(
            f"{CLOUD_API_BASE}/extract/task/{task_id}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        state = data.get("state", "")

        if state == "done":
            zip_url = data.get("full_zip_url", "")
            if zip_url:
                logger.info("云端任务完成: %s", task_id)
                return zip_url
            raise RuntimeError("任务完成但未返回 zip_url")

        if state == "failed":
            raise RuntimeError(f"云端解析失败: {data.get('err_msg', '未知错误')}")

        logger.debug("任务 %s 状态: %s, 等待中...", task_id, state)
        time.sleep(interval)

    raise TimeoutError(f"云端任务 {task_id} 超时 ({timeout}s)")


def _download_results(zip_url: str, output_dir: Path, stem: str) -> ParseResult:
    """从云端下载 ZIP 并解压到输出目录。"""
    logger.info("正在下载云端结果...")
    resp = requests.get(zip_url, timeout=120)
    resp.raise_for_status()

    extract_dir = output_dir / stem / "cloud"
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(resp.content), "r") as z:
        z.extractall(str(extract_dir))

    md_files = list(extract_dir.rglob("*.md"))
    markdown = ""
    if md_files:
        markdown = md_files[0].read_text(encoding="utf-8")

    images_dir = None
    for candidate in extract_dir.rglob("images"):
        if candidate.is_dir():
            images_dir = candidate
            break

    content_list = None
    cl_files = list(extract_dir.rglob("*content_list.json"))
    if cl_files:
        content_list = json.loads(cl_files[0].read_text(encoding="utf-8"))

    logger.info(
        "云端解析完成: %d 字符 Markdown, %d 张图片",
        len(markdown),
        len(list(images_dir.glob("*"))) if images_dir else 0,
    )

    return ParseResult(
        markdown=markdown,
        images_dir=images_dir,
        content_list=content_list,
        output_dir=extract_dir,
    )
