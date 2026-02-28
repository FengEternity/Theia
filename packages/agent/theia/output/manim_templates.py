"""Manim 场景代码模板。

每个模板是一段可参数化的 Python 代码字符串，通过 string.Template
安全替换后写入临时 .py 文件，由 ``manim render`` CLI 渲染。

设计原则：
- 使用 string.Template ($var) 而非 str.format 以避免花括号冲突
- 每个模板产出一个 Scene 子类
- 背景色、字体大小、颜色等可由调用方覆盖
"""

from __future__ import annotations

from string import Template
from typing import Any

from ..schemas import ManimAnimationType

# ---------------------------------------------------------------------------
# 模板常量
# ---------------------------------------------------------------------------

FORMULA_WRITE_TEMPLATE = Template(r"""from manim import *

class FormulaWrite(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        tex = MathTex(r"$formula", font_size=$font_size)
        tex.set_color("$text_color")
        self.play(Write(tex), run_time=$run_time)
        self.wait($wait_time)
""")

FORMULA_TRANSFORM_TEMPLATE = Template(r"""from manim import *

class FormulaTransform(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        formulas = $formulas
        prev = MathTex(formulas[0], font_size=$font_size).set_color("$text_color")
        self.play(Write(prev), run_time=1.0)
        for f in formulas[1:]:
            next_tex = MathTex(f, font_size=$font_size).set_color("$text_color")
            self.play(TransformMatchingTex(prev, next_tex), run_time=$run_time)
            self.wait(0.3)
            prev = next_tex
        self.wait($wait_time)
""")

FORMULA_DERIVATION_TEMPLATE = Template(r"""from manim import *

class FormulaDerivation(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        formulas = $formulas
        prev = MathTex(formulas[0], font_size=$font_size).set_color("$text_color")
        self.play(Write(prev), run_time=1.2)
        for i, f in enumerate(formulas[1:], 1):
            next_tex = MathTex(f, font_size=$font_size).set_color("$text_color")
            arrow = MathTex(r"\Downarrow", font_size=$font_size).set_color("$accent_color")
            group = VGroup(prev, arrow, next_tex).arrange(DOWN, buff=0.5)
            self.play(
                FadeIn(arrow, shift=DOWN * 0.3),
                TransformMatchingTex(prev.copy(), next_tex),
                run_time=$run_time,
            )
            self.wait(0.4)
            if i < len(formulas) - 1:
                self.play(FadeOut(arrow), next_tex.animate.move_to(ORIGIN), run_time=0.5)
            prev = next_tex
        self.wait($wait_time)
""")

GRAPH_PLOT_TEMPLATE = Template(r"""from manim import *
import numpy as np

class GraphPlot(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        axes = Axes(
            x_range=$x_range,
            y_range=$y_range,
            x_length=$x_length,
            y_length=$y_length,
            axis_config={"color": "$axis_color", "include_tip": True},
        )
        labels = axes.get_axis_labels(
            x_label=MathTex("$x_label").set_color("$text_color"),
            y_label=MathTex("$y_label").set_color("$text_color"),
        )
        self.play(Create(axes), Write(labels), run_time=1.5)
$plot_commands
        self.wait($wait_time)
""")

COORDINATE_SYSTEM_TEMPLATE = Template(r"""from manim import *
import numpy as np

class CoordinateSystem(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        plane = NumberPlane(
            x_range=$x_range,
            y_range=$y_range,
            background_line_style={"stroke_color": "$grid_color", "stroke_opacity": 0.4},
        )
        self.play(Create(plane), run_time=1.5)
$draw_commands
        self.wait($wait_time)
""")

GEOMETRY_TEMPLATE = Template(r"""from manim import *

class Geometry(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
$geometry_commands
        self.wait($wait_time)
""")

VECTOR_FIELD_TEMPLATE = Template(r"""from manim import *
import numpy as np

class VectorFieldScene(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        plane = NumberPlane(
            x_range=$x_range,
            y_range=$y_range,
            background_line_style={"stroke_color": "$grid_color", "stroke_opacity": 0.3},
        )
        self.play(Create(plane), run_time=1.0)
        func = lambda pos: $vector_func
        field = ArrowVectorField(func, x_range=$x_range[:2], y_range=$y_range[:2])
        self.play(Create(field), run_time=$run_time)
        self.wait($wait_time)
""")

THREE_D_SURFACE_TEMPLATE = Template(r"""from manim import *
import numpy as np

class ThreeDSurface(ThreeDScene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        axes = ThreeDAxes(
            x_range=$x_range,
            y_range=$y_range,
            z_range=$z_range,
        )
        surface = Surface(
            lambda u, v: axes.c2p(u, v, $surface_func),
            u_range=$u_range,
            v_range=$v_range,
            resolution=(32, 32),
        )
        surface.set_style(fill_opacity=0.7)
        surface.set_fill_by_value(axes=axes, colorscale=[BLUE, GREEN, YELLOW], axis=2)

        self.set_camera_orientation(phi=60 * DEGREES, theta=-45 * DEGREES)
        self.play(Create(axes), run_time=1.0)
        self.play(Create(surface), run_time=$run_time)
        self.begin_ambient_camera_rotation(rate=0.15)
        self.wait($wait_time)
        self.stop_ambient_camera_rotation()
""")

FORMULA_HIGHLIGHT_TEMPLATE = Template(r"""from manim import *

class FormulaHighlight(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        title = Text("$title_text", font_size=32, color="$accent_color")
        title.to_edge(UP, buff=0.6)

        formula = MathTex(r"$formula", font_size=$font_size)
        formula.set_color("$text_color")

        self.play(Write(title), run_time=0.6)
        self.play(Write(formula), run_time=$run_time)
        self.wait(0.3)

        highlights = $highlights
        for start, end, color in highlights:
            self.play(
                formula[0][start:end].animate.set_color(color),
                run_time=0.4,
            )
            self.wait(0.2)
        self.wait($wait_time)
""")

FORMULA_MULTILINE_TEMPLATE = Template(r"""from manim import *

class FormulaMultiline(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        formulas = $formulas
        tex_group = VGroup()
        for f in formulas:
            tex = MathTex(f, font_size=$font_size)
            tex.set_color("$text_color")
            tex_group.add(tex)
        tex_group.arrange(DOWN, buff=0.6, aligned_edge=LEFT)
        if tex_group.width > 12:
            tex_group.scale_to_fit_width(12)
        if tex_group.height > 6:
            tex_group.scale_to_fit_height(6)

        for tex in tex_group:
            self.play(Write(tex), run_time=$run_time)
            self.wait(0.15)
        self.wait($wait_time)
""")

CUSTOM_TEMPLATE = Template(r"""from manim import *
import numpy as np
$custom_code
""")

# ---------------------------------------------------------------------------
# LaTeX 降级模板: 使用 Text 替代 MathTex
# ---------------------------------------------------------------------------

FORMULA_WRITE_NO_LATEX_TEMPLATE = Template(r"""from manim import *
import re

def clean_latex(s):
    s = s.strip()
    for d in [r'\[', r'\]', '$$']:
        s = s.replace(d, '')
    s = re.sub(r'\\text\{([^}]+)\}', r'\1', s)
    s = re.sub(r'\\(?:mathbf|mathrm|mathcal|boldsymbol)\{([^}]+)\}', r'\1', s)
    s = re.sub(r'\\(?:left|right|Big|big)[|()\\]?', '', s)
    s = s.replace(r'\frac', '').replace('{', '(').replace('}', ')')
    for cmd in [r'\alpha', r'\beta', r'\gamma', r'\theta', r'\sigma', r'\mu',
                r'\lambda', r'\pi', r'\epsilon', r'\delta', r'\nabla', r'\infty']:
        s = s.replace(cmd, cmd[1:])
    s = s.replace(r'\cdot', '·').replace(r'\times', '×').replace(r'\sqrt', '√')
    s = s.replace(r'\sum', 'Σ').replace(r'\prod', 'Π').replace(r'\int', '∫')
    s = s.replace(r'\leq', '≤').replace(r'\geq', '≥').replace(r'\neq', '≠')
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

class FormulaWrite(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        raw = r"$formula"
        cleaned = clean_latex(raw)
        tex = Text(cleaned, font_size=min($font_size, 36), color="$text_color")
        if tex.width > 12:
            tex.scale_to_fit_width(12)
        self.play(Write(tex), run_time=$run_time)
        self.wait($wait_time)
""")

FORMULA_TRANSFORM_NO_LATEX_TEMPLATE = Template(r"""from manim import *
import re

def clean_latex(s):
    s = s.strip()
    for d in [r'\[', r'\]', '$$']:
        s = s.replace(d, '')
    s = re.sub(r'\\text\{([^}]+)\}', r'\1', s)
    s = re.sub(r'\\(?:mathbf|mathrm|mathcal)\{([^}]+)\}', r'\1', s)
    s = re.sub(r'\\(?:left|right|Big|big)[|()\\]?', '', s)
    s = s.replace(r'\frac', '').replace('{', '(').replace('}', ')')
    s = s.replace(r'\cdot', '·').replace(r'\times', '×').replace(r'\sqrt', '√')
    s = s.replace(r'\sum', 'Σ').replace(r'\prod', 'Π').replace(r'\int', '∫')
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

class FormulaTransform(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        formulas = [clean_latex(f) for f in $formulas]
        prev = Text(formulas[0], font_size=min($font_size, 32), color="$text_color")
        if prev.width > 12:
            prev.scale_to_fit_width(12)
        self.play(Write(prev), run_time=1.0)
        for f in formulas[1:]:
            next_text = Text(f, font_size=min($font_size, 32), color="$text_color")
            if next_text.width > 12:
                next_text.scale_to_fit_width(12)
            self.play(Transform(prev, next_text), run_time=$run_time)
            self.wait(0.3)
            prev = next_text
        self.wait($wait_time)
""")

FORMULA_DERIVATION_NO_LATEX_TEMPLATE = Template(r"""from manim import *
import re

def clean_latex(s):
    s = s.strip()
    for d in [r'\[', r'\]', '$$']:
        s = s.replace(d, '')
    s = re.sub(r'\\text\{([^}]+)\}', r'\1', s)
    s = re.sub(r'\\(?:mathbf|mathrm|mathcal)\{([^}]+)\}', r'\1', s)
    s = re.sub(r'\\(?:left|right|Big|big)[|()\\]?', '', s)
    s = s.replace(r'\frac', '').replace('{', '(').replace('}', ')')
    s = s.replace(r'\cdot', '·').replace(r'\times', '×').replace(r'\sqrt', '√')
    s = s.replace(r'\sum', 'Σ').replace(r'\prod', 'Π').replace(r'\int', '∫')
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

class FormulaDerivation(Scene):
    def construct(self):
        self.camera.background_color = "$bg_color"
        formulas = [clean_latex(f) for f in $formulas]
        fs = min($font_size, 30)
        prev = Text(formulas[0], font_size=fs, color="$text_color")
        if prev.width > 11:
            prev.scale_to_fit_width(11)
        self.play(Write(prev), run_time=1.2)
        for i, f in enumerate(formulas[1:], 1):
            next_text = Text(f, font_size=fs, color="$text_color")
            if next_text.width > 11:
                next_text.scale_to_fit_width(11)
            arrow = Text("↓", font_size=int(fs * 1.2), color="$accent_color")
            group = VGroup(prev, arrow, next_text).arrange(DOWN, buff=0.5)
            self.play(
                FadeIn(arrow, shift=DOWN * 0.3),
                Transform(prev.copy(), next_text),
                run_time=$run_time,
            )
            self.wait(0.4)
            if i < len(formulas) - 1:
                self.play(FadeOut(arrow), next_text.animate.move_to(ORIGIN), run_time=0.5)
            prev = next_text
        self.wait($wait_time)
""")

# ---------------------------------------------------------------------------
# 模板注册表
# ---------------------------------------------------------------------------

TEMPLATE_REGISTRY: dict[str, tuple[Template, str]] = {
    ManimAnimationType.FORMULA_WRITE: (FORMULA_WRITE_TEMPLATE, "FormulaWrite"),
    ManimAnimationType.FORMULA_TRANSFORM: (FORMULA_TRANSFORM_TEMPLATE, "FormulaTransform"),
    ManimAnimationType.FORMULA_DERIVATION: (FORMULA_DERIVATION_TEMPLATE, "FormulaDerivation"),
    ManimAnimationType.FORMULA_HIGHLIGHT: (FORMULA_HIGHLIGHT_TEMPLATE, "FormulaHighlight"),
    ManimAnimationType.FORMULA_MULTILINE: (FORMULA_MULTILINE_TEMPLATE, "FormulaMultiline"),
    ManimAnimationType.GRAPH_PLOT: (GRAPH_PLOT_TEMPLATE, "GraphPlot"),
    ManimAnimationType.COORDINATE_SYSTEM: (COORDINATE_SYSTEM_TEMPLATE, "CoordinateSystem"),
    ManimAnimationType.GEOMETRY: (GEOMETRY_TEMPLATE, "Geometry"),
    ManimAnimationType.VECTOR_FIELD: (VECTOR_FIELD_TEMPLATE, "VectorFieldScene"),
    ManimAnimationType.THREE_D_SURFACE: (THREE_D_SURFACE_TEMPLATE, "ThreeDSurface"),
    ManimAnimationType.CUSTOM: (CUSTOM_TEMPLATE, "CustomScene"),
}

NO_LATEX_FALLBACK: dict[str, tuple[Template, str]] = {
    ManimAnimationType.FORMULA_WRITE: (FORMULA_WRITE_NO_LATEX_TEMPLATE, "FormulaWrite"),
    ManimAnimationType.FORMULA_TRANSFORM: (FORMULA_TRANSFORM_NO_LATEX_TEMPLATE, "FormulaTransform"),
    ManimAnimationType.FORMULA_DERIVATION: (FORMULA_DERIVATION_NO_LATEX_TEMPLATE, "FormulaDerivation"),
}

# ---------------------------------------------------------------------------
# 默认参数
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    "bg_color": "#1a1a2e",
    "text_color": "#e0e0e0",
    "accent_color": "#4fc3f7",
    "axis_color": "#888888",
    "grid_color": "#444444",
    "font_size": 48,
    "run_time": 1.5,
    "wait_time": 0.5,
    "x_range": "[-5, 5, 1]",
    "y_range": "[-3, 3, 1]",
    "z_range": "[-2, 2, 1]",
    "x_length": 10,
    "y_length": 6,
    "x_label": "x",
    "y_label": "y",
    "u_range": "[-3, 3]",
    "v_range": "[-3, 3]",
    "plot_commands": "pass",
    "draw_commands": "pass",
    "geometry_commands": "pass",
    "vector_func": "np.array([pos[1], -pos[0], 0])",
    "surface_func": "np.sin(u) * np.cos(v)",
    "custom_code": "class CustomScene(Scene):\n    def construct(self):\n        self.wait(1)",
}


def get_template(
    anim_type: ManimAnimationType,
    *,
    latex_available: bool = True,
) -> tuple[Template, str]:
    """返回 ``(template, scene_class_name)``。

    当 ``latex_available=False`` 时，公式类动画自动使用降级模板（Text 替代 MathTex）。
    """
    if not latex_available:
        fallback = NO_LATEX_FALLBACK.get(anim_type)
        if fallback is not None:
            return fallback

    entry = TEMPLATE_REGISTRY.get(anim_type)
    if entry is None:
        raise ValueError(f"未注册的动画类型: {anim_type}")
    return entry


def _indent_code_block(code: str, indent: int = 8) -> str:
    """确保多行代码块的每一行都有一致的缩进。

    用户提供的代码中不应包含前导缩进（由模板位置决定），
    但如果包含了，会被统一规范化。
    """
    lines = code.strip().splitlines()
    if not lines:
        return "pass"

    min_indent = float("inf")
    for line in lines:
        stripped = line.lstrip()
        if stripped:
            min_indent = min(min_indent, len(line) - len(stripped))
    if min_indent == float("inf"):
        min_indent = 0

    prefix = " " * indent
    result = []
    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            result.append("")
        else:
            original_extra = len(line) - len(stripped) - min_indent
            extra = " " * max(0, original_extra)
            result.append(f"{prefix}{extra}{stripped}")
    return "\n".join(result)


_CODE_BLOCK_KEYS = {"plot_commands", "draw_commands", "geometry_commands", "custom_code"}


def build_template_params(
    anim_type: ManimAnimationType,
    *,
    formulas: list[str] | None = None,
    config: dict[str, Any] | None = None,
    resolution: tuple[int, int] = (1920, 1080),
    duration_hint_sec: float = 3.0,
) -> dict[str, Any]:
    """合并默认参数、config 覆盖和公式列表，返回模板所需的完整参数字典。"""
    params = dict(_DEFAULTS)

    animation_time = min(duration_hint_sec * 0.6, 15.0)
    remaining_wait = max(duration_hint_sec - animation_time, 0.5)
    params["wait_time"] = round(remaining_wait, 1)
    params["run_time"] = round(min(animation_time * 0.3, 2.5), 1)

    if config:
        params.update(config)

    for key in _CODE_BLOCK_KEYS:
        if key in params and isinstance(params[key], str) and params[key] != "pass":
            params[key] = _indent_code_block(params[key])

    if formulas:
        if anim_type in (
            ManimAnimationType.FORMULA_WRITE,
            ManimAnimationType.FORMULA_HIGHLIGHT,
        ):
            params["formula"] = formulas[0]
        else:
            params["formulas"] = repr(formulas)

    params.setdefault("title_text", "")
    params.setdefault("highlights", "[]")

    aspect = resolution[0] / resolution[1]
    if aspect < 1.0:
        params.setdefault("x_length", 6)
        params.setdefault("y_length", 10)

    return params
