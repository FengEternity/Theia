"""基于文件的简易缓存，用于流水线各步骤。

缓存解析结果和 LLM 提取结果，避免对同一份 PDF 重复处理。
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

CACHE_DIR_NAME = ".theia_cache"


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _cache_dir(workspace: Path) -> Path:
    d = workspace / CACHE_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_cached(
    workspace: Path,
    key: str,
    model_cls: type[T],
) -> T | None:
    """读取缓存的 Pydantic 模型，不存在则返回 *None*。"""
    cache_path = _cache_dir(workspace) / f"{key}.json"
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        result = model_cls(**data)
        logger.info("缓存命中: %s", key)
        return result
    except Exception:
        logger.debug("缓存无效: %s", key)
        return None


def set_cached(workspace: Path, key: str, model: BaseModel) -> None:
    """将 Pydantic 模型写入缓存。"""
    cache_path = _cache_dir(workspace) / f"{key}.json"
    cache_path.write_text(
        json.dumps(model.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.debug("已缓存: %s", key)


def cache_key_for_pdf(pdf_path: Path, step: str) -> str:
    """根据文件哈希和步骤名称生成缓存键。"""
    h = _file_hash(pdf_path)
    return f"{pdf_path.stem}_{h}_{step}"


def cache_key_for_content(content: str, *tags: str) -> str:
    """根据内容哈希和可选标签生成缓存键。"""
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    suffix = "_".join(tags) if tags else "data"
    return f"{suffix}_{h}"
