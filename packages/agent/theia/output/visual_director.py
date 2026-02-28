"""视觉导演 (Visual Director): 基于规则引擎的动画编排。

Agent 3: 根据场景类型、word_timings 和注意力标注，
为每个场景生成精确的动画阶段（AnimationPhase）。

初始版本使用规则引擎（无需 LLM），后续可升级为 LLM 驱动。
"""

from __future__ import annotations

import logging

from ..schemas import (
    AnimationPhase,
    ManimAnimationSpec,
    ManimAnimationType,
    SceneNarration,
    StoryBlueprint,
    VisualChoreography,
    WordTiming,
)

logger = logging.getLogger(__name__)

SCENE_TEMPLATES: dict[str, list[dict]] = {
    "title": [
        {"pct_start": 0.0, "pct_end": 1.0, "mode": "voice_primary", "elements": ["title", "authors", "year"], "transition": "fade_in"},
    ],
    "overview": [
        {"pct_start": 0.0, "pct_end": 0.3, "mode": "voice_primary", "elements": ["problem"], "transition": "fade_in"},
        {"pct_start": 0.3, "pct_end": 1.0, "mode": "synced", "elements": ["problem", "contributions"], "transition": "slide_in"},
    ],
    "method": [
        {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["summary"], "transition": "fade_in"},
    ],
    "formula": [
        {"pct_start": 0.0, "pct_end": 0.12, "mode": "voice_primary", "elements": ["title"], "transition": "fade_in"},
        {"pct_start": 0.12, "pct_end": 0.35, "mode": "visual_primary", "elements": ["title", "formula"], "transition": "scale_in"},
        {"pct_start": 0.35, "pct_end": 1.0, "mode": "synced", "elements": ["title", "formula", "explanation"], "transition": "fade_in"},
    ],
    "figure": [
        {"pct_start": 0.0, "pct_end": 0.2, "mode": "visual_primary", "elements": ["image"], "transition": "scale_in"},
        {"pct_start": 0.2, "pct_end": 0.35, "mode": "visual_primary", "elements": ["image"], "transition": "none"},
        {"pct_start": 0.35, "pct_end": 1.0, "mode": "synced", "elements": ["image", "caption", "description"], "transition": "fade_in"},
    ],
    "result": [
        {"pct_start": 0.0, "pct_end": 0.15, "mode": "voice_primary", "elements": ["datasets"], "transition": "fade_in"},
        {"pct_start": 0.15, "pct_end": 1.0, "mode": "synced", "elements": ["datasets", "metrics", "findings"], "transition": "slide_in"},
    ],
    "conclusion": [
        {"pct_start": 0.0, "pct_end": 0.3, "mode": "voice_primary", "elements": ["conclusion"], "transition": "fade_in"},
        {"pct_start": 0.3, "pct_end": 1.0, "mode": "synced", "elements": ["conclusion", "contributions"], "transition": "fade_in"},
    ],
}


def choreograph_scenes(
    blueprint: StoryBlueprint,
    narrations: list[SceneNarration],
    scene_word_timings: list[list[WordTiming]],
    scene_durations_ms: list[int],
) -> list[VisualChoreography]:
    """为所有场景生成视觉编排。

    参数:
        blueprint: 故事蓝图。
        narrations: 各场景旁白及标注。
        scene_word_timings: 各场景的 word_timings（来自 TTS）。
        scene_durations_ms: 各场景实际时长（毫秒）。

    返回:
        每个场景的视觉编排列表。
    """
    choreographies: list[VisualChoreography] = []

    for i, scene_plan in enumerate(blueprint.scenes):
        duration_ms = scene_durations_ms[i] if i < len(scene_durations_ms) else 10000
        word_timings = scene_word_timings[i] if i < len(scene_word_timings) else []
        narration = narrations[i] if i < len(narrations) else None

        scene_type = scene_plan.type

        if scene_type == "method":
            phases = _choreograph_method(narration, word_timings, duration_ms)
        else:
            phases = _choreograph_from_template(scene_type, duration_ms, narration)

        choreographies.append(VisualChoreography(scene_index=i, phases=phases))

    logger.info(
        "视觉编排完成: %d 个场景, 共 %d 个动画阶段",
        len(choreographies),
        sum(len(c.phases) for c in choreographies),
    )
    return choreographies


# ---------------------------------------------------------------------------
# Manim 动画分配
# ---------------------------------------------------------------------------


def assign_manim_animations(
    blueprint: StoryBlueprint,
    narrations: list[SceneNarration],
    scene_durations_ms: list[int] | None = None,
) -> list[list[ManimAnimationSpec]]:
    """为每个场景判断是否需要 Manim 预渲染动画。

    返回与 blueprint.scenes 等长的列表，每个元素是该场景的动画规格。
    """
    result: list[list[ManimAnimationSpec]] = []

    for i, scene_plan in enumerate(blueprint.scenes):
        narration = narrations[i] if i < len(narrations) else None
        data = narration.data if narration else {}
        scene_dur_ms = scene_durations_ms[i] if scene_durations_ms and i < len(scene_durations_ms) else None
        specs = _assign_manim_for_scene(scene_plan.type, data, scene_duration_ms=scene_dur_ms)
        result.append(specs)

    total = sum(len(s) for s in result)
    if total:
        logger.info("Manim 动画分配: %d 个场景共 %d 个动画", sum(1 for s in result if s), total)
    return result


def _assign_manim_for_scene(
    scene_type: str,
    scene_data: dict,
    *,
    scene_duration_ms: int | None = None,
) -> list[ManimAnimationSpec]:
    """根据场景类型和数据决定需要哪些 Manim 动画。

    双层渲染策略:
    - Manim 负责语义可视化（矩阵流动、函数图像、几何构造）
    - Remotion KaTeX 负责精确公式展示（通过 FormulaOverlay 浮层）
    - 两层同时呈现，互补而非替代
    """
    specs: list[ManimAnimationSpec] = []
    scene_sec = (scene_duration_ms / 1000) if scene_duration_ms else 10.0

    if scene_type == "method":
        pass

    elif scene_type == "concept":
        formulas = scene_data.get("formulas", [])
        if formulas:
            specs.append(
                ManimAnimationSpec(
                    type=ManimAnimationType.FORMULA_WRITE,
                    formulas=[formulas[0]],
                    duration_hint_sec=min(scene_sec * 0.7, 10.0),
                    position="right",
                )
            )

    elif scene_type == "result":
        metrics = scene_data.get("metrics", [])
        if len(metrics) >= 2:
            viz_code = _generate_metrics_chart_viz(metrics)
            if viz_code:
                specs.append(
                    ManimAnimationSpec(
                        type=ManimAnimationType.GEOMETRY,
                        config={"geometry_commands": viz_code},
                        duration_hint_sec=min(scene_sec * 0.7, 15.0),
                        position="right",
                    )
                )

    return specs


def _detect_formula_highlights(formula: str) -> list[tuple[int, int, str]]:
    """检测公式中值得高亮的语义部分，返回 [(start, end, color), ...]。

    注意：MathTex 的索引基于渲染后的 submobjects，这里给出近似范围。
    实际 Manim 中 MathTex[0] 是整体，子索引对应渲染后的字符。
    """
    fl = formula.lower()
    highlights: list[tuple[int, int, str]] = []

    keyword_colors = [
        (["attention", "attn"], "#ff6b6b"),
        (["softmax"], "#ffd93d"),
        (["query", "key", "value"], "#4fc3f7"),
        (["\\frac", "\\sqrt"], "#a0e7a0"),
        (["\\sigma", "\\mu", "\\alpha"], "#ff9ff3"),
    ]

    for keywords, color in keyword_colors:
        for kw in keywords:
            idx = fl.find(kw)
            if idx >= 0:
                highlights.append((idx, idx + len(kw), color))

    return highlights[:5]


def _generate_formula_semantic_viz(formula: str, scene_data: dict) -> str | None:
    """为公式生成语义可视化的 Manim 代码。

    通过关键词检测公式类型，生成对应的直观动画，
    而精确公式由 Remotion KaTeX 浮层展示。
    """
    fl = formula.lower()
    title = scene_data.get("title", "").lower()
    combined = fl + " " + title

    if any(kw in combined for kw in ["softmax", "attention", "qk^t", "multi-head", "multihead"]):
        return _viz_attention_mechanism()
    if any(kw in combined for kw in ["layernorm", "layer_norm", "batchnorm", "batch_norm"]):
        return _viz_normalization()
    if "norm" in combined and any(kw in combined for kw in ["mu", "sigma", "mean", "var"]):
        return _viz_normalization()
    if any(kw in combined for kw in ["feed.?forward", "ffn", "w_1", "w_2"]):
        return _viz_feed_forward()
    if any(kw in combined for kw in ["residual", "skip.?connect", "x\\+", "add.*norm"]):
        return _viz_residual_connection()
    if any(kw in combined for kw in ["\\nabla", "gradient", "\\partial", "backprop"]):
        return _viz_gradient_flow()
    if any(kw in combined for kw in ["loss", "cross.?entropy", "mse", "criterion"]):
        return _viz_loss_landscape()
    if any(kw in combined for kw in ["\\sum", "\\prod", "sigma"]):
        return _viz_summation()
    if any(kw in combined for kw in ["\\int", "integral"]):
        return _viz_integral()
    if any(kw in combined for kw in ["matrix", "\\begin{bmatrix}", "\\mathbf", "\\mathbb"]):
        return _viz_matrix_operation()
    if any(kw in combined for kw in ["relu", "sigmoid", "tanh", "activation", "gelu"]):
        return _viz_activation_function()
    if any(kw in combined for kw in ["embed", "positional", "encoding"]):
        return _viz_embedding()

    return None


def _viz_attention_mechanism() -> str:
    return """
import numpy as np
title = Text("Attention Mechanism", font_size=30, color=WHITE).to_edge(UP, buff=0.4)
self.play(Write(title), run_time=0.6)

q = Rectangle(width=1.2, height=2, color=BLUE, fill_opacity=0.4)
Text("Q", font_size=24, color=BLUE_B).move_to(q)
q_g = VGroup(q, Text("Q", font_size=24, color=BLUE_B).move_to(q)).shift(LEFT*4 + DOWN*0.5)

k = Rectangle(width=2, height=1.2, color=GREEN, fill_opacity=0.4)
k_g = VGroup(k, Text("Kᵀ", font_size=24, color=GREEN_B).move_to(k)).shift(LEFT*1.5 + DOWN*0.5)

v = Rectangle(width=2, height=1.2, color=RED, fill_opacity=0.4)
v_g = VGroup(v, Text("V", font_size=24, color=RED_B).move_to(v)).shift(RIGHT*3 + DOWN*0.5)

self.play(FadeIn(q_g, shift=UP*0.4), FadeIn(k_g, shift=UP*0.4), FadeIn(v_g, shift=UP*0.4), run_time=1.0)

mult = Text("×", font_size=32, color=WHITE).move_to((q_g.get_right() + k_g.get_left()) / 2)
self.play(Write(mult), run_time=0.3)

scores = Rectangle(width=2, height=2, color=PURPLE, fill_opacity=0.3)
scores_g = VGroup(scores, Text("Scores", font_size=20, color=PURPLE_B).move_to(scores)).move_to(LEFT*2.5 + DOWN*0.5)
self.play(FadeOut(mult), Transform(q_g, scores_g), FadeOut(k_g), run_time=0.8)

scale = Text("÷ √dₖ", font_size=24, color=ORANGE).next_to(scores_g, DOWN, buff=0.2)
self.play(Write(scale), run_time=0.4)
self.play(q_g.animate.set_color(ORANGE), FadeOut(scale), run_time=0.5)

sm = Text("softmax →", font_size=22, color=TEAL).next_to(q_g, RIGHT, buff=0.3)
self.play(Write(sm), run_time=0.4)

bars = VGroup(*[Rectangle(width=0.3, height=0.2+np.random.random()*0.6, color=TEAL, fill_opacity=0.7).shift(RIGHT*i*0.35) for i in range(5)])
bars.arrange(RIGHT, buff=0.05).move_to(RIGHT*0.5 + DOWN*0.5)
self.play(FadeOut(sm), FadeOut(q_g), FadeIn(bars), run_time=0.6)

dot = Text("·", font_size=40, color=WHITE).move_to((bars.get_right() + v_g.get_left()) / 2)
self.play(Write(dot), run_time=0.2)

out = Rectangle(width=2, height=2, color=GOLD, fill_opacity=0.4)
out_g = VGroup(out, Text("Output", font_size=22, color=GOLD).move_to(out)).move_to(RIGHT*1 + DOWN*0.5)
self.play(FadeOut(dot), FadeOut(v_g), FadeOut(bars), FadeIn(out_g, scale=0.5), run_time=0.8)

box = SurroundingRectangle(out_g, color=GOLD, buff=0.15)
self.play(Create(box), run_time=0.4)
"""


def _viz_normalization() -> str:
    return """
import numpy as np
title = Text("Layer Normalization", font_size=30, color=WHITE).to_edge(UP, buff=0.4)
self.play(Write(title), run_time=0.6)

np.random.seed(42)
raw_values = np.random.randn(8) * 2 + 3
norm_values = (raw_values - raw_values.mean()) / (raw_values.std() + 1e-5)

axes = Axes(x_range=[0, 9, 1], y_range=[-3, 6, 1], x_length=10, y_length=5, axis_config={"color": GREY_B})
axes.shift(DOWN * 0.3)
self.play(Create(axes), run_time=0.8)

raw_bars = VGroup()
for i, v in enumerate(raw_values):
    bar = Rectangle(width=0.6, height=abs(v)*0.5, color=RED if v > 3.5 else BLUE, fill_opacity=0.5)
    bar.next_to(axes.c2p(i+0.5, 0), UP if v >= 0 else DOWN, buff=0)
    raw_bars.add(bar)
label1 = Text("Before Norm", font_size=20, color=RED_B).next_to(raw_bars, UP, buff=0.2)
self.play(FadeIn(raw_bars), Write(label1), run_time=1.0)
self.wait(0.5)

arrow = Arrow(LEFT*0.5, RIGHT*0.5, color=YELLOW).next_to(raw_bars, RIGHT, buff=0.3)
arrow_label = Text("LayerNorm", font_size=18, color=YELLOW).next_to(arrow, UP, buff=0.1)
self.play(Create(arrow), Write(arrow_label), run_time=0.4)

norm_bars = VGroup()
for i, v in enumerate(norm_values):
    bar = Rectangle(width=0.6, height=abs(v)*0.8, color=GREEN, fill_opacity=0.5)
    bar.next_to(axes.c2p(i+0.5, 0), UP if v >= 0 else DOWN, buff=0)
    norm_bars.add(bar)

label2 = Text("After Norm (μ=0, σ=1)", font_size=20, color=GREEN_B).next_to(norm_bars, UP, buff=0.2)
self.play(
    Transform(raw_bars, norm_bars),
    Transform(label1, label2),
    FadeOut(arrow), FadeOut(arrow_label),
    run_time=1.5,
)

mean_line = DashedLine(axes.c2p(0, 0), axes.c2p(9, 0), color=YELLOW, dash_length=0.1)
mean_label = Text("μ = 0", font_size=18, color=YELLOW).next_to(mean_line, RIGHT, buff=0.2)
self.play(Create(mean_line), Write(mean_label), run_time=0.5)
"""


def _viz_loss_landscape() -> str:
    return """
import numpy as np
title = Text("Loss Landscape", font_size=30, color=WHITE).to_edge(UP, buff=0.4)
self.play(Write(title), run_time=0.6)

axes = Axes(x_range=[-3, 3, 1], y_range=[-1, 5, 1], x_length=9, y_length=5, axis_config={"color": GREY_B})
self.play(Create(axes), run_time=0.8)

loss_curve = axes.plot(lambda x: 0.5*x**2 + 0.3*np.sin(3*x) + 1, color=RED, x_range=[-2.8, 2.8])
loss_label = Text("Loss", font_size=22, color=RED).next_to(loss_curve, UP, buff=0.1).shift(LEFT*2)
self.play(Create(loss_curve), Write(loss_label), run_time=1.2)

dot = Dot(axes.c2p(2.5, 0.5*2.5**2 + 0.3*np.sin(7.5) + 1), color=YELLOW, radius=0.12)
self.play(FadeIn(dot, scale=0.5), run_time=0.4)

path_points = [2.5, 1.8, 1.0, 0.3, -0.1, 0.05]
for x in path_points[1:]:
    y = 0.5*x**2 + 0.3*np.sin(3*x) + 1
    new_pos = axes.c2p(x, y)
    trail = Line(dot.get_center(), new_pos, color=YELLOW_A, stroke_width=2, stroke_opacity=0.5)
    self.play(Create(trail), dot.animate.move_to(new_pos), run_time=0.4)

star = Star(n=5, outer_radius=0.15, color=GREEN, fill_opacity=1).move_to(dot.get_center())
min_label = Text("minimum", font_size=18, color=GREEN).next_to(star, DOWN, buff=0.15)
self.play(Transform(dot, star), Write(min_label), run_time=0.4)
"""


def _viz_activation_function() -> str:
    return """
import numpy as np
title = Text("Activation Functions", font_size=30, color=WHITE).to_edge(UP, buff=0.4)
self.play(Write(title), run_time=0.6)

axes = Axes(x_range=[-4, 4, 1], y_range=[-1.5, 4, 1], x_length=10, y_length=5, axis_config={"color": GREY_B})
self.play(Create(axes), run_time=0.8)

relu = axes.plot(lambda x: max(0, x), color=BLUE, x_range=[-4, 4])
relu_label = Text("ReLU", font_size=20, color=BLUE).move_to(axes.c2p(3, 3.5))
self.play(Create(relu), Write(relu_label), run_time=1.0)

sigmoid = axes.plot(lambda x: 1/(1+np.exp(-x)), color=GREEN, x_range=[-4, 4])
sig_label = Text("Sigmoid", font_size=20, color=GREEN).move_to(axes.c2p(-2.5, 1.2))
self.play(Create(sigmoid), Write(sig_label), run_time=1.0)

gelu = axes.plot(lambda x: 0.5*x*(1+np.tanh(np.sqrt(2/np.pi)*(x+0.044715*x**3))), color=YELLOW, x_range=[-4, 4])
gelu_label = Text("GELU", font_size=20, color=YELLOW).move_to(axes.c2p(2, 1.5))
self.play(Create(gelu), Write(gelu_label), run_time=1.0)
"""


def _viz_embedding() -> str:
    return """
import numpy as np
title = Text("Positional Encoding", font_size=30, color=WHITE).to_edge(UP, buff=0.4)
self.play(Write(title), run_time=0.6)

tokens = ["The", "cat", "sat", "on", "mat"]
token_boxes = VGroup()
for i, tok in enumerate(tokens):
    box = RoundedRectangle(width=1.2, height=0.7, corner_radius=0.1, color=BLUE, fill_opacity=0.3)
    text = Text(tok, font_size=18, color=WHITE).move_to(box)
    token_boxes.add(VGroup(box, text))
token_boxes.arrange(RIGHT, buff=0.3).shift(UP*1.5)
self.play(FadeIn(token_boxes, shift=DOWN*0.3), run_time=0.8)

pos_boxes = VGroup()
for i in range(len(tokens)):
    box = RoundedRectangle(width=1.2, height=0.7, corner_radius=0.1, color=GREEN, fill_opacity=0.3)
    text = Text(f"pos={i}", font_size=14, color=GREEN).move_to(box)
    pos_boxes.add(VGroup(box, text))
pos_boxes.arrange(RIGHT, buff=0.3).next_to(token_boxes, DOWN, buff=0.4)

plus_signs = VGroup()
for i in range(len(tokens)):
    plus = Text("+", font_size=20, color=YELLOW)
    plus.move_to((token_boxes[i].get_bottom() + pos_boxes[i].get_top()) / 2)
    plus_signs.add(plus)

self.play(FadeIn(pos_boxes, shift=UP*0.3), Write(plus_signs), run_time=0.8)

result_boxes = VGroup()
for i in range(len(tokens)):
    box = RoundedRectangle(width=1.2, height=0.7, corner_radius=0.1, color=GOLD, fill_opacity=0.3)
    text = Text(f"e{i}", font_size=18, color=GOLD).move_to(box)
    result_boxes.add(VGroup(box, text))
result_boxes.arrange(RIGHT, buff=0.3).next_to(pos_boxes, DOWN, buff=0.6)

eq_sign = Text("=", font_size=24, color=WHITE).move_to((pos_boxes.get_bottom() + result_boxes.get_top()) / 2)
self.play(Write(eq_sign), FadeIn(result_boxes, scale=0.5), run_time=0.8)

label = Text("Token + Position = Input Embedding", font_size=22, color=GOLD).next_to(result_boxes, DOWN, buff=0.4)
self.play(Write(label), run_time=0.6)
"""


def _viz_feed_forward() -> str:
    return """
import numpy as np
title = Text("Feed-Forward Network", font_size=30, color=WHITE).to_edge(UP, buff=0.4)
self.play(Write(title), run_time=0.6)

input_layer = VGroup()
for i in range(4):
    dot = Circle(radius=0.2, color=BLUE, fill_opacity=0.5).shift(UP*(1.5-i) + LEFT*4)
    input_layer.add(dot)
input_label = Text("Input\\n(d_model)", font_size=16, color=BLUE_B).next_to(input_layer, DOWN, buff=0.2)

hidden_layer = VGroup()
for i in range(6):
    dot = Circle(radius=0.2, color=YELLOW, fill_opacity=0.5).shift(UP*(2.25 - i*0.9))
    hidden_layer.add(dot)
hidden_label = Text("Hidden\\n(d_ff)", font_size=16, color=YELLOW).next_to(hidden_layer, DOWN, buff=0.2)

output_layer = VGroup()
for i in range(4):
    dot = Circle(radius=0.2, color=GREEN, fill_opacity=0.5).shift(UP*(1.5-i) + RIGHT*4)
    output_layer.add(dot)
output_label = Text("Output\\n(d_model)", font_size=16, color=GREEN).next_to(output_layer, DOWN, buff=0.2)

self.play(FadeIn(input_layer), Write(input_label), run_time=0.6)

lines1 = VGroup()
for inp in input_layer:
    for hid in hidden_layer:
        line = Line(inp.get_right(), hid.get_left(), color=BLUE_A, stroke_width=1, stroke_opacity=0.3)
        lines1.add(line)

self.play(Create(lines1), FadeIn(hidden_layer), Write(hidden_label), run_time=0.8)

relu_label = Text("ReLU", font_size=22, color=RED).next_to(hidden_layer, UP, buff=0.2)
self.play(Write(relu_label), run_time=0.3)
self.play(hidden_layer.animate.set_color(RED), run_time=0.4)
self.play(hidden_layer.animate.set_color(YELLOW), FadeOut(relu_label), run_time=0.3)

lines2 = VGroup()
for hid in hidden_layer:
    for out in output_layer:
        line = Line(hid.get_right(), out.get_left(), color=GREEN_A, stroke_width=1, stroke_opacity=0.3)
        lines2.add(line)

self.play(Create(lines2), FadeIn(output_layer), Write(output_label), run_time=0.8)
"""


def _viz_residual_connection() -> str:
    return """
import numpy as np
title = Text("Residual Connection + LayerNorm", font_size=28, color=WHITE).to_edge(UP, buff=0.4)
self.play(Write(title), run_time=0.6)

x_box = RoundedRectangle(width=2, height=0.8, corner_radius=0.1, color=BLUE, fill_opacity=0.3)
x_text = Text("x", font_size=26, color=BLUE).move_to(x_box)
x_group = VGroup(x_box, x_text).shift(LEFT*3 + UP*1)
self.play(FadeIn(x_group), run_time=0.5)

sublayer_box = RoundedRectangle(width=3, height=0.8, corner_radius=0.1, color=YELLOW, fill_opacity=0.3)
sublayer_text = Text("Sublayer(x)", font_size=22, color=YELLOW).move_to(sublayer_box)
sublayer_group = VGroup(sublayer_box, sublayer_text).next_to(x_group, RIGHT, buff=1.5)

arrow1 = Arrow(x_group.get_right(), sublayer_group.get_left(), color=GREY_B, buff=0.1)
self.play(Create(arrow1), FadeIn(sublayer_group), run_time=0.6)

skip_arc = ArcBetweenPoints(x_group.get_bottom() + DOWN*0.1, sublayer_group.get_bottom() + DOWN*0.1 + RIGHT*1.5, angle=-PI/4, color=RED)
skip_label = Text("skip", font_size=18, color=RED).next_to(skip_arc, DOWN, buff=0.1)
self.play(Create(skip_arc), Write(skip_label), run_time=0.6)

add_circle = Circle(radius=0.3, color=GREEN, fill_opacity=0.3).next_to(sublayer_group, RIGHT, buff=1)
add_text = Text("+", font_size=28, color=GREEN).move_to(add_circle)
add_group = VGroup(add_circle, add_text)
arrow2 = Arrow(sublayer_group.get_right(), add_group.get_left(), color=GREY_B, buff=0.1)
self.play(Create(arrow2), FadeIn(add_group), run_time=0.5)

norm_box = RoundedRectangle(width=2.5, height=0.8, corner_radius=0.1, color=PURPLE, fill_opacity=0.3)
norm_text = Text("LayerNorm", font_size=22, color=PURPLE).move_to(norm_box)
norm_group = VGroup(norm_box, norm_text).next_to(add_group, DOWN, buff=0.8)
arrow3 = Arrow(add_group.get_bottom(), norm_group.get_top(), color=GREY_B, buff=0.1)
self.play(Create(arrow3), FadeIn(norm_group), run_time=0.5)

eq = Text("y = LayerNorm(x + Sublayer(x))", font_size=22, color=GOLD).to_edge(DOWN, buff=0.5)
self.play(Write(eq), run_time=0.8)
"""


def _viz_gradient_flow() -> str:
    return """
import numpy as np
title = Text("Gradient Flow", font_size=30, color=WHITE).to_edge(UP, buff=0.4)
self.play(Write(title), run_time=0.6)

axes = Axes(x_range=[-3, 3, 1], y_range=[-1, 4, 1], x_length=8, y_length=5, axis_config={"color": GREY_B})
self.play(Create(axes), run_time=1.0)

curve = axes.plot(lambda x: x**2, color=BLUE, x_range=[-2.5, 2.5])
self.play(Create(curve), run_time=1.0)

dot = Dot(axes.c2p(2, 4), color=YELLOW, radius=0.12)
self.play(FadeIn(dot), run_time=0.3)

positions = [2, 1.5, 1.0, 0.5, 0.1]
for x in positions[1:]:
    new_pos = axes.c2p(x, x**2)
    arrow = Arrow(dot.get_center(), new_pos, color=RED, buff=0.1, stroke_width=3)
    self.play(Create(arrow), run_time=0.3)
    self.play(dot.animate.move_to(new_pos), FadeOut(arrow), run_time=0.4)

star = Star(n=5, outer_radius=0.2, color=GOLD, fill_opacity=1).move_to(dot.get_center())
self.play(Transform(dot, star), run_time=0.4)
"""


def _viz_summation() -> str:
    return """
import numpy as np
title = Text("Summation", font_size=30, color=WHITE).to_edge(UP, buff=0.4)
self.play(Write(title), run_time=0.6)

bars = VGroup()
values = [0.3, 0.7, 1.2, 0.9, 1.5, 0.4, 0.8]
colors = [BLUE, GREEN, YELLOW, RED, PURPLE, TEAL, ORANGE]
for i, (v, c) in enumerate(zip(values, colors)):
    bar = Rectangle(width=0.6, height=v * 2, color=c, fill_opacity=0.6)
    label = Text(f"{v}", font_size=18, color=WHITE).next_to(bar, UP, buff=0.1)
    bars.add(VGroup(bar, label))
bars.arrange(RIGHT, buff=0.3, aligned_edge=DOWN).move_to(DOWN*0.5)

for bar in bars:
    self.play(GrowFromEdge(bar[0], DOWN), Write(bar[1]), run_time=0.3)

brace = Brace(bars, DOWN, color=WHITE)
total = Text(f"Σ = {sum(values):.1f}", font_size=28, color=GOLD).next_to(brace, DOWN)
self.play(Create(brace), Write(total), run_time=0.8)
"""


def _viz_integral() -> str:
    return """
import numpy as np
title = Text("Integration", font_size=30, color=WHITE).to_edge(UP, buff=0.4)
self.play(Write(title), run_time=0.6)

axes = Axes(x_range=[-1, 5, 1], y_range=[-0.5, 2, 0.5], x_length=9, y_length=4, axis_config={"color": GREY_B})
self.play(Create(axes), run_time=0.8)

curve = axes.plot(lambda x: np.sin(x) + 1, color=BLUE, x_range=[0, 4])
self.play(Create(curve), run_time=0.8)

area = axes.get_area(curve, x_range=[0.5, 3.5], color=[BLUE, GREEN], opacity=0.5)
self.play(FadeIn(area), run_time=1.0)

label = Text("Area under curve", font_size=24, color=GREEN).next_to(area, UP, buff=0.3)
self.play(Write(label), run_time=0.6)
"""


def _viz_matrix_operation() -> str:
    return """
import numpy as np
title = Text("Matrix Operation", font_size=30, color=WHITE).to_edge(UP, buff=0.4)
self.play(Write(title), run_time=0.6)

def make_matrix(rows, cols, color, label_text):
    rects = VGroup()
    for r in range(rows):
        for c in range(cols):
            rect = Square(side_length=0.5, color=color, fill_opacity=0.3 + np.random.random()*0.3)
            rect.move_to([c*0.55, -r*0.55, 0])
            rects.add(rect)
    rects.move_to(ORIGIN)
    label = Text(label_text, font_size=22, color=color).next_to(rects, UP, buff=0.2)
    return VGroup(rects, label)

m_a = make_matrix(3, 2, BLUE, "A (3×2)").shift(LEFT*3.5 + DOWN*0.3)
m_b = make_matrix(2, 4, GREEN, "B (2×4)").shift(DOWN*0.3)
m_c = make_matrix(3, 4, GOLD, "C (3×4)").shift(RIGHT*3.5 + DOWN*0.3)

self.play(FadeIn(m_a, shift=RIGHT*0.3), run_time=0.6)
self.play(FadeIn(m_b, shift=RIGHT*0.3), run_time=0.6)

mult = Text("×", font_size=36, color=WHITE).move_to((m_a.get_right() + m_b.get_left()) / 2)
eq = Text("=", font_size=36, color=WHITE).move_to((m_b.get_right() + m_c.get_left()) / 2)
self.play(Write(mult), Write(eq), run_time=0.4)

self.play(FadeIn(m_c, scale=0.5), run_time=0.8)
box = SurroundingRectangle(m_c, color=GOLD, buff=0.15)
self.play(Create(box), run_time=0.4)
"""


def _generate_steps_flow_viz(steps: list, scene_data: dict) -> str | None:
    """为方法论步骤生成流程图可视化。"""
    if not steps or len(steps) < 2:
        return None

    step_labels = []
    for i, step in enumerate(steps[:5]):
        text = str(step)[:50]
        text = text.replace('"', '\\"').replace("\\", "\\\\")
        step_labels.append(f'"{i + 1}. {text}"')

    labels_str = ", ".join(step_labels)
    n_steps = len(step_labels)
    box_height = 1.0 if n_steps <= 3 else 0.8
    font_size = 16 if n_steps > 3 else 18
    box_width = 8

    return f"""
labels = [{labels_str}]
boxes = VGroup()
arrows = VGroup()

colors = [BLUE, GREEN, YELLOW, RED, PURPLE, TEAL]
for i, label in enumerate(labels):
    color = colors[i % len(colors)]
    box = RoundedRectangle(width={box_width}, height={box_height}, corner_radius=0.15, color=color, fill_opacity=0.25)
    text = Text(label, font_size={font_size}, color=WHITE)
    if text.width > {box_width - 0.6}:
        text.scale_to_fit_width({box_width - 0.6})
    text.move_to(box)
    group = VGroup(box, text)
    boxes.add(group)

boxes.arrange(DOWN, buff=0.35).move_to(ORIGIN)

for i, box in enumerate(boxes):
    self.play(FadeIn(box, shift=RIGHT * 0.3), run_time=0.4)
    if i < len(boxes) - 1:
        arrow = Arrow(box.get_bottom(), boxes[i+1].get_top(), color=GREY_B, buff=0.08, stroke_width=2)
        arrows.add(arrow)
        self.play(Create(arrow), run_time=0.2)
"""


def _generate_metrics_chart_viz(metrics: list) -> str | None:
    """为结果指标生成柱状图可视化。"""
    if not metrics:
        return None

    bar_entries = []
    for m in metrics[:6]:
        if isinstance(m, dict):
            name = str(m.get("name", m.get("metric", "")))[:15].replace('"', '\\"')
            value = m.get("value", 0)
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue
            bar_entries.append((name, value))
        elif isinstance(m, str):
            bar_entries.append((m[:15].replace('"', '\\"'), 1.0))

    if not bar_entries:
        return None

    max_val = max(v for _, v in bar_entries) or 1.0
    colors = ["BLUE", "GREEN", "YELLOW", "RED", "PURPLE", "TEAL"]
    lines = [
        'title = Text("Results", font_size=28, color=WHITE).to_edge(UP, buff=0.4)',
        'self.play(Write(title), run_time=0.5)',
        'bars = VGroup()',
    ]

    for i, (name, val) in enumerate(bar_entries):
        h = max(0.3, (val / max_val) * 3.0)
        color = colors[i % len(colors)]
        lines.append(f'b{i} = Rectangle(width=0.8, height={h:.2f}, color={color}, fill_opacity=0.6)')
        lines.append(f'l{i} = Text("{name}", font_size=14, color=WHITE)')
        lines.append(f'v{i} = Text("{val}", font_size=16, color={color})')
        lines.append(f'l{i}.next_to(b{i}, DOWN, buff=0.1)')
        lines.append(f'v{i}.next_to(b{i}, UP, buff=0.1)')
        lines.append(f'bars.add(VGroup(b{i}, l{i}, v{i}))')

    lines.append('bars.arrange(RIGHT, buff=0.5, aligned_edge=DOWN).move_to(DOWN*0.3)')
    lines.append('for bar in bars:')
    lines.append('    self.play(GrowFromEdge(bar[0], DOWN), Write(bar[1]), Write(bar[2]), run_time=0.4)')

    return "\n".join(lines)


def _choreograph_from_template(
    scene_type: str,
    duration_ms: int,
    narration: SceneNarration | None,
) -> list[AnimationPhase]:
    """基于场景类型模板生成动画阶段。"""
    template = SCENE_TEMPLATES.get(scene_type, SCENE_TEMPLATES["overview"])
    phases: list[AnimationPhase] = []

    for tmpl in template:
        start_ms = int(tmpl["pct_start"] * duration_ms)
        end_ms = int(tmpl["pct_end"] * duration_ms)
        phases.append(
            AnimationPhase(
                start_ms=start_ms,
                end_ms=end_ms,
                attention_mode=tmpl["mode"],
                elements_to_show=list(tmpl["elements"]),
                transition_type=tmpl["transition"],
            )
        )

    if narration and narration.attention_markers:
        phases = _refine_with_markers(phases, narration, duration_ms)

    return phases


def _choreograph_method(
    narration: SceneNarration | None,
    word_timings: list[WordTiming],
    duration_ms: int,
) -> list[AnimationPhase]:
    """为 method 场景生成逐步揭示的动画阶段。"""
    step_count = 0
    if narration and narration.data:
        steps = narration.data.get("steps", [])
        step_count = len(steps)

    if step_count == 0:
        return _choreograph_from_template("method", duration_ms, narration)

    phases: list[AnimationPhase] = []

    summary_end_ms = int(0.15 * duration_ms)
    phases.append(
        AnimationPhase(
            start_ms=0,
            end_ms=summary_end_ms,
            attention_mode="voice_primary",
            elements_to_show=["summary"],
            transition_type="fade_in",
        )
    )

    steps_duration_ms = duration_ms - summary_end_ms
    step_duration = steps_duration_ms // step_count

    if word_timings:
        step_boundaries = _find_step_boundaries(word_timings, step_count, summary_end_ms, duration_ms)
    else:
        step_boundaries = [
            (summary_end_ms + i * step_duration, summary_end_ms + (i + 1) * step_duration)
            for i in range(step_count)
        ]

    for i, (start, end) in enumerate(step_boundaries):
        visible = ["summary"] + [f"step_{j}" for j in range(i + 1)]
        phases.append(
            AnimationPhase(
                start_ms=start,
                end_ms=end,
                attention_mode="synced",
                elements_to_show=visible,
                highlight_element=f"step_{i}",
                transition_type="slide_in",
            )
        )

    return phases


def _find_step_boundaries(
    word_timings: list[WordTiming],
    step_count: int,
    summary_end_ms: int,
    duration_ms: int,
) -> list[tuple[int, int]]:
    """利用 word_timings 找到每个步骤的时间边界。

    查找包含"第X步"、"首先"、"然后"、"接着"、"最后"等标记词的位置。
    找不到时退化为均分。
    """
    trigger_patterns = ["第一", "第二", "第三", "第四", "第五", "第六", "首先", "然后", "接着", "其次", "最后"]
    found_offsets: list[int] = []

    accumulated_text = ""
    for wt in word_timings:
        prev_len = len(accumulated_text)
        accumulated_text += wt.text
        for pattern in trigger_patterns:
            if pattern in accumulated_text[prev_len:]:
                found_offsets.append(wt.offset_ms)
                break

    if len(found_offsets) < step_count:
        step_duration = (duration_ms - summary_end_ms) // step_count
        return [
            (summary_end_ms + i * step_duration, summary_end_ms + (i + 1) * step_duration)
            for i in range(step_count)
        ]

    found_offsets = sorted(set(found_offsets))[:step_count]

    boundaries: list[tuple[int, int]] = []
    for i, offset in enumerate(found_offsets):
        start = max(offset, summary_end_ms)
        end = found_offsets[i + 1] if i + 1 < len(found_offsets) else duration_ms
        boundaries.append((start, end))

    return boundaries


def _refine_with_markers(
    phases: list[AnimationPhase],
    narration: SceneNarration,
    duration_ms: int,
) -> list[AnimationPhase]:
    """根据旁白中的注意力标注微调动画阶段。

    将标注的模式切换点映射到时间线上，切分已有阶段。
    """
    if not narration.attention_markers or not narration.narration:
        return phases

    total_chars = len(narration.narration)
    if total_chars == 0:
        return phases

    refined: list[AnimationPhase] = []

    for phase in phases:
        markers_in_range = []
        for marker in narration.attention_markers:
            marker_ms = int((marker.char_offset / total_chars) * duration_ms)
            if phase.start_ms <= marker_ms < phase.end_ms:
                markers_in_range.append((marker_ms, marker))

        if not markers_in_range:
            refined.append(phase)
            continue

        current_start = phase.start_ms
        for marker_ms, marker in sorted(markers_in_range, key=lambda x: x[0]):
            if marker_ms > current_start:
                refined.append(
                    AnimationPhase(
                        start_ms=current_start,
                        end_ms=marker_ms,
                        attention_mode=phase.attention_mode,
                        elements_to_show=phase.elements_to_show,
                        highlight_element=phase.highlight_element,
                        transition_type=phase.transition_type,
                    )
                )
            current_start = marker_ms

        refined.append(
            AnimationPhase(
                start_ms=current_start,
                end_ms=phase.end_ms,
                attention_mode=markers_in_range[-1][1].mode_switch_to,
                elements_to_show=phase.elements_to_show,
                highlight_element=phase.highlight_element,
                transition_type="none",
            )
        )

    return refined
