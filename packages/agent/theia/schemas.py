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


class KeyConcept(BaseModel):
    """核心概念，可用于 concept 场景。"""

    term: str = Field(description="术语名称（如 Multi-Head Attention）")
    definition: str = Field(description="一句话通俗定义（面向非专业观众）")
    related_terms: list[str] = Field(default_factory=list, description="关联术语")


class Analogy(BaseModel):
    """技术类比，可用于 analogy 场景。"""

    concept: str = Field(description="技术概念")
    analogy: str = Field(description="日常生活类比")
    mapping: str = Field(default="", description="类比映射说明")


class ComponentRelation(BaseModel):
    """组件间依赖关系，可用于 relationship 场景。"""

    source: str = Field(description="源组件")
    target: str = Field(description="目标组件")
    relation: str = Field(description="关系描述（如 '输出传入', '依赖于'）")


class MethodDetail(BaseModel):
    summary: str = Field(description="方法概述（一段话）")
    key_steps: list[str] = Field(default_factory=list, description="有序的方法步骤")
    formulas: list[str] = Field(default_factory=list, description="关键公式（LaTeX 格式）")
    component_relations: list[ComponentRelation] = Field(
        default_factory=list,
        description="组件间依赖关系（用于 relationship 场景）",
    )


class BaselineResult(BaseModel):
    name: str
    metric: str
    value: float | None = None
    highlight: bool = False
    dataset: str = Field(default="", description="所属数据集（可选，用于区分多数据集结果）")

    @field_validator("value", mode="before")
    @classmethod
    def _coerce_value(cls, v: object) -> float | None:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            s = s.replace("%", "").replace(",", "").replace("％", "").strip()
            try:
                return float(s)
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
    key_concepts: list[KeyConcept] = Field(
        default_factory=list,
        description="核心概念列表（用于 concept 场景）",
    )
    analogies: list[Analogy] = Field(
        default_factory=list,
        description="技术类比列表（用于 analogy 场景）",
    )
    code_snippets: list[str] = Field(
        default_factory=list,
        description="代码片段/伪代码列表（用于 code_demo 场景）",
    )
    audience_takeaways: list[str] = Field(
        default_factory=list,
        description="面向普通观众的精炼要点（用于 summary_card/character_talk 场景）",
    )


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


# ---------------------------------------------------------------------------
# Manim 动画集成模型
# ---------------------------------------------------------------------------


class ManimAnimationType(str, Enum):
    FORMULA_WRITE = "formula_write"
    FORMULA_TRANSFORM = "formula_transform"
    FORMULA_DERIVATION = "formula_derivation"
    FORMULA_HIGHLIGHT = "formula_highlight"
    FORMULA_MULTILINE = "formula_multiline"
    GRAPH_PLOT = "graph_plot"
    COORDINATE_SYSTEM = "coordinate_system"
    GEOMETRY = "geometry"
    VECTOR_FIELD = "vector_field"
    THREE_D_SURFACE = "3d_surface"
    CUSTOM = "custom"


class ManimAnimationSpec(BaseModel):
    """描述一个需要 Manim 渲染的动画。由 Visual Director 生成。"""

    type: ManimAnimationType
    formulas: list[str] = Field(default_factory=list, description="LaTeX 公式列表")
    config: dict[str, Any] = Field(default_factory=dict, description="动画类型专属配置")
    duration_hint_sec: float = Field(default=3.0, description="期望时长（秒）")
    position: str = Field(default="center", description="在场景中的位置: center|left|right|full")


class ManimClip(BaseModel):
    """Manim 渲染后的视频片段元数据。"""

    clip_path: str = Field(description="相对于 workspace 的视频文件路径")
    start_ms: int = Field(default=0, description="在场景中开始播放的时间（毫秒）")
    duration_ms: int = Field(description="片段时长（毫秒）")
    position: str = Field(default="center", description="在场景中的位置: center|left|right|full")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)


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
    choreography: list[AnimationPhase] = Field(
        default_factory=list,
        description="视觉导演生成的动画编排阶段（空则使用组件默认时序）",
    )
    manim_animations: list[ManimAnimationSpec] = Field(
        default_factory=list,
        description="需要 Manim 预渲染的动画规格（由 Visual Director 填充）",
    )
    manim_clips: list[ManimClip] = Field(
        default_factory=list,
        description="Manim 渲染后的视频片段（由 manim_render_node 填充）",
    )


VIDEO_PRESETS: dict[str, tuple[int, int]] = {
    "landscape": (1920, 1080),
    "bilibili": (1920, 1080),
    "portrait": (1080, 1920),
    "douyin": (1080, 1920),
    "xiaohongshu": (1080, 1440),
    "square": (1080, 1080),
}


# ---------------------------------------------------------------------------
# 多 Agent 视频编排模型
# ---------------------------------------------------------------------------


class ScenePlan(BaseModel):
    """故事架构师为单个场景生成的规划。"""

    type: str = Field(description="场景类型，如 title/overview/method/formula/figure/result/conclusion")
    target_duration_range: tuple[float, float] = Field(description="目标时长范围 (min_sec, max_sec)")
    narrative_role: str = Field(
        description="叙事角色: hook | build_up | climax | resolution | transition"
    )
    attention_strategy: str = Field(
        default="synced",
        description="该场景的主要注意力策略: voice_primary | visual_primary | synced",
    )
    key_moment: bool = Field(default=False, description="是否为全片关键信息点")
    narration_word_range: tuple[int, int] = Field(
        default=(50, 150),
        description="旁白字数范围 (min_chars, max_chars)",
    )


class StoryBlueprint(BaseModel):
    """故事架构师的完整输出：全片叙事规划。"""

    narrative_arc: str = Field(description="一句话描述叙事弧线")
    scenes: list[ScenePlan] = Field(description="有序场景规划列表")
    total_target_duration: tuple[float, float] = Field(
        default=(120.0, 240.0),
        description="目标总时长范围 (min_sec, max_sec)",
    )
    key_moments: list[str] = Field(
        default_factory=list,
        description="全片 2-3 个最重要的信息点描述",
    )


class AttentionMarker(BaseModel):
    """旁白文本中的注意力模式切换标注。"""

    char_offset: int = Field(description="旁白文本中的字符位置")
    mode_switch_to: str = Field(description="voice_primary | visual_primary | synced")
    visual_hint: str = Field(
        default="",
        description="pause | reveal | highlight | dim_others",
    )


class SceneNarration(BaseModel):
    """场景编剧为单个场景生成的旁白及标注。"""

    scene_index: int = Field(description="对应 StoryBlueprint.scenes 的索引")
    narration: str = Field(description="旁白文本")
    data: dict[str, Any] = Field(default_factory=dict, description="场景特有的数据载荷")
    attention_markers: list[AttentionMarker] = Field(
        default_factory=list,
        description="旁白中的注意力模式切换点",
    )
    pause_points: list[int] = Field(
        default_factory=list,
        description="旁白中需要自然停顿的字符位置",
    )


class AnimationPhase(BaseModel):
    """视觉导演定义的单个动画阶段。"""

    start_ms: int = Field(description="阶段开始时间（相对场景起点，毫秒）")
    end_ms: int = Field(description="阶段结束时间（相对场景起点，毫秒）")
    attention_mode: str = Field(
        default="synced",
        description="voice_primary | visual_primary | synced",
    )
    elements_to_show: list[str] = Field(
        default_factory=list,
        description="该阶段应可见的元素标识（如 'image', 'caption', 'step_0', 'formula'）",
    )
    highlight_element: str | None = Field(
        default=None,
        description="当前高亮元素标识",
    )
    transition_type: str = Field(
        default="fade_in",
        description="过渡动画类型: fade_in | slide_in | scale_in | none",
    )


class VisualChoreography(BaseModel):
    """视觉导演为单个场景生成的完整动画编排。"""

    scene_index: int = Field(description="对应场景索引")
    phases: list[AnimationPhase] = Field(default_factory=list)


class ReviewResult(BaseModel):
    """节奏审核员的审核结果。"""

    approved: bool = Field(description="是否通过审核")
    revision_target: str = Field(
        default="",
        description="需要修改的目标: narration | choreography | both | (空=通过)",
    )
    issues: list[str] = Field(default_factory=list, description="发现的问题列表")
    suggestions: list[str] = Field(default_factory=list, description="具体修改建议")


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

    # --- 模型配置（每个步骤独立） ---
    extract_model: str = "kimi-k2-0905-preview"
    scan_model: str = "kimi-k2-0905-preview"
    figure_model: str = "kimi-k2.5"
    story_model: str = "kimi-k2-0905-preview"
    scene_model: str = "kimi-k2-0905-preview"
    gate_model: str = "kimi-k2-0905-preview"
    judge_model: str = "kimi-k2-0905-preview"
    script_model: str = "kimi-k2-0905-preview"
    tts_voice: str | None = None
    mineru_backend: str = "pipeline"

    llm_model: str = "kimi-k2-0905-preview"
    extract_api_key: str | None = None
    extract_api_base: str | None = None
    scan_api_key: str | None = None
    scan_api_base: str | None = None
    figure_api_key: str | None = None
    figure_api_base: str | None = None
    story_api_key: str | None = None
    story_api_base: str | None = None
    scene_api_key: str | None = None
    scene_api_base: str | None = None
    gate_api_key: str | None = None
    gate_api_base: str | None = None
    judge_api_key: str | None = None
    judge_api_base: str | None = None
    script_api_key: str | None = None
    script_api_base: str | None = None


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
