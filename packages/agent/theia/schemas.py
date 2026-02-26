"""流水线中共享的核心数据模型。"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# 进度回调协议
# ---------------------------------------------------------------------------


class StepInfo(BaseModel):
    """单个流水线步骤的进度信息。"""

    step: int = Field(description="当前步骤序号 (1-5)")
    total_steps: int = Field(default=5, description="总步骤数")
    name: str = Field(description="步骤名称: parse | extract | script | tts | render")
    status: str = Field(description="状态: started | progress | completed | failed")
    message: str = Field(default="")
    progress_pct: int = Field(default=0, ge=0, le=100, description="步骤内进度 0-100")
    detail: dict[str, Any] = Field(default_factory=dict, description="额外信息")


@runtime_checkable
class ProgressCallback(Protocol):
    """流水线进度回调协议。

    由 task_manager 或 CLI 实现，agent 层仅依赖此协议，
    实现 agent ↔ server 解耦。
    """

    def on_step(self, info: StepInfo) -> None: ...

    def on_token(self, step_name: str, token: str) -> None:
        """LLM 流式输出的 token 片段回调。

        参数:
            step_name: 当前步骤标识 (如 ``pass1``, ``pass2``, ``script``)。
            token: 本次输出的文本片段。
        """
        ...


# ---------------------------------------------------------------------------
# 论文摘要（LLM 提取输出）
# ---------------------------------------------------------------------------


class Figure(BaseModel):
    path: str = Field(description="提取的图片文件相对路径")
    caption: str = Field(default="", description="图片标题文本")
    description: str = Field(default="", description="多模态 LLM 生成的图片内容描述")
    importance: int = Field(default=0, ge=0, le=5, description="重要性评分 0-5")
    figure_type: str = Field(
        default="",
        description="图片类型: architecture/comparison/result/visualization/other",
    )


class MethodDetail(BaseModel):
    summary: str = Field(description="方法概述（一段话）")
    key_steps: list[str] = Field(default_factory=list, description="有序的方法步骤")
    formulas: list[str] = Field(default_factory=list, description="关键公式（LaTeX 格式）")


class BaselineResult(BaseModel):
    name: str
    metric: str
    value: float | None = None
    highlight: bool = False

    @field_validator("value", mode="before")
    @classmethod
    def _coerce_value(cls, v: object) -> float | None:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return None
        return None


class ResultDetail(BaseModel):
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    baselines: list[BaselineResult] = Field(default_factory=list, description="对比方法性能数据")
    findings: str = Field(default="", description="实验发现摘要")


class PaperSummary(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    problem: str = Field(description="研究问题陈述")
    method: MethodDetail
    results: ResultDetail
    conclusion: str
    contributions: list[str] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
    paper_type: str = Field(default="", description="论文类型: empirical/theoretical/survey/system")
    core_idea: str = Field(default="", description="一句话核心直觉")
    key_insights: list[str] = Field(default_factory=list, description="关键洞察列表")


class PaperOverview(BaseModel):
    """Pass 1 输出：论文快速扫描结果，用于指导后续深度提取。"""

    paper_type: str = Field(description="论文类型: empirical/theoretical/survey/system")
    core_idea: str = Field(description="一句话核心思想")
    key_contributions: list[str] = Field(default_factory=list)
    important_sections: list[str] = Field(
        default_factory=list,
        description="需要深度阅读的章节标题（原文标题）",
    )
    reading_focus: list[str] = Field(
        default_factory=list,
        description="关键问题列表，指导 Pass 2 的深度提取",
    )


# ---------------------------------------------------------------------------
# 视频脚本（传递给 Remotion）
# ---------------------------------------------------------------------------


class SceneType(str, Enum):
    TITLE = "title"
    OVERVIEW = "overview"
    METHOD = "method"
    FORMULA = "formula"
    FIGURE = "figure"
    RESULT = "result"
    CONCLUSION = "conclusion"
    CONCEPT = "concept"
    ANALOGY = "analogy"
    RELATIONSHIP = "relationship"
    DEMO = "demo"
    COMPARISON = "comparison"
    CHARACTER_TALK = "character_talk"
    SUMMARY_CARD = "summary_card"
    CODE_DEMO = "code_demo"


class WordTiming(BaseModel):
    text: str
    offset_ms: int = Field(description="相对于场景音频开始的偏移（毫秒）")
    duration_ms: int


class Scene(BaseModel):
    type: SceneType
    duration_in_frames: int = Field(ge=1)
    narration: str = Field(description="该场景的 TTS 旁白文本")
    audio_file: str | None = Field(default=None, description="音频文件相对路径")
    data: dict[str, Any] = Field(default_factory=dict, description="场景特有的数据载荷")
    word_timings: list[WordTiming] = Field(default_factory=list, description="字级时间戳")


VIDEO_PRESETS: dict[str, tuple[int, int]] = {
    "landscape": (1920, 1080),
    "bilibili": (1920, 1080),
    "portrait": (1080, 1920),
    "douyin": (1080, 1920),
    "xiaohongshu": (1080, 1440),
    "square": (1080, 1080),
}


class VideoMeta(BaseModel):
    fps: int = 30
    width: int = 1920
    height: int = 1080
    theme: str = "academic"


class VideoScript(BaseModel):
    meta: VideoMeta = Field(default_factory=VideoMeta)
    scenes: list[Scene] = Field(default_factory=list)

    @property
    def total_duration_in_frames(self) -> int:
        return sum(s.duration_in_frames for s in self.scenes)

    @property
    def total_duration_seconds(self) -> float:
        return self.total_duration_in_frames / self.meta.fps


# ---------------------------------------------------------------------------
# 流水线输入参数（Pydantic 模型，用于入口验证）
# ---------------------------------------------------------------------------


class PipelineInput(BaseModel):
    """用户输入参数，在 run_pipeline 入口处验证后展平注入 PipelineState。"""

    pdf_path: str
    workspace: str
    language: str = "zh"
    video_preset: str = "landscape"
    fps: int = 30
    skip_tts: bool = False
    skip_render: bool = False
    use_cache: bool = True
    narration_style: str = "default"
    theme: str = "academic"
    speech_rate: int = 0
    output_path: str | None = None
    interactive_mode: bool = False

    extract_model: str = "gpt-4o"
    scan_model: str = "gpt-4o-mini"
    script_model: str = "gpt-4o-mini"
    figure_model: str = "gpt-4o"
    tts_voice: str | None = None
    mineru_backend: str = "pipeline"

    llm_model: str = "gpt-4o"
    extract_api_key: str | None = None
    extract_api_base: str | None = None
    script_api_key: str | None = None
    script_api_base: str | None = None
    figure_api_key: str | None = None
    figure_api_base: str | None = None


# ---------------------------------------------------------------------------
# 流水线上下文（向后兼容）
# ---------------------------------------------------------------------------


class PipelineContext(BaseModel):
    """在流水线中传递路径和中间结果。"""

    input_pdf: Path
    workspace: Path
    parsed_dir: Path | None = None
    markdown_content: str | None = None
    paper_summary: PaperSummary | None = None
    video_script: VideoScript | None = None
    output_video: Path | None = None
