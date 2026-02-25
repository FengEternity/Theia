"""声音试听预览文件的生成与缓存。"""

from __future__ import annotations

import logging
from pathlib import Path

import edge_tts

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "workspace" / "voice_previews"


async def get_or_generate_preview(voice_id: str, text: str, rate: int = 0) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = voice_id.replace("/", "_")
    suffix = f"_rate{rate}" if rate != 0 else ""
    path = CACHE_DIR / f"{safe_name}{suffix}.mp3"

    if path.exists() and path.stat().st_size > 0:
        return path

    try:
        rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"
        communicate = edge_tts.Communicate(text, voice_id, rate=rate_str)
        await communicate.save(str(path))
    except Exception:
        path.unlink(missing_ok=True)
        raise

    if not path.exists() or path.stat().st_size == 0:
        path.unlink(missing_ok=True)
        raise RuntimeError(f"生成预览文件为空: {voice_id}")

    return path
