"""输出生成：视频脚本（多 Agent 协作）、语音合成和视频渲染。"""

from .renderer import render_video
from .scriptwriter import generate_video_script
from .tts import synthesize_narration

__all__ = [
    "generate_video_script",
    "render_video",
    "synthesize_narration",
]
