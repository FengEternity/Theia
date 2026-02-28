"""Theia CLI 入口。"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """Theia: 论文 PDF 到讲解视频 Agent。"""


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None, help="输出视频路径。")
@click.option("-w", "--workspace", type=click.Path(path_type=Path), default="./workspace", help="工作目录。")
@click.option(
    "-m",
    "--model",
    default=lambda: os.getenv("THEIA_EXTRACT_MODEL", "kimi-k2-0905-preview"),
    help="LLM 模型（LiteLLM 标识符，作为后备）。",
)
@click.option("--extract-model", default=None, help="论文提取模型（默认同 -m）。")
@click.option("--script-model", default=None, help="脚本生成模型。")
@click.option(
    "-l", "--language", default="zh", type=click.Choice(["zh", "en", "auto"]), help="主要语言。'auto' 为自动检测。"
)
@click.option("--voice", default=None, help="Edge TTS 声音名称。")
@click.option("--backend", default="pipeline", help="MinerU 后端。")
@click.option("--fps", default=30, type=int, help="视频帧率。")
@click.option(
    "--preset",
    default="landscape",
    type=click.Choice(["landscape", "bilibili", "portrait", "douyin", "xiaohongshu", "square"]),
    help="视频尺寸预设（平台）。",
)
@click.option("--skip-tts", is_flag=True, help="跳过 TTS 语音合成。")
@click.option("--skip-render", is_flag=True, help="跳过视频渲染。")
@click.option("--scan-model", default=None, help="Pass 1 快速扫描模型。")
@click.option(
    "--narration-style",
    default=lambda: os.getenv("THEIA_NARRATION_STYLE", "default"),
    type=click.Choice(["default", "academic", "story", "popsci"]),
    help="旁白风格。",
)
@click.option(
    "--theme",
    default=lambda: os.getenv("THEIA_THEME", "academic"),
    type=click.Choice(["academic", "popsci"]),
    help="视频视觉主题。",
)
@click.option("-v", "--verbose", is_flag=True, help="启用调试日志。")
def render(
    pdf_path: Path,
    output: Path | None,
    workspace: Path,
    model: str,
    extract_model: str | None,
    script_model: str | None,
    language: str,
    voice: str | None,
    backend: str,
    fps: int,
    preset: str,
    skip_tts: bool,
    skip_render: bool,
    scan_model: str | None,
    narration_style: str,
    theme: str,
    verbose: bool,
    **_kwargs,
) -> None:
    """将论文 PDF 渲染为讲解视频。

    示例: theia render paper.pdf -o output.mp4
    """
    _setup_logging(verbose)

    from .pipeline import run_pipeline

    try:
        result = run_pipeline(
            pdf_path,
            output,
            workspace=workspace,
            llm_model=model,
            extract_model=extract_model,
            scan_model=scan_model,
            script_model=script_model,
            language=language,
            tts_voice=voice,
            mineru_backend=backend,
            fps=fps,
            video_preset=preset,
            skip_tts=skip_tts,
            skip_render=skip_render,
            narration_style=narration_style,
            theme=theme,
        )
        if result.get("output_video"):
            click.echo(f"\n视频已保存到: {result['output_video']}")
        else:
            click.echo("\n流水线完成（渲染已跳过）。")
    except Exception as exc:
        click.echo(f"\n错误: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default="./workspace/parsed")
@click.option("-l", "--lang", default="ch", help="OCR 语言提示。")
@click.option("--backend", default="pipeline", help="MinerU 后端。")
@click.option("-v", "--verbose", is_flag=True)
def parse(pdf_path: Path, output_dir: Path, lang: str, backend: str, verbose: bool) -> None:
    """仅解析 PDF，不运行完整流水线。"""
    _setup_logging(verbose)

    from .parsing.pdf import parse_pdf

    result = parse_pdf(pdf_path, output_dir, lang=lang, backend=backend)
    click.echo(f"Markdown: {len(result.markdown)} 字符")
    click.echo(f"图片: {len(result.image_paths)} 个文件")
    click.echo(f"输出目录: {result.output_dir}")


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("-m", "--model", default="kimi-k2-0905-preview", help="LLM 模型。")
@click.option("-w", "--workspace", type=click.Path(path_type=Path), default="./workspace")
@click.option("--backend", default="pipeline", help="MinerU 后端。")
@click.option("--scan-model", default=None, help="Pass 1 快速扫描模型。")
@click.option("-v", "--verbose", is_flag=True)
def extract(
    pdf_path: Path,
    model: str,
    workspace: Path,
    backend: str,
    scan_model: str | None,
    verbose: bool,
) -> None:
    """解析 PDF 并提取论文摘要（不生成视频）。"""
    _setup_logging(verbose)

    from .extraction.extractor import extract_paper_summary
    from .parsing.pdf import parse_pdf

    result = parse_pdf(pdf_path, workspace / "parsed", backend=backend)
    summary = extract_paper_summary(
        result.markdown,
        model=model,
        scan_model=scan_model,
        images_dir=result.images_dir,
        content_list=result.content_list,
    )

    import json

    click.echo(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
