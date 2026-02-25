"""Remotion 渲染桥接模块。

通过子进程调用 Remotion CLI，将 VideoScript JSON 渲染为最终视频。
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path

from .schemas import VideoScript

logger = logging.getLogger(__name__)

_DEFAULT_VIDEO_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent / "video"


def _find_video_package(video_package_dir: Path | None = None) -> Path:
    """定位 Remotion 视频包目录。

    查找顺序:
    1. 显式传入的 video_package_dir
    2. 环境变量 THEIA_VIDEO_PACKAGE_DIR
    3. 默认相对路径
    """
    if video_package_dir and video_package_dir.exists():
        return video_package_dir

    env_dir = os.getenv("THEIA_VIDEO_PACKAGE_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.exists():
            return p

    if _DEFAULT_VIDEO_PACKAGE_DIR.exists():
        return _DEFAULT_VIDEO_PACKAGE_DIR

    raise FileNotFoundError(
        f"Remotion 视频包未找到: {_DEFAULT_VIDEO_PACKAGE_DIR}。"
        "请确保 packages/video 存在且已安装 node_modules，"
        "或设置 THEIA_VIDEO_PACKAGE_DIR 环境变量。"
    )


def _ensure_npx() -> str:
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("未找到 npx，请安装 Node.js >= 18。")
    return npx


def render_video(
    script: VideoScript,
    output_path: Path,
    *,
    workspace: Path | None = None,
    parsed_dir: Path | None = None,
    video_package_dir: Path | None = None,
) -> Path:
    """从 VideoScript 渲染视频。

    参数:
        script: 包含音频文件路径的完整视频脚本。
        output_path: 最终 MP4 的输出路径。
        workspace: 包含音频文件的工作目录。脚本中引用的
                   音频路径会被复制到 Remotion 的 ``public/`` 目录。
        parsed_dir: MinerU 解析输出目录（直接定位图片，避免遍历）。
        video_package_dir: Remotion 视频包目录（覆盖默认值和环境变量）。

    返回:
        渲染完成的视频文件路径。
    """
    video_dir = _find_video_package(video_package_dir)
    npx = _ensure_npx()

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    public_dir = video_dir / "public"
    public_dir.mkdir(exist_ok=True)

    if workspace:
        _copy_audio_files(script, workspace, public_dir)
        _copy_figure_files(script, workspace, public_dir, parsed_dir=parsed_dir)

    # 序列化脚本为 JSON（驼峰命名以匹配 TypeScript）
    script_data = _to_camel_case_dict(script)
    logger.info("传递给 Remotion 的 meta: %s", json.dumps(script_data.get("meta", {})))
    script_json_path = public_dir / "video_script.json"
    script_json_path.write_text(json.dumps(script_data, ensure_ascii=False, indent=2))

    total_frames = sum(s.duration_in_frames for s in script.scenes)

    # 将 props 写入文件（避免命令行参数长度限制）
    props_file = public_dir / "_render_props.json"
    props_file.write_text(
        json.dumps({"script": script_data}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    concurrency = max(2, min(os.cpu_count() or 4, 16))
    gl_renderer = "angle" if platform.system() == "Darwin" else "swiftshader"

    cmd = [
        npx,
        "remotion",
        "render",
        "PaperVideo",
        str(output_path),
        "--props",
        str(props_file),
        "--concurrency",
        str(concurrency),
        "--gl",
        gl_renderer,
        "--jpeg-quality",
        "80",
        "--log",
        "warn",
    ]

    logger.info(
        "正在渲染 %d 帧 -> %s (concurrency=%d, gl=%s)",
        total_frames,
        output_path,
        concurrency,
        gl_renderer,
    )
    logger.debug("命令: %s", " ".join(cmd[:8]) + " ...")

    result = subprocess.run(
        cmd,
        cwd=str(video_dir),
        capture_output=True,
        text=True,
        timeout=1800,
    )

    if result.returncode != 0:
        logger.error("Remotion 渲染失败:\nstdout: %s\nstderr: %s", result.stdout, result.stderr)
        raise RuntimeError(f"Remotion 渲染失败 (退出码 {result.returncode}): {result.stderr[:500]}")

    if not output_path.exists():
        raise FileNotFoundError(f"渲染完成但未找到输出文件: {output_path}")

    logger.info("视频已渲染: %s", output_path)

    _generate_thumbnail(video_dir, npx, output_path, props_file)

    return output_path


def _generate_thumbnail(video_dir: Path, npx: str, video_path: Path, props_file: Path) -> None:
    """渲染第 1 帧作为视频封面图。"""
    gl_renderer = "angle" if platform.system() == "Darwin" else "swiftshader"
    thumb_path = video_path.with_suffix(".png")
    cmd = [
        npx,
        "remotion",
        "still",
        "PaperVideo",
        str(thumb_path),
        "--props",
        str(props_file),
        "--frame",
        "60",
        "--gl",
        gl_renderer,
        "--log",
        "warn",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(video_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and thumb_path.exists():
            logger.info("封面已生成: %s", thumb_path)
        else:
            logger.warning("封面生成失败: %s", result.stderr[:200])
    except Exception as exc:
        logger.warning("封面生成异常: %s", exc)


def _copy_audio_files(script: VideoScript, workspace: Path, public_dir: Path) -> None:
    """将脚本中引用的音频文件复制到 Remotion 的 public 目录。"""
    audio_dest = public_dir / "audio"
    audio_dest.mkdir(exist_ok=True)

    for i, scene in enumerate(script.scenes):
        if not scene.audio_file:
            continue
        src = Path(scene.audio_file)
        if not src.is_absolute():
            candidates = [src, workspace / src, workspace / src.name]
            src = next((c for c in candidates if c.exists()), src)
        if src.exists():
            dest = audio_dest / f"scene_{i}.mp3"
            shutil.copy2(src, dest)
            scene.audio_file = f"audio/scene_{i}.mp3"
            logger.debug("复制音频: %s -> %s", src, dest)


def _copy_figure_files(
    script: VideoScript,
    workspace: Path,
    public_dir: Path,
    *,
    parsed_dir: Path | None = None,
) -> None:
    """将脚本中引用的论文图片复制到 Remotion 的 public 目录。"""
    figures_dest = public_dir / "figures"
    figures_dest.mkdir(exist_ok=True)

    if parsed_dir:
        p = Path(parsed_dir)
        images_candidate = p / "images"
        parsed_dirs = [images_candidate] if images_candidate.exists() else list(p.rglob("images"))
    else:
        parsed_dirs = list((workspace / "parsed").rglob("images"))

    def _resolve_and_copy(fig_path: str) -> str | None:
        src = None
        name = Path(fig_path).name
        for images_dir in parsed_dirs:
            candidate = images_dir / name
            if candidate.exists():
                src = candidate
                break
        if src is None:
            for images_dir in parsed_dirs:
                candidate = images_dir.parent / fig_path
                if candidate.exists():
                    src = candidate
                    break
        if src and src.exists():
            dest = figures_dest / src.name
            shutil.copy2(src, dest)
            remotion_path = f"figures/{src.name}"
            logger.debug("复制图片: %s -> %s", src, dest)
            return remotion_path
        return None

    for scene in script.scenes:
        # figure 专属场景的 figurePath
        fp = scene.data.get("figurePath", "")
        if fp:
            resolved = _resolve_and_copy(fp)
            if resolved:
                scene.data["figurePath"] = resolved

        # 其他场景的 figures 列表
        fig_paths = scene.data.get("figures", [])
        updated_paths: list[str] = []
        for fig_path in fig_paths:
            resolved = _resolve_and_copy(fig_path)
            if resolved:
                updated_paths.append(resolved)
        if updated_paths:
            scene.data["figures"] = updated_paths


def _to_camel_case_dict(script: VideoScript) -> dict:
    """将 VideoScript 转换为驼峰命名的 dict，匹配 TypeScript schema。"""
    return {
        "meta": {
            "fps": script.meta.fps,
            "width": script.meta.width,
            "height": script.meta.height,
            "theme": script.meta.theme,
        },
        "scenes": [
            {
                "type": s.type.value,
                "durationInFrames": s.duration_in_frames,
                "narration": s.narration,
                "audioFile": s.audio_file,
                "data": s.data,
                "wordTimings": [
                    {"text": wt.text, "offsetMs": wt.offset_ms, "durationMs": wt.duration_ms} for wt in s.word_timings
                ],
            }
            for s in script.scenes
        ],
    }
