from __future__ import annotations

from dataclasses import dataclass, field

_REGISTRY: dict[str, "SceneSpec"] = {}


@dataclass(frozen=True)
class SceneSpec:
    """单个场景类型的完整规格。"""

    name: str
    category: str
    description: str
    duration_bounds: tuple[float, float]
    narration_word_range: tuple[int, int]
    visual_pause_sec: float
    min_scene_sec: float
    data_schema: dict[str, str]
    remotion_component: str
    template_phases: list[dict] = field(default_factory=list)
    narration_guide: str = ""
    attention_default: str = "synced"
    manim_capable: bool = False
    skip_aux_figures: bool = False


def _register(spec: SceneSpec) -> None:
    _REGISTRY[spec.name] = spec


_register(
    SceneSpec(
        name="title",
        category="universal",
        description="论文标题与作者信息展示",
        duration_bounds=(5.0, 10.0),
        narration_word_range=(15, 35),
        visual_pause_sec=0.0,
        min_scene_sec=5.0,
        data_schema={"title": "str", "authors": "list[str]", "year": "int"},
        remotion_component="TitleScene",
        template_phases=[
            {
                "pct_start": 0.0,
                "pct_end": 1.0,
                "mode": "voice_primary",
                "elements": ["title", "authors", "year"],
                "transition": "fade_in",
            }
        ],
        narration_guide="一句简短的开场白引出论文名称。不要放 hook、数据预告或背景铺垫。",
        attention_default="voice_primary",
    )
)

_register(
    SceneSpec(
        name="overview",
        category="universal",
        description="研究问题与贡献概览",
        duration_bounds=(15.0, 35.0),
        narration_word_range=(60, 120),
        visual_pause_sec=0.0,
        min_scene_sec=15.0,
        data_schema={"problem": "str", "contributions": "list[str]"},
        remotion_component="OverviewScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.3, "mode": "voice_primary", "elements": ["problem"], "transition": "fade_in"},
            {"pct_start": 0.3, "pct_end": 1.0, "mode": "synced", "elements": ["problem", "contributions"], "transition": "slide_in"},
        ],
        narration_guide="用一个出人意料的事实/问题/反常识作为 hook 开场。可以预告最亮眼的成果数据。铺垫研究背景，引出核心思路。结尾过渡到方法讲解。",
    )
)

_register(
    SceneSpec(
        name="conclusion",
        category="universal",
        description="论文结论与贡献总结",
        duration_bounds=(10.0, 22.0),
        narration_word_range=(40, 80),
        visual_pause_sec=0.0,
        min_scene_sec=10.0,
        data_schema={"conclusion": "str", "contributions": "list[str]"},
        remotion_component="ConclusionScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.3, "mode": "voice_primary", "elements": ["conclusion"], "transition": "fade_in"},
            {"pct_start": 0.3, "pct_end": 1.0, "mode": "synced", "elements": ["conclusion", "contributions"], "transition": "fade_in"},
        ],
        narration_guide="一句话概括论文成果。展望未来或发人深省的收尾。",
    )
)

_register(
    SceneSpec(
        name="method",
        category="academic",
        description="方法步骤讲解",
        duration_bounds=(15.0, 35.0),
        narration_word_range=(60, 120),
        visual_pause_sec=2.0,
        min_scene_sec=15.0,
        data_schema={"summary": "str", "steps": "list[str]"},
        remotion_component="MethodScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["summary"], "transition": "fade_in"}
        ],
        narration_guide="先概括方法核心直觉，再按步骤讲解。不详细解释公式。结尾引向公式或下一个场景。",
        manim_capable=True,
    )
)

_register(
    SceneSpec(
        name="formula",
        category="academic",
        description="公式展示与解释",
        duration_bounds=(15.0, 30.0),
        narration_word_range=(55, 100),
        visual_pause_sec=5.0,
        min_scene_sec=15.0,
        data_schema={"formula": "str", "explanation": "str", "title": "str"},
        remotion_component="FormulaScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.12, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
            {"pct_start": 0.12, "pct_end": 0.35, "mode": "visual_primary", "elements": ["title", "formula"], "transition": "scale_in"},
            {"pct_start": 0.35, "pct_end": 1.0, "mode": "synced", "elements": ["title", "formula", "explanation"], "transition": "fade_in"},
        ],
        narration_guide="引出公式 → 停顿 → 解释核心含义（不逐符号解释，只讲直觉）。语速放慢，用'...'表示停顿。",
        attention_default="visual_primary",
        manim_capable=True,
        skip_aux_figures=True,
    )
)

_register(
    SceneSpec(
        name="figure",
        category="academic",
        description="图表展示与解读",
        duration_bounds=(12.0, 25.0),
        narration_word_range=(50, 85),
        visual_pause_sec=4.0,
        min_scene_sec=12.0,
        data_schema={"figurePath": "str", "caption": "str", "description": "str"},
        remotion_component="FigureScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.2, "mode": "visual_primary", "elements": ["image"], "transition": "scale_in"},
            {"pct_start": 0.2, "pct_end": 0.35, "mode": "visual_primary", "elements": ["image"], "transition": "none"},
            {"pct_start": 0.35, "pct_end": 1.0, "mode": "synced", "elements": ["image", "caption", "description"], "transition": "fade_in"},
        ],
        narration_guide="'我们来看这张图...' → 停顿 → 描述关键信息。先给观众看图时间，再讲解。",
        attention_default="visual_primary",
        skip_aux_figures=True,
    )
)

_register(
    SceneSpec(
        name="result",
        category="academic",
        description="实验结果与数据对比",
        duration_bounds=(15.0, 32.0),
        narration_word_range=(60, 110),
        visual_pause_sec=2.0,
        min_scene_sec=15.0,
        data_schema={"datasets": "list[str]", "metrics": "list[str]", "baselines": "list[dict]", "findings": "str"},
        remotion_component="ResultScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["datasets"], "transition": "fade_in"},
            {"pct_start": 0.15, "pct_end": 1.0, "mode": "synced", "elements": ["datasets", "metrics", "findings"], "transition": "slide_in"},
        ],
        narration_guide="用对比方式呈现数据。提到具体的数据集和数字。",
        manim_capable=True,
    )
)

_register(
    SceneSpec(
        name="concept",
        category="popsci",
        description="术语概念解释",
        duration_bounds=(12.0, 25.0),
        narration_word_range=(50, 90),
        visual_pause_sec=1.0,
        min_scene_sec=12.0,
        data_schema={"term": "str", "definition": "str", "related_terms": "list[str]"},
        remotion_component="ConceptScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.2, "mode": "voice_primary", "elements": ["term"], "transition": "fade_in"},
            {"pct_start": 0.2, "pct_end": 0.5, "mode": "synced", "elements": ["term", "definition"], "transition": "scale_in"},
            {"pct_start": 0.5, "pct_end": 1.0, "mode": "synced", "elements": ["term", "definition", "related_terms"], "transition": "fade_in"},
        ],
        narration_guide="先抛出术语，停顿让观众产生好奇。然后用通俗语言给出定义。最后关联到论文方法中的角色。",
        manim_capable=True,
    )
)

_register(
    SceneSpec(
        name="analogy",
        category="popsci",
        description="类比解释技术概念",
        duration_bounds=(15.0, 28.0),
        narration_word_range=(60, 100),
        visual_pause_sec=0.0,
        min_scene_sec=15.0,
        data_schema={"concept": "str", "analogy": "str", "mapping": "str"},
        remotion_component="AnalogyScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.35, "mode": "voice_primary", "elements": ["concept"], "transition": "fade_in"},
            {"pct_start": 0.35, "pct_end": 0.65, "mode": "visual_primary", "elements": ["concept", "analogy"], "transition": "slide_in"},
            {"pct_start": 0.65, "pct_end": 1.0, "mode": "synced", "elements": ["concept", "analogy", "mapping"], "transition": "fade_in"},
        ],
        narration_guide="先描述技术概念的核心特征。然后引出类比：'这就好比...'。最后解释类比的对应关系。",
    )
)

_register(
    SceneSpec(
        name="comparison",
        category="popsci",
        description="对比表格展示",
        duration_bounds=(12.0, 25.0),
        narration_word_range=(50, 90),
        visual_pause_sec=2.0,
        min_scene_sec=12.0,
        data_schema={"title": "str", "columns": "list[dict]", "highlight_column": "str"},
        remotion_component="ComparisonScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
            {"pct_start": 0.15, "pct_end": 1.0, "mode": "synced", "elements": ["title", "table"], "transition": "slide_in"},
        ],
        narration_guide="先说明对比的维度和方法。然后逐列解读表格亮点。最后总结本文方法的优势。",
        manim_capable=True,
    )
)

_register(
    SceneSpec(
        name="relationship",
        category="popsci",
        description="关系图与架构展示",
        duration_bounds=(15.0, 28.0),
        narration_word_range=(60, 100),
        visual_pause_sec=2.0,
        min_scene_sec=15.0,
        data_schema={"title": "str", "nodes": "list[dict]", "edges": "list[dict]"},
        remotion_component="RelationshipScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
            {"pct_start": 0.15, "pct_end": 0.5, "mode": "visual_primary", "elements": ["nodes"], "transition": "scale_in"},
            {"pct_start": 0.5, "pct_end": 1.0, "mode": "synced", "elements": ["nodes", "edges"], "transition": "fade_in"},
        ],
        narration_guide="先介绍系统的整体架构。然后逐步揭示各组件及其连接。最后强调关键数据流。",
        manim_capable=True,
    )
)

_register(
    SceneSpec(
        name="demo",
        category="popsci",
        description="演示场景展示",
        duration_bounds=(12.0, 25.0),
        narration_word_range=(40, 80),
        visual_pause_sec=3.0,
        min_scene_sec=12.0,
        data_schema={"demo_type": "str", "title": "str", "content": "str"},
        remotion_component="DemoScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.1, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
            {"pct_start": 0.1, "pct_end": 1.0, "mode": "visual_primary", "elements": ["title", "content"], "transition": "scale_in"},
        ],
        narration_guide="先简要介绍演示场景。然后逐步展示操作过程。最后总结演示效果。",
        attention_default="visual_primary",
        skip_aux_figures=True,
    )
)

_register(
    SceneSpec(
        name="code_demo",
        category="popsci",
        description="代码演示与讲解",
        duration_bounds=(12.0, 25.0),
        narration_word_range=(40, 80),
        visual_pause_sec=3.0,
        min_scene_sec=12.0,
        data_schema={"language": "str", "code": "str", "highlights": "list[int]", "title": "str"},
        remotion_component="CodeDemoScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.1, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
            {"pct_start": 0.1, "pct_end": 0.4, "mode": "visual_primary", "elements": ["code"], "transition": "scale_in"},
            {"pct_start": 0.4, "pct_end": 1.0, "mode": "synced", "elements": ["code", "highlights"], "transition": "none"},
        ],
        narration_guide="先介绍代码的功能。然后逐段讲解核心逻辑。高亮部分配合语音重点强调。",
        attention_default="visual_primary",
        skip_aux_figures=True,
    )
)

_register(
    SceneSpec(
        name="character_talk",
        category="popsci",
        description="角色对话式讲解",
        duration_bounds=(10.0, 20.0),
        narration_word_range=(40, 70),
        visual_pause_sec=0.0,
        min_scene_sec=10.0,
        data_schema={"character": "str", "topic": "str", "talking_points": "list[str]"},
        remotion_component="CharacterTalkScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["character"], "transition": "scale_in"},
            {"pct_start": 0.15, "pct_end": 1.0, "mode": "synced", "elements": ["character", "talking_points"], "transition": "fade_in"},
        ],
        narration_guide="用轻松对话的语气讲解。每个要点用一两句话说清。穿插提问引发思考。",
        skip_aux_figures=True,
    )
)

_register(
    SceneSpec(
        name="summary_card",
        category="popsci",
        description="要点总结卡片",
        duration_bounds=(10.0, 20.0),
        narration_word_range=(30, 60),
        visual_pause_sec=0.0,
        min_scene_sec=10.0,
        data_schema={"title": "str", "items": "list[dict]"},
        remotion_component="SummaryCardScene",
        template_phases=[
            {"pct_start": 0.0, "pct_end": 0.1, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
            {"pct_start": 0.1, "pct_end": 1.0, "mode": "synced", "elements": ["title", "items"], "transition": "slide_in"},
        ],
        narration_guide="逐条读出要点，每条之间留短停顿。最后做一句总结。",
    )
)

SCENE_BUDGET: dict[str, tuple[int, int]] = {
    "academic": (5, 10),
    "popsci": (7, 12),
}


def get_spec(scene_type: str) -> SceneSpec:
    """查询单个场景规格。未找到时 raise KeyError。"""
    return _REGISTRY[scene_type]


def get_duration_bounds() -> dict[str, tuple[float, float]]:
    """返回所有场景的时长约束，用于 Pacing Reviewer。"""
    return {k: v.duration_bounds for k, v in _REGISTRY.items()}


def get_templates() -> dict[str, list[dict]]:
    """返回所有场景的编排模板，用于 Visual Director。"""
    return {k: v.template_phases for k, v in _REGISTRY.items()}


def get_narration_guides() -> dict[str, str]:
    """返回所有场景的旁白写作要求，用于 Scene Writer prompt。"""
    return {k: v.narration_guide for k, v in _REGISTRY.items()}


def get_data_schemas() -> dict[str, dict[str, str]]:
    """返回所有场景的 data 字段 schema。"""
    return {k: v.data_schema for k, v in _REGISTRY.items()}


def get_word_ranges() -> dict[str, tuple[int, int]]:
    """返回所有场景的旁白字数范围，用于 Story Architect prompt。"""
    return {k: v.narration_word_range for k, v in _REGISTRY.items()}


def get_visual_pauses() -> dict[str, float]:
    """返回所有场景的视觉停顿秒数。"""
    return {k: v.visual_pause_sec for k, v in _REGISTRY.items()}


def get_min_scene_seconds() -> dict[str, float]:
    """返回所有场景的最低时长下限。"""
    return {k: v.min_scene_sec for k, v in _REGISTRY.items()}


def get_skip_aux_figures_set() -> set[str]:
    """返回应跳过辅助图片分配的场景类型集合。"""
    return {k for k, v in _REGISTRY.items() if v.skip_aux_figures}


def list_by_category(category: str) -> list[SceneSpec]:
    """按分类列出场景。"""
    return [v for v in _REGISTRY.values() if v.category == category]


def all_scene_types() -> list[str]:
    """返回所有已注册场景类型名称。"""
    return list(_REGISTRY.keys())
