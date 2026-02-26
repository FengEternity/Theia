"""Edge TTS 语音合成模块。

为视频每个场景生成语音文件，并根据实际音频时长
更新视频脚本中的帧数，确保音画精确同步。
支持 SSML 语速/语调控制和场景缓冲帧。
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import re
from pathlib import Path

import edge_tts
from mutagen.mp3 import MP3

from ..schemas import VideoScript, WordTiming

logger = logging.getLogger(__name__)

DEFAULT_VOICE_ZH = "zh-CN-YunxiNeural"
DEFAULT_VOICE_EN = "en-US-GuyNeural"

VOICE_PRESETS: dict[str, dict[str, str]] = {
    "zh": {
        "yunxi": "zh-CN-YunxiNeural",
        "yunxi_calm": "zh-CN-YunxiNeural",
        "xiaoyi": "zh-CN-XiaoyiNeural",
        "yunyang": "zh-CN-YunyangNeural",
        "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    },
    "en": {
        "guy": "en-US-GuyNeural",
        "jenny": "en-US-JennyNeural",
        "aria": "en-US-AriaNeural",
        "davis": "en-US-DavisNeural",
    },
}

SCENE_PADDING: dict[str, tuple[float, float]] = {
    "title": (0.5, 1.0),
    "overview": (0.5, 0.5),
    "method": (0.5, 0.5),
    "formula": (1.0, 2.0),
    "figure": (1.0, 1.5),
    "result": (0.5, 1.0),
    "conclusion": (0.5, 1.5),
}

SCENE_PROSODY: dict[str, dict[str, str]] = {
    "title": {"rate": "-5%", "pitch": "+3%"},
    "overview": {"rate": "+0%", "pitch": "+0%"},
    "method": {"rate": "+0%", "pitch": "+0%"},
    "formula": {"rate": "-10%", "pitch": "+0%"},
    "figure": {"rate": "-5%", "pitch": "+0%"},
    "result": {"rate": "+3%", "pitch": "+2%"},
    "conclusion": {"rate": "-8%", "pitch": "+0%"},
}


def _wrap_ssml(text: str, voice: str, scene_type: str) -> str:
    """将旁白文本包装为 SSML，应用场景级语速/语调。"""
    prosody = SCENE_PROSODY.get(scene_type, {})
    rate = prosody.get("rate", "+0%")
    pitch = prosody.get("pitch", "+0%")

    text = re.sub(r"\.{3,}", '<break time="400ms"/>', text)
    text = re.sub(r"[？?]", '？<break time="300ms"/>', text)

    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">'
        f'<voice name="{voice}">'
        f'<prosody rate="{rate}" pitch="{pitch}">'
        f"{text}"
        f"</prosody></voice></speak>"
    )


class TTSBackend:
    """TTS 后端基类，支持扩展不同 TTS 引擎。"""

    async def synthesize(self, text: str, output_path: Path, voice: str, scene_type: str) -> tuple[float, list[dict]]:
        raise NotImplementedError


_TTS_MAX_RETRIES = int(os.getenv("THEIA_TTS_MAX_RETRIES", "3"))
_TTS_TIMEOUT = int(os.getenv("THEIA_TTS_TIMEOUT", "30"))


class EdgeTTSBackend(TTSBackend):
    """Edge TTS 后端（默认），内置重试和超时机制。"""

    def __init__(self, rate_offset: int = 0):
        self.rate_offset = rate_offset

    async def _do_synthesize(self, text: str, output_path: Path, voice: str, scene_type: str) -> tuple[float, list[dict]]:
        prosody = SCENE_PROSODY.get(scene_type, {})
        scene_rate = int(prosody.get("rate", "+0%").replace("%", ""))
        total_rate = scene_rate + self.rate_offset
        rate_str = f"+{total_rate}%" if total_rate >= 0 else f"{total_rate}%"
        communicate = edge_tts.Communicate(text, voice, rate=rate_str)

        word_timings: list[dict] = []
        with open(output_path, "wb") as fp:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    fp.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word_timings.append(
                        {
                            "text": chunk["text"],
                            "offset_ms": chunk["offset"] // 10_000,
                            "duration_ms": chunk["duration"] // 10_000,
                        }
                    )

        audio = MP3(str(output_path))
        duration = audio.info.length

        if not word_timings:
            word_timings = _estimate_word_timings(text, duration)

        logger.debug(
            "TTS [Edge]: %.1f 秒, %d 词边界 -> %s (scene=%s)",
            duration,
            len(word_timings),
            output_path.name,
            scene_type,
        )
        return duration, word_timings

    async def synthesize(self, text: str, output_path: Path, voice: str, scene_type: str) -> tuple[float, list[dict]]:
        last_exc: Exception | None = None
        for attempt in range(1, _TTS_MAX_RETRIES + 1):
            try:
                return await asyncio.wait_for(
                    self._do_synthesize(text, output_path, voice, scene_type),
                    timeout=_TTS_TIMEOUT,
                )
            except (TimeoutError, asyncio.TimeoutError, OSError, ConnectionError) as exc:
                last_exc = exc
                delay = min(2 ** attempt, 15)
                logger.warning(
                    "TTS 第 %d/%d 次尝试失败 (%s: %s)，%ds 后重试",
                    attempt, _TTS_MAX_RETRIES, type(exc).__name__, str(exc)[:100], delay,
                )
                await asyncio.sleep(delay)
            except Exception as exc:
                last_exc = exc
                if attempt < _TTS_MAX_RETRIES:
                    delay = min(2 ** attempt, 15)
                    logger.warning(
                        "TTS 第 %d/%d 次尝试失败 (%s)，%ds 后重试",
                        attempt, _TTS_MAX_RETRIES, exc, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    break

        raise RuntimeError(
            f"Edge TTS 在 {_TTS_MAX_RETRIES} 次重试后仍失败: {last_exc}"
        ) from last_exc


def _estimate_word_timings(text: str, duration_s: float) -> list[dict]:
    """当 word boundary 事件不可用时，基于字符数估算时间戳。"""
    import re as _re

    segments = _re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+|[0-9]+[.%]?[0-9]*|\S", text)
    if not segments:
        return []

    total_chars = sum(len(s) for s in segments)
    if total_chars == 0:
        return []

    ms_per_char = (duration_s * 1000) / total_chars
    offset = 0
    timings = []
    for seg in segments:
        dur = int(len(seg) * ms_per_char)
        timings.append({"text": seg, "offset_ms": int(offset), "duration_ms": dur})
        offset += dur

    return timings


_tts_backend: TTSBackend = EdgeTTSBackend()


def set_tts_backend(backend: TTSBackend) -> None:
    """切换 TTS 后端（如 Fish Audio、ChatTTS 等自定义实现）。"""
    global _tts_backend
    _tts_backend = backend
    logger.info("TTS 后端已切换: %s", type(backend).__name__)


async def _synthesize_one(
    text: str,
    output_path: Path,
    voice: str,
    *,
    scene_type: str = "overview",
    backend: TTSBackend | None = None,
) -> tuple[float, list[dict]]:
    """合成单条文本，返回 (音频时长秒, word_timings)。"""
    b = backend or _tts_backend
    return await b.synthesize(text, output_path, voice, scene_type)


def _timings_to_srt(
    all_timings: list[tuple[int, float, list[dict]]],
    fps: int,
) -> str:
    """将所有场景的 word timing 合并为 SRT 字幕。

    每条字幕约 15-25 个字符，避免单字字幕和过长字幕。
    """
    entries: list[str] = []
    idx = 1

    for scene_idx, scene_offset_s, timings in all_timings:
        if not timings:
            continue

        chunk_text = ""
        chunk_start_ms = 0

        for wt in timings:
            abs_start_ms = int(scene_offset_s * 1000) + wt["offset_ms"]
            abs_end_ms = abs_start_ms + wt["duration_ms"]

            if not chunk_text:
                chunk_start_ms = abs_start_ms

            chunk_text += wt["text"]

            if len(chunk_text) >= 18 or wt is timings[-1]:
                entries.append(
                    f"{idx}\n{_ms_to_srt_time(chunk_start_ms)} --> {_ms_to_srt_time(abs_end_ms)}\n{chunk_text}\n"
                )
                idx += 1
                chunk_text = ""

    return "\n".join(entries)


def _ms_to_srt_time(ms: int) -> str:
    """将毫秒转为 SRT 时间格式 HH:MM:SS,mmm。"""
    h = ms // 3_600_000
    m = (ms % 3_600_000) // 60_000
    s = (ms % 60_000) // 1_000
    remainder = ms % 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{remainder:03d}"


async def _synthesize_all(
    script: VideoScript,
    audio_dir: Path,
    voice: str,
    backend: TTSBackend | None = None,
) -> VideoScript:
    """为所有场景生成音频并更新帧时长（含缓冲帧），同时生成 SRT 字幕。

    所有有旁白的场景并行合成，完成后按顺序计算累计时间和字幕。
    """
    audio_dir.mkdir(parents=True, exist_ok=True)

    async def _do_one(i: int, scene_type: str, narration: str) -> tuple[int, float, list[dict]] | None:
        audio_path = audio_dir / f"scene_{i}.mp3"
        try:
            duration_s, word_timings = await _synthesize_one(
                narration,
                audio_path,
                voice,
                scene_type=scene_type,
                backend=backend,
            )
            return i, duration_s, word_timings
        except Exception as exc:
            logger.error("场景 %d TTS 失败（跳过）: %s", i, exc)
            return None

    tasks = []
    for i, scene in enumerate(script.scenes):
        if scene.narration.strip():
            tasks.append(_do_one(i, scene.type.value, scene.narration))

    results_list = await asyncio.gather(*tasks)
    failed_count = sum(1 for r in results_list if r is None)
    if failed_count == len(tasks) and tasks:
        raise RuntimeError(f"所有 {len(tasks)} 个场景的 TTS 合成均失败")
    if failed_count > 0:
        logger.warning("TTS: %d/%d 个场景合成失败", failed_count, len(tasks))

    results_map: dict[int, tuple[float, list[dict]]] = {
        r[0]: (r[1], r[2]) for r in results_list if r is not None
    }

    all_timings: list[tuple[int, float, list[dict]]] = []
    cumulative_s = 0.0

    for i, scene in enumerate(script.scenes):
        if i not in results_map:
            cumulative_s += scene.duration_in_frames / script.meta.fps
            continue

        duration_s, word_timings = results_map[i]
        audio_path = audio_dir / f"scene_{i}.mp3"

        pre_pad, post_pad = SCENE_PADDING.get(scene.type.value, (0.5, 0.5))
        total_s = pre_pad + duration_s + post_pad

        scene.audio_file = str(audio_path)
        scene.duration_in_frames = max(
            int(math.ceil(total_s * script.meta.fps)),
            script.meta.fps * 2,
        )
        scene.word_timings = [
            WordTiming(text=wt["text"], offset_ms=wt["offset_ms"], duration_ms=wt["duration_ms"]) for wt in word_timings
        ]

        audio_start_s = cumulative_s + pre_pad
        all_timings.append((i, audio_start_s, word_timings))
        cumulative_s += total_s

    srt_content = _timings_to_srt(all_timings, script.meta.fps)
    srt_path = audio_dir / "subtitles.srt"
    srt_path.write_text(srt_content, encoding="utf-8")

    logger.info(
        "TTS 完成: %d 个音频文件, 约 %.0f 秒 (含缓冲帧), 字幕: %s",
        sum(1 for s in script.scenes if s.audio_file),
        script.total_duration_seconds,
        srt_path,
    )
    return script


def synthesize_narration(
    script: VideoScript,
    audio_dir: Path,
    *,
    voice: str | None = None,
    language: str = "zh",
    speech_rate: int = 0,
) -> VideoScript:
    """TTS 合成的同步入口。

    参数:
        script: 包含旁白文本的视频脚本。
        audio_dir: 音频文件输出目录。
        voice: Edge TTS 声音名称（或预设别名），为 *None* 时自动选择。
        language: 语言提示，用于自动选择声音。
        speech_rate: 全局语速偏移百分比（如 +20 表示加速 20%，-10 表示减速 10%）。

    返回:
        更新了 ``audio_file`` 路径和 ``duration_in_frames``
        的 :class:`VideoScript`。同时在 audio_dir 下生成 ``subtitles.srt``。
    """
    backend: TTSBackend = _tts_backend
    if isinstance(backend, EdgeTTSBackend) and speech_rate != 0:
        backend = EdgeTTSBackend(rate_offset=speech_rate)

    if voice is None:
        voice = DEFAULT_VOICE_ZH if language == "zh" else DEFAULT_VOICE_EN
    else:
        presets = VOICE_PRESETS.get(language, {})
        voice = presets.get(voice, voice)

    logger.info("正在合成旁白 voice=%s, speech_rate=%+d%%", voice, speech_rate)
    return asyncio.run(_synthesize_all(script, audio_dir, voice, backend=backend))
