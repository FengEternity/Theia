"""Manim 预渲染模块。

将 VideoScript 中标记的 ManimAnimationSpec 渲染为视频片段，
供 Remotion 在最终合成时嵌入播放。

渲染通过子进程调用 ``manim render`` CLI 实现，
避免在主进程中 import manim 导致的依赖冲突。
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from ..schemas import ManimAnimationSpec, ManimAnimationType, ManimClip, VideoScript
from .manim_templates import build_template_params, get_template

logger = logging.getLogger(__name__)

_QUALITY_FLAGS: dict[str, str] = {
    "low_quality": "-ql",
    "medium_quality": "-qm",
    "high_quality": "-qh",
    "production_quality": "-qp",
}


def is_manim_available() -> bool:
    """检测当前环境是否安装了 ManimCE。"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "manim", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


_TEXLIVE_BIN = Path.home() / "texlive" / "2025" / "bin" / "x86_64-linux"


def _ensure_latex_path() -> dict[str, str]:
    """返回包含 texlive 路径的环境变量字典，供子进程使用。"""
    import os

    env = os.environ.copy()
    texlive_str = str(_TEXLIVE_BIN)
    if _TEXLIVE_BIN.exists() and texlive_str not in env.get("PATH", ""):
        env["PATH"] = f"{texlive_str}:{env.get('PATH', '')}"
    return env


def is_latex_available() -> bool:
    """检测当前环境是否安装了 LaTeX（公式渲染所需）。"""
    if shutil.which("latex") is not None or shutil.which("xelatex") is not None:
        return True
    if _TEXLIVE_BIN.exists():
        return (
            (_TEXLIVE_BIN / "latex").exists()
            or (_TEXLIVE_BIN / "xelatex").exists()
        )
    return False


def render_manim_clips(
    script: VideoScript,
    workspace: Path,
    *,
    quality: str = "medium_quality",
    transparent: bool = False,
) -> VideoScript:
    """扫描 script 中的 manim_animations，渲染为视频片段。

    参数:
        script: 包含 manim_animations 的视频脚本。
        workspace: 工作目录。
        quality: 渲染质量 (low_quality / medium_quality / high_quality / production_quality)。
        transparent: 是否渲染透明背景 (webm)。

    返回:
        更新了 manim_clips 的 VideoScript（原对象被就地修改）。
    """
    if not is_manim_available():
        logger.warning("ManimCE 未安装或不可用，跳过所有 Manim 动画渲染")
        return script

    clips_dir = workspace / "manim_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = workspace / "manim_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    resolution = (script.meta.width, script.meta.height)
    fps = script.meta.fps
    total_rendered = 0
    total_failed = 0

    latex_available = is_latex_available()
    if not latex_available:
        logger.warning("LaTeX 未安装，公式类 Manim 动画将被跳过（几何/向量场等仍可渲染）")

    for scene_idx, scene in enumerate(script.scenes):
        if not scene.manim_animations:
            continue

        for anim_idx, spec in enumerate(scene.manim_animations):
            clip_id = f"s{scene_idx}_a{anim_idx}"
            cache_key = _compute_cache_key(spec)
            cached_path = clips_dir / f"{cache_key}.mp4"

            if cached_path.exists():
                logger.debug("使用缓存的 Manim 片段: %s", cached_path.name)
                clip = _build_clip_metadata(cached_path, spec, clips_dir)
                scene.manim_clips.append(clip)
                total_rendered += 1
                continue

            try:
                clip = _render_single_clip(
                    spec=spec,
                    tmp_dir=tmp_dir,
                    clips_dir=clips_dir,
                    clip_id=clip_id,
                    cache_key=cache_key,
                    resolution=resolution,
                    fps=fps,
                    quality=quality,
                    transparent=transparent,
                    latex_available=latex_available,
                )
                scene.manim_clips.append(clip)
                total_rendered += 1
            except Exception:
                logger.exception("Manim 渲染失败 (scene=%d, anim=%d)，该动画将退回 Remotion 默认", scene_idx, anim_idx)
                total_failed += 1

    _cleanup_tmp(tmp_dir)

    logger.info(
        "Manim 预渲染完成: %d 成功, %d 失败",
        total_rendered,
        total_failed,
    )
    return script


def _render_single_clip(
    *,
    spec: ManimAnimationSpec,
    tmp_dir: Path,
    clips_dir: Path,
    clip_id: str,
    cache_key: str,
    resolution: tuple[int, int],
    fps: int,
    quality: str,
    transparent: bool,
    latex_available: bool = True,
) -> ManimClip:
    """渲染单个 Manim 动画片段。"""
    template, scene_class = get_template(spec.type, latex_available=latex_available)
    params = build_template_params(
        spec.type,
        formulas=spec.formulas or None,
        config=spec.config or None,
        resolution=resolution,
        duration_hint_sec=spec.duration_hint_sec,
    )

    scene_code = template.safe_substitute(params)

    tmp_file = tmp_dir / f"_manim_{clip_id}.py"
    tmp_file.write_text(scene_code, encoding="utf-8")

    quality_flag = _QUALITY_FLAGS.get(quality, "-qm")

    media_dir = tmp_dir / "media"
    cmd = [
        sys.executable,
        "-m",
        "manim",
        "render",
        str(tmp_file),
        scene_class,
        quality_flag,
        "--format",
        "webm" if transparent else "mp4",
        "--media_dir",
        str(media_dir),
        "--fps",
        str(fps),
        "-r",
        f"{resolution[0]},{resolution[1]}",
        "--disable_caching",
    ]
    if transparent:
        cmd.append("--transparent")

    logger.debug("Manim 命令: %s", " ".join(cmd[:10]) + " ...")

    env = _ensure_latex_path()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(tmp_dir),
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"manim render 失败 (exit {result.returncode}): {result.stderr[:500]}"
        )

    output_file = _find_rendered_file(media_dir, scene_class, transparent)
    if output_file is None:
        raise FileNotFoundError(
            f"Manim 渲染完成但未找到输出文件 (scene_class={scene_class})"
        )

    ext = ".webm" if transparent else ".mp4"
    dest = clips_dir / f"{cache_key}{ext}"
    shutil.copy2(output_file, dest)

    return _build_clip_metadata(dest, spec, clips_dir)


def _find_rendered_file(
    media_dir: Path,
    scene_class: str,
    transparent: bool,
) -> Path | None:
    """在 manim 的 media 目录中查找渲染产物。"""
    ext = "*.webm" if transparent else "*.mp4"
    candidates = sorted(media_dir.rglob(ext), key=lambda p: p.stat().st_mtime, reverse=True)
    for c in candidates:
        if scene_class in c.stem or scene_class.lower() in c.stem.lower():
            return c
    return candidates[0] if candidates else None


def _build_clip_metadata(
    clip_path: Path,
    spec: ManimAnimationSpec,
    clips_dir: Path,
) -> ManimClip:
    """从渲染文件和 spec 构造 ManimClip 元数据。"""
    duration_ms = _probe_duration_ms(clip_path)
    if duration_ms <= 0:
        duration_ms = int(spec.duration_hint_sec * 1000)

    rel_path = str(clip_path.relative_to(clips_dir.parent))

    return ManimClip(
        clip_path=rel_path,
        start_ms=0,
        duration_ms=duration_ms,
        position=spec.position,
        opacity=1.0,
    )


def _probe_duration_ms(path: Path) -> int:
    """用 ffprobe 获取视频时长（毫秒）。"""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(float(result.stdout.strip()) * 1000)
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return 0


def _compute_cache_key(spec: ManimAnimationSpec) -> str:
    """基于动画规格计算缓存 key。"""
    payload = f"{spec.type.value}|{'|'.join(spec.formulas)}|{sorted(spec.config.items())}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _cleanup_tmp(tmp_dir: Path) -> None:
    """清理临时生成的 .py 文件和 media 目录。"""
    try:
        media = tmp_dir / "media"
        if media.exists():
            shutil.rmtree(media)
        for f in tmp_dir.glob("_manim_*.py"):
            f.unlink(missing_ok=True)
    except OSError as exc:
        logger.debug("清理 manim 临时文件失败: %s", exc)
