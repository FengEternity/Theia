"""基于 LangGraph 的流水线编排。

使用 LangGraph 的 StateGraph 实现论文到视频的流水线。
v1: 线性流程（解析 → 提取 → 脚本 → TTS → 渲染）。
未来: 条件路由、质量检查、人机交互。
"""

from __future__ import annotations

import json
import logging
from collections import Counter
import re
import threading
from pathlib import Path
from typing import Any, Callable, Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from typing_extensions import TypedDict

from ._utils import extract_figures_from_markdown, pdf_stem
from .cache import cache_key_for_content, cache_key_for_pdf, get_cached, set_cached
from .scene_registry import get_skip_aux_figures_set
from .llm.config import LLMConfig, detect_language
from .schemas import VIDEO_PRESETS, PaperSummary, PipelineInput, ProgressCallback, StepInfo, VideoScript

logger = logging.getLogger(__name__)

_SKIP_AUX_FIGURES = get_skip_aux_figures_set()


# ---------------------------------------------------------------------------
# 图状态定义
# ---------------------------------------------------------------------------


class PipelineState(TypedDict, total=False):
    """LangGraph 完整状态。

    扁平结构以兼容 LangGraph 的浅合并语义。
    字段按逻辑分组，通过 PipelineInput 模型在入口处验证。
    """

    # ---- 输入参数（对应 PipelineInput，不可变） ----
    pdf_path: str
    workspace: str
    llm_model: str
    extract_model: str
    scan_model: str
    figure_model: str
    story_model: str
    scene_model: str
    gate_model: str
    judge_model: str
    script_model: str
    language: str
    tts_voice: str | None
    mineru_backend: str
    fps: int
    video_preset: str
    skip_tts: bool
    skip_render: bool
    use_cache: bool
    single_pass_extraction: bool
    output_path: str | None
    narration_style: str
    theme: str
    speech_rate: int
    interactive_mode: bool

    # ---- API 凭据（各步骤独立，由 LLMConfig 解析后注入） ----
    extract_api_key: str | None
    extract_api_base: str | None
    scan_api_key: str | None
    scan_api_base: str | None
    figure_api_key: str | None
    figure_api_base: str | None
    story_api_key: str | None
    story_api_base: str | None
    scene_api_key: str | None
    scene_api_base: str | None
    gate_api_key: str | None
    gate_api_base: str | None
    judge_api_key: str | None
    judge_api_base: str | None
    script_api_key: str | None
    script_api_base: str | None

    # ---- 中间产物（各节点自动填充，Phase 3 可人工编辑） ----
    detected_language: str
    markdown_content: str
    content_list_json: str | None
    parsed_dir: str
    paper_summary_json: str
    video_script_json: str
    figures_json: str

    # ---- 输出 ----
    output_video: str | None
    error: str | None

    # NOTE: _progress_callback 不再存入 state（不可序列化），
    # 改用模块级 _callback_registry 按 workspace 路径查找。


# ---------------------------------------------------------------------------
# 进度回调注册表（线程安全，不参与 LangGraph 序列化）
# ---------------------------------------------------------------------------

_callback_lock = threading.Lock()
_callback_registry: dict[str, ProgressCallback] = {}


def register_progress_callback(workspace: str, cb: ProgressCallback) -> None:
    with _callback_lock:
        _callback_registry[workspace] = cb


def unregister_progress_callback(workspace: str) -> None:
    with _callback_lock:
        _callback_registry.pop(workspace, None)


# ---------------------------------------------------------------------------
# 进度通知辅助
# ---------------------------------------------------------------------------


def _notify(
    state: PipelineState, step: int, name: str, status: str, message: str = "", progress_pct: int = 0, **detail: Any
) -> None:
    """安全地触发进度回调（若已注册）。"""
    ws = state.get("workspace", "")
    with _callback_lock:
        cb = _callback_registry.get(ws)
    if cb and isinstance(cb, ProgressCallback):
        try:
            cb.on_step(
                StepInfo(
                    step=step,
                    total_steps=5,
                    name=name,
                    status=status,
                    message=message,
                    progress_pct=progress_pct,
                    detail=detail,
                )
            )
        except Exception:
            raise


def _make_on_token(workspace: str, step_name: str) -> Callable[[str], None] | None:
    """为指定 workspace 和步骤生成 token 流式回调。

    如果没有注册回调或回调不支持 on_token，返回 None。
    """
    with _callback_lock:
        cb = _callback_registry.get(workspace)
    if cb and hasattr(cb, "on_token"):
        return lambda text: cb.on_token(step_name, text)
    return None


# ---------------------------------------------------------------------------
# 节点函数
# ---------------------------------------------------------------------------


def parse_node(state: PipelineState) -> dict:
    """节点 1: 解析输入内容（PDF 或网页文章）。"""
    from .parsing.pdf import ParseResult, parse_pdf
    from .parsing.web import is_article_url, parse_article

    pdf_input = state["pdf_path"]
    workspace = Path(state["workspace"])
    use_cache = state.get("use_cache", True)
    stem = pdf_stem(pdf_input)
    is_web_article = is_article_url(pdf_input)

    parse_label = "抓取网页文章" if is_web_article else "使用 MinerU 解析 PDF"
    _notify(state, 1, "parse", "started", parse_label)
    logger.info("=" * 60)
    logger.info("步骤 1/5: %s", parse_label)
    logger.info("=" * 60)

    md_out = workspace / "parsed" / f"{stem}.md"
    cached = False

    if use_cache and md_out.exists() and md_out.stat().st_size > 100:
        markdown = md_out.read_text(encoding="utf-8")
        parsed_base = workspace / "parsed"
        output_dir = parsed_base
        images_dir = None
        for sub in parsed_base.rglob("images"):
            if sub.is_dir():
                images_dir = sub
                output_dir = sub.parent
                break

        content_list_cached = None
        cl_candidates = list(parsed_base.rglob("*content_list.json"))
        if cl_candidates:
            try:
                content_list_cached = json.loads(cl_candidates[0].read_text(encoding="utf-8"))
                logger.info("从缓存加载 content_list: %s (%d 条)", cl_candidates[0], len(content_list_cached))
            except Exception as exc:
                logger.warning("加载缓存 content_list 失败: %s", exc)

        result = ParseResult(
            markdown=markdown,
            images_dir=images_dir,
            content_list=content_list_cached,
            output_dir=output_dir,
        )
        logger.info("使用已缓存的解析结果: %s (%d 字符)", md_out, len(markdown))
        cached = True

    if not cached:
        if is_web_article:
            result = parse_article(pdf_input, workspace / "parsed")
        else:
            lang_hint = state.get("language", "zh")
            mineru_lang = {"zh": "ch", "en": "en", "auto": "ch"}.get(lang_hint, lang_hint)

            result = parse_pdf(
                pdf_input,
                workspace / "parsed",
                lang=mineru_lang,
                backend=state.get("mineru_backend", "pipeline"),
            )

        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(result.markdown, encoding="utf-8")

    detected_lang = detect_language(result.markdown)
    logger.info(
        "Markdown: %d 字符, %d 张图片, 检测到语言: %s",
        len(result.markdown),
        len(result.image_paths),
        detected_lang,
    )

    figures = extract_figures_from_markdown(result.markdown)
    logger.info("提取到 %d 张图片引用", len(figures))
    _notify(
        state,
        1,
        "parse",
        "completed",
        f"解析完成: {len(result.markdown)} 字符, {len(figures)} 张图片",
        progress_pct=100,
    )

    content_list_json = None
    if result.content_list:
        content_list_json = json.dumps(result.content_list, ensure_ascii=False)

    return {
        "markdown_content": result.markdown,
        "content_list_json": content_list_json,
        "parsed_dir": str(result.output_dir),
        "detected_language": detected_lang,
        "figures_json": json.dumps(figures, ensure_ascii=False),
    }


def extract_node(state: PipelineState) -> dict:
    """节点 2: 使用 LLM 提取论文信息。"""
    from .extraction.extractor import extract_paper_summary

    single_pass_mode = state.get("single_pass_extraction", False)
    extract_mode_label = "单轮提取" if single_pass_mode else "三遍阅读法"
    _notify(state, 2, "extract", "started", f"使用 LLM 提取论文信息 ({extract_mode_label})")
    logger.info("=" * 60)
    logger.info("步骤 2/5: 使用 LLM 提取论文信息 (%s)", extract_mode_label)
    logger.info("=" * 60)

    workspace = Path(state["workspace"])
    pdf_input = state["pdf_path"]
    is_url = pdf_input.startswith("http://") or pdf_input.startswith("https://")
    use_cache = state.get("use_cache", True)

    summary = None
    cache_key = None
    if use_cache and not is_url:
        cache_key = cache_key_for_pdf(Path(pdf_input), "summary_mp")
    if cache_key:
        summary = get_cached(workspace, cache_key, PaperSummary)

    stem = pdf_stem(pdf_input)

    if summary is None:
        existing_file = workspace / "scripts" / f"{stem}_summary.json"
        if existing_file.exists():
            try:
                summary = PaperSummary.model_validate_json(existing_file.read_text(encoding="utf-8"))
                logger.info("使用已有提取结果: %s", existing_file)
            except Exception:
                pass

    if summary is None:
        model = state.get("extract_model") or state.get("llm_model", "kimi-k2-0905-preview")
        scan_model = state.get("scan_model") or model

        images_dir = None
        parsed_dir = state.get("parsed_dir")
        if parsed_dir:
            candidate = Path(parsed_dir) / "images"
            if candidate.exists():
                images_dir = candidate

        content_list = None
        cl_json = state.get("content_list_json")
        if cl_json:
            content_list = json.loads(cl_json)

        summary = extract_paper_summary(
            state["markdown_content"],
            model=model,
            scan_model=scan_model,
            figure_model=state.get("figure_model"),
            images_dir=images_dir,
            content_list=content_list,
            api_key=state.get("extract_api_key"),
            api_base=state.get("extract_api_base"),
            scan_api_key=state.get("scan_api_key"),
            scan_api_base=state.get("scan_api_base"),
            figure_api_key=state.get("figure_api_key"),
            figure_api_base=state.get("figure_api_base"),
            on_token=_make_on_token(str(workspace), "extract"),
            single_pass=single_pass_mode,
        )
        if cache_key:
            set_cached(workspace, cache_key, summary)

    # 从 arXiv ID 推断年份作为校验/修正
    arxiv_match = re.match(r"(\d{2})(\d{2})\.", stem)
    if arxiv_match:
        arxiv_year = 2000 + int(arxiv_match.group(1))
        if summary.year is None or summary.year != arxiv_year:
            logger.info("从 arXiv ID 修正年份: %s -> %s", summary.year, arxiv_year)
            summary.year = arxiv_year

    summary_json = summary.model_dump_json(indent=2)

    out = workspace / "scripts" / f"{stem}_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(summary_json, encoding="utf-8")

    logger.info("已提取: '%s' by %s", summary.title, ", ".join(summary.authors[:3]))
    logger.info(
        "提取结果: title='%s', authors=%d, method_steps=%d, formulas=%d, figures=%d, contributions=%d",
        summary.title[:60],
        len(summary.authors),
        len(summary.method.key_steps),
        len(summary.method.formulas),
        len(summary.figures),
        len(summary.contributions),
    )

    _notify(state, 2, "extract", "completed", f"已提取: '{summary.title}'", progress_pct=100)

    return {"paper_summary_json": summary_json}


def quality_gate_node(state: PipelineState) -> dict:
    """节点 2b: 质量门控 — 检测 → (交互模式) 暂停让用户决定 → 可选修复。

    非交互模式: 自动检测 + 修复。
    交互模式: 检测后暂停展示报告，用户决定是否修复。
    """
    from .quality.gate import run_quality_gate, QUALITY_THRESHOLD
    from .quality.evaluator import ExtractionEvaluator

    _notify(state, 2, "quality_gate", "started", "质量门控：评估提取结果")
    logger.info("=" * 60)
    logger.info("步骤 2b: 质量门控")
    logger.info("=" * 60)

    summary = PaperSummary.model_validate_json(state["paper_summary_json"])
    markdown = state["markdown_content"]
    content_list_json_str = state.get("content_list_json")

    # 阶段 1: 质量检测
    evaluator = ExtractionEvaluator(markdown)
    pre_result = evaluator.evaluate_fast(summary)
    _notify(
        state, 2, "quality_gate", "progress",
        f"初始评分: {pre_result.fast_total:.1f}/{pre_result.max_total:.1f}",
        progress_pct=50,
        quality_score=round(pre_result.fast_total, 2),
        quality_max=round(pre_result.max_total, 2),
        quality_threshold=QUALITY_THRESHOLD,
        quality_detail=pre_result.l2.__dict__,
        phase="pre_repair",
    )

    # 阶段 2 (交互模式): 暂停，让用户决定是否修复
    skip_repair = False
    if state.get("interactive_mode"):
        from .quality.gate import _identify_weaknesses
        weaknesses = _identify_weaknesses(pre_result)
        passed = pre_result.fast_total >= QUALITY_THRESHOLD
        decision = interrupt({
            "step": "quality_gate",
            "message": (
                f"质量检测完成，总分 {pre_result.fast_total:.1f}/{pre_result.max_total:.1f}"
                f"（阈值 {QUALITY_THRESHOLD:.1f}，{'已达标' if passed else '建议修复'}）"
            ),
            "quality_score": round(pre_result.fast_total, 2),
            "quality_max": round(pre_result.max_total, 2),
            "quality_threshold": QUALITY_THRESHOLD,
            "quality_passed": passed,
            "quality_l1": pre_result.l1.__dict__,
            "quality_l2": pre_result.l2.__dict__,
            "quality_weaknesses": weaknesses,
            "quality_detail": pre_result.l2.__dict__,
        })
        action = decision.get("action", "repair") if isinstance(decision, dict) else "repair"
        if action == "skip_repair":
            skip_repair = True
            logger.info("用户跳过 AI 修复，直接进入脚本生成")
            _notify(
                state, 2, "quality_gate", "completed",
                "用户跳过修复，继续生成脚本",
                progress_pct=100,
                quality_score=round(pre_result.fast_total, 2),
                quality_max=round(pre_result.max_total, 2),
                quality_threshold=QUALITY_THRESHOLD,
                quality_detail=pre_result.l2.__dict__,
                phase="pre_repair",
            )
            return {}

    if not skip_repair:
        # 阶段 3: AI 修复
        _notify(state, 2, "quality_gate", "progress", "正在进行 AI 修复...", progress_pct=60)
        summary = run_quality_gate(
            summary,
            markdown,
            state,
            content_list_json=content_list_json_str,
            on_token_factory=_make_on_token,
        )

        # 修复后评分
        post_result = evaluator.evaluate_fast(summary)
        passed = post_result.fast_total >= QUALITY_THRESHOLD
        _notify(
            state, 2, "quality_gate", "completed",
            f"质量门控完成: {post_result.fast_total:.1f}/{post_result.max_total:.1f} ({'通过' if passed else '已尽力修复'})",
            progress_pct=100,
            quality_score=round(post_result.fast_total, 2),
            quality_max=round(post_result.max_total, 2),
            quality_threshold=QUALITY_THRESHOLD,
            quality_passed=passed,
            quality_detail={
                "l1": post_result.l1.__dict__,
                "l2": post_result.l2.__dict__,
            },
            phase="post_repair",
        )

        summary_json = summary.model_dump_json(indent=2)

        workspace = Path(state["workspace"])
        stem = pdf_stem(state["pdf_path"])
        out = workspace / "scripts" / f"{stem}_summary.json"
        out.write_text(summary_json, encoding="utf-8")

        return {"paper_summary_json": summary_json}

    return {}


def review_extract_node(state: PipelineState) -> dict:
    """交互审核节点：提取结果审核（质量门控在之后自动运行）。

    独立于 extract_node，避免 LangGraph resume 时重跑整个提取流程。
    支持的 action：
      - "approve"：批准提取结果，进入质量门控
      - "edit"：编辑提取结果后继续，进入质量门控
    """
    if not state.get("interactive_mode"):
        return {}

    summary_json = state["paper_summary_json"]
    decision = interrupt(
        {
            "step": "extract",
            "artifact_type": "paper_summary",
            "data": json.loads(summary_json),
            "message": "论文信息提取完成，请审核或编辑后继续",
        }
    )
    action = decision.get("action", "approve") if isinstance(decision, dict) else "approve"

    if action == "edit" and "data" in decision:
        summary = PaperSummary(**decision["data"])
        summary_json = summary.model_dump_json(indent=2)

        workspace = Path(state["workspace"])
        stem = pdf_stem(state["pdf_path"])
        out = workspace / "scripts" / f"{stem}_summary.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(summary_json, encoding="utf-8")
        logger.info("用户已编辑提取结果")
        return {"paper_summary_json": summary_json}

    return {}


def script_node(state: PipelineState) -> dict:
    """节点 3: 多 Agent 协作生成视频脚本。"""
    from .output.scriptwriter import generate_video_script

    _notify(state, 3, "script", "started", "多 Agent 协作生成视频脚本")
    logger.info("=" * 60)
    logger.info("步骤 3/5: 多 Agent 协作生成视频脚本")
    logger.info("=" * 60)

    summary = PaperSummary.model_validate_json(state["paper_summary_json"])
    story_model = state.get("story_model") or state.get("script_model") or state.get("llm_model", "kimi-k2-0905-preview")
    scene_model = state.get("scene_model") or state.get("script_model") or state.get("llm_model", "kimi-k2-0905-preview")
    lang = state.get("detected_language") or state.get("language", "zh")
    preset = state.get("video_preset", "landscape")
    w, h = VIDEO_PRESETS.get(preset, (1920, 1080))

    workspace = Path(state["workspace"])
    use_cache = state.get("use_cache", True)
    theme = state.get("theme", "academic")
    narration_style = state.get("narration_style", "default")
    logger.info(
        "脚本参数: theme=%s, narration_style=%s, story_model=%s, scene_model=%s, lang=%s",
        theme, narration_style, story_model, scene_model, lang,
    )
    script_cache_key = (
        cache_key_for_content(
            state["paper_summary_json"],
            "script_ma",
            lang,
            preset,
            theme,
            narration_style,
        )
        if use_cache
        else None
    )

    script = None
    if script_cache_key:
        script = get_cached(workspace, script_cache_key, VideoScript)

    if script is None:
        def _on_agent_step(agent: str, message: str) -> None:
            """将 Agent 步骤进度转发为 pipeline 进度通知。"""
            _notify(state, 3, "script", "progress", message, agent_name=agent)

        logger.info("脚本生成: story_model=%s, scene_model=%s", story_model, scene_model)
        script = generate_video_script(
            summary,
            story_model=story_model,
            scene_model=scene_model,
            story_api_key=state.get("story_api_key"),
            story_api_base=state.get("story_api_base"),
            scene_api_key=state.get("scene_api_key"),
            scene_api_base=state.get("scene_api_base"),
            fps=state.get("fps", 30),
            language=lang,
            width=w,
            height=h,
            narration_style=narration_style,
            theme=theme,
            on_token=_make_on_token(str(workspace), "script"),
            on_agent_step=_on_agent_step,
        )

    # 将提取的图片分配给场景
    # 按 importance 降序排列，确保用户标记的高分图片优先使用
    analyzed_figures = (
        sorted(
            summary.figures,
            key=lambda f: f.importance,
            reverse=True,
        )
        if summary.figures
        else []
    )
    raw_figures = json.loads(state.get("figures_json", "[]"))

    if analyzed_figures:
        used_indices: set[int] = set()
        figure_scenes = [s for s in script.scenes if s.type.value == "figure"]

        # 第一轮：figure 场景优先使用 LLM 指定的 figure_index
        for fscene in figure_scenes:
            idx = fscene.data.get("figure_index")
            if idx is not None and 0 <= int(idx) < len(analyzed_figures):
                chosen = analyzed_figures[int(idx)]
                used_indices.add(int(idx))
            else:
                # 回退：选第一个未使用的图
                chosen = next(
                    (f for i, f in enumerate(analyzed_figures) if i not in used_indices),
                    None,
                )
                if chosen is None:
                    continue
                used_indices.add(analyzed_figures.index(chosen))

            fscene.data["figurePath"] = f"figures/{Path(chosen.path).name}"
            if not fscene.data.get("caption"):
                fscene.data["caption"] = chosen.caption
            if chosen.description and not fscene.data.get("description"):
                fscene.data["description"] = chosen.description
            fscene.data.pop("figure_index", None)

        # 第二轮：其他非辅助场景分配剩余图片（按 figure_type 匹配）
        remaining = [f for i, f in enumerate(analyzed_figures) if i not in used_indices]
        for scene in script.scenes:
            if scene.type.value in _SKIP_AUX_FIGURES:
                continue
            matched = [f for f in remaining if f.figure_type == scene.type.value][:2]
            if not matched:
                matched = remaining[:2]
            if matched:
                scene.data["figures"] = [f"figures/{Path(f.path).name}" for f in matched]
                scene.data["figure_captions"] = [f.caption for f in matched]
                for m in matched:
                    if m in remaining:
                        remaining.remove(m)

    elif raw_figures:
        figure_scenes = [s for s in script.scenes if s.type.value == "figure"]
        remaining_figs = list(raw_figures)

        for fscene in figure_scenes:
            idx = fscene.data.get("figure_index")
            if idx is not None and 0 <= int(idx) < len(remaining_figs):
                best = remaining_figs[int(idx)]
                remaining_figs = [f for i, f in enumerate(remaining_figs) if i != int(idx)]
            elif remaining_figs:
                best = remaining_figs.pop(0)
            else:
                continue
            fscene.data["figurePath"] = f"figures/{Path(best['path']).name}"
            if not fscene.data.get("caption"):
                fscene.data["caption"] = best.get("caption", "")
            fscene.data.pop("figure_index", None)

        for scene in script.scenes:
            if scene.type.value in _SKIP_AUX_FIGURES:
                continue
            if not remaining_figs:
                break
            assigned = remaining_figs[:2]
            remaining_figs = remaining_figs[2:]
            scene.data["figures"] = [f"figures/{Path(f['path']).name}" for f in assigned]
            scene.data["figure_captions"] = [f.get("caption", "") for f in assigned]

    if script_cache_key:
        set_cached(workspace, script_cache_key, script)

    type_counts = Counter(s.type.value for s in script.scenes)
    logger.info("场景类型分布: %s", dict(type_counts))

    script_json_str = script.model_dump_json()

    stem = pdf_stem(state["pdf_path"])
    script_out = workspace / "scripts" / f"{stem}_script.json"
    script_out.parent.mkdir(parents=True, exist_ok=True)
    script_out.write_text(
        json.dumps(script.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("脚本: %d 个场景, 约 %.0f 秒", len(script.scenes), script.total_duration_seconds)
    _notify(
        state,
        3,
        "script",
        "completed",
        f"脚本: {len(script.scenes)} 个场景, 约 {script.total_duration_seconds:.0f} 秒",
        progress_pct=100,
    )

    return {"video_script_json": script_json_str}


def review_script_node(state: PipelineState) -> dict:
    """交互审核节点：脚本审核。"""
    if not state.get("interactive_mode"):
        return {}

    script_json_str = state["video_script_json"]
    decision = interrupt(
        {
            "step": "script",
            "artifact_type": "video_script",
            "data": json.loads(script_json_str),
            "message": "视频脚本生成完成，请审核旁白和场景后继续",
        }
    )
    action = decision.get("action", "approve") if isinstance(decision, dict) else "approve"
    if action == "edit" and "data" in decision:
        script = VideoScript(**decision["data"])
        script_json_str = script.model_dump_json()

        workspace = Path(state["workspace"])
        stem = pdf_stem(state["pdf_path"])
        script_out = workspace / "scripts" / f"{stem}_script.json"
        script_out.parent.mkdir(parents=True, exist_ok=True)
        script_out.write_text(
            json.dumps(script.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("用户已编辑视频脚本")
        return {"video_script_json": script_json_str}

    return {}


def tts_node(state: PipelineState) -> dict:
    """节点 4: 合成旁白语音。"""
    from .output.tts import synthesize_narration

    if state.get("skip_tts"):
        logger.info("步骤 4/5: TTS 已跳过")
        _notify(state, 4, "tts", "completed", "TTS 已跳过", progress_pct=100)
        return {}

    _notify(state, 4, "tts", "started", "合成旁白语音")
    logger.info("=" * 60)
    logger.info("步骤 4/5: 合成旁白语音")
    logger.info("=" * 60)

    workspace = Path(state["workspace"])
    script = VideoScript.model_validate_json(state["video_script_json"])

    # 旁白语言始终由 language 参数控制（非论文原文语言）
    narration_lang = state.get("language", "zh")
    if narration_lang == "auto":
        narration_lang = "zh"
    script = synthesize_narration(
        script,
        workspace / "audio",
        voice=state.get("tts_voice"),
        language=narration_lang,
        speech_rate=state.get("speech_rate", 0),
    )

    audio_count = sum(1 for s in script.scenes if s.audio_file)
    total_duration = script.total_duration_seconds
    logger.info("TTS 完成: %d 个音频文件, 总时长 %.1f 秒", audio_count, total_duration)

    stem = pdf_stem(state["pdf_path"])
    script_path = workspace / "scripts" / f"{stem}_script.json"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        json.dumps(script.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _notify(state, 4, "tts", "completed", "语音合成完成", progress_pct=100)

    return {"video_script_json": script.model_dump_json()}


def visual_director_node(state: PipelineState) -> dict:
    """节点 4.5: TTS 后运行视觉导演，用真实 word_timings 精细化动画编排。"""
    script = VideoScript.model_validate_json(state["video_script_json"])

    has_word_timings = any(s.word_timings for s in script.scenes)
    if not has_word_timings:
        logger.info("视觉导演: 无 word_timings，跳过精细编排")
        return {}

    from .output.visual_director import choreograph_scenes
    from .schemas import SceneNarration
    from .schemas_compat import _rebuild_blueprint_from_script

    blueprint = _rebuild_blueprint_from_script(script)

    narrations = [
        SceneNarration(
            scene_index=i,
            narration=s.narration,
            data=s.data,
        )
        for i, s in enumerate(script.scenes)
    ]

    scene_word_timings = [s.word_timings for s in script.scenes]
    scene_durations_ms = [int(s.duration_in_frames / script.meta.fps * 1000) for s in script.scenes]

    choreographies = choreograph_scenes(
        blueprint, narrations, scene_word_timings, scene_durations_ms,
    )

    for choreo in choreographies:
        if choreo.scene_index < len(script.scenes):
            script.scenes[choreo.scene_index].choreography = choreo.phases

    updated_indices = [c.scene_index for c in choreographies]
    logger.info("编排更新场景: %s", updated_indices)

    from .output.visual_director import assign_manim_animations

    manim_specs = assign_manim_animations(blueprint, narrations, scene_durations_ms)
    for i, specs in enumerate(manim_specs):
        if i < len(script.scenes) and specs:
            script.scenes[i].manim_animations = specs

    logger.info("视觉导演: 已用 word_timings 更新 %d 个场景的动画编排", len(choreographies))

    return {"video_script_json": script.model_dump_json()}


def manim_render_node(state: PipelineState) -> dict:
    """节点 4.6: 使用 Manim 预渲染数学动画片段。"""
    script = VideoScript.model_validate_json(state["video_script_json"])

    has_manim = any(s.manim_animations for s in script.scenes)
    if not has_manim:
        logger.info("Manim 渲染: 无需渲染的数学动画，跳过")
        return {}

    manim_scenes = [i for i, s in enumerate(script.scenes) if s.manim_animations]
    logger.info("Manim 动画场景: %s", manim_scenes)

    from .output.manim_renderer import render_manim_clips

    _notify(state, 5, "render", "progress", "使用 Manim 预渲染数学动画片段", progress_pct=10)
    workspace = Path(state["workspace"])
    script = render_manim_clips(script, workspace, quality="medium_quality")

    return {"video_script_json": script.model_dump_json()}


def review_tts_node(state: PipelineState) -> dict:
    """交互审核节点：TTS 试听。"""
    if not state.get("interactive_mode"):
        return {}

    script = VideoScript.model_validate_json(state["video_script_json"])
    audio_files = [s.audio_file for s in script.scenes if s.audio_file]
    interrupt(
        {
            "step": "tts",
            "artifact_type": "audio",
            "data": {"audio_files": audio_files, "scene_count": len(script.scenes)},
            "message": "语音合成完成，请试听后继续渲染",
        }
    )
    return {}


def render_node(state: PipelineState) -> dict:
    """节点 5: 使用 Remotion 渲染视频。"""
    from .output.renderer import render_video

    if state.get("skip_render"):
        logger.info("步骤 5/5: 渲染已跳过")
        _notify(state, 5, "render", "completed", "渲染已跳过", progress_pct=100)
        return {}

    _notify(state, 5, "render", "started", "使用 Remotion 渲染视频")
    logger.info("=" * 60)
    logger.info("步骤 5/5: 使用 Remotion 渲染视频")
    logger.info("=" * 60)

    workspace = Path(state["workspace"])
    script = VideoScript.model_validate_json(state["video_script_json"])

    stem = pdf_stem(state["pdf_path"])
    output_path = state.get("output_path")
    if not output_path:
        output_path = str(workspace / "output" / f"{stem}.mp4")

    parsed_dir = state.get("parsed_dir")
    result = render_video(
        script,
        Path(output_path),
        workspace=workspace,
        parsed_dir=Path(parsed_dir) if parsed_dir else None,
    )

    logger.info("视频已渲染: %s", result)
    _notify(state, 5, "render", "completed", f"视频已渲染: {result}", progress_pct=100)
    return {"output_video": str(result)}


# ---------------------------------------------------------------------------
# 质量路由（未来扩展）
# ---------------------------------------------------------------------------


def route_after_extract(state: PipelineState) -> Literal["review_extract_node", "extract_node"]:
    """提取后路由：摘要过短时触发重新提取，否则进入审核节点。"""
    summary_json = state.get("paper_summary_json", "")
    if len(summary_json) < 100:
        logger.warning("摘要过短，正在重新提取...")
        return "extract_node"
    return "review_extract_node"



def route_tts_or_skip(state: PipelineState) -> Literal["tts_node", "render_node"]:
    """根据配置跳过 TTS。"""
    if state.get("skip_tts"):
        return "render_node"
    return "tts_node"


# ---------------------------------------------------------------------------
# 图构建
# ---------------------------------------------------------------------------


def build_graph(*, with_checkpointer: bool = False, interactive: bool = False) -> StateGraph:
    """构建 LangGraph 流水线。

    参数:
        with_checkpointer: 为 True 时添加 InMemorySaver，
                          支持人机交互和持久化。
        interactive: 为 True 时自动启用 checkpointer（interrupt 依赖它）。

    返回:
        编译后的 StateGraph，可直接调用。
    """
    builder = StateGraph(PipelineState)

    builder.add_node("parse_node", parse_node)
    builder.add_node("extract_node", extract_node)
    builder.add_node("quality_gate_node", quality_gate_node)
    builder.add_node("review_extract_node", review_extract_node)
    builder.add_node("script_node", script_node)
    builder.add_node("review_script_node", review_script_node)
    builder.add_node("tts_node", tts_node)
    builder.add_node("visual_director_node", visual_director_node)
    builder.add_node("manim_render_node", manim_render_node)
    builder.add_node("review_tts_node", review_tts_node)
    builder.add_node("render_node", render_node)

    builder.add_edge(START, "parse_node")
    builder.add_edge("parse_node", "extract_node")

    builder.add_conditional_edges(
        "extract_node",
        route_after_extract,
        {"review_extract_node": "review_extract_node", "extract_node": "extract_node"},
    )

    builder.add_edge("review_extract_node", "quality_gate_node")
    builder.add_edge("quality_gate_node", "script_node")
    builder.add_edge("script_node", "review_script_node")
    builder.add_edge("review_script_node", "tts_node")
    builder.add_edge("tts_node", "visual_director_node")
    builder.add_edge("visual_director_node", "manim_render_node")
    builder.add_edge("manim_render_node", "review_tts_node")
    builder.add_edge("review_tts_node", "render_node")
    builder.add_edge("render_node", END)

    use_checkpointer = with_checkpointer or interactive
    checkpointer = InMemorySaver() if use_checkpointer else None
    return builder.compile(checkpointer=checkpointer)


_STEP_ORDER = ["parse", "extract", "script", "tts", "render"]
_STEP_TO_NODE = {
    "parse": "parse_node",
    "extract": "extract_node",
    "script": "script_node",
    "tts": "tts_node",
    "render": "render_node",
}

_ALL_NODE_FUNCS = {
    "parse_node": parse_node,
    "extract_node": extract_node,
    "quality_gate_node": quality_gate_node,
    "review_extract_node": review_extract_node,
    "script_node": script_node,
    "review_script_node": review_script_node,
    "tts_node": tts_node,
    "visual_director_node": visual_director_node,
    "manim_render_node": manim_render_node,
    "review_tts_node": review_tts_node,
    "render_node": render_node,
}

_STEP_CHAIN = [
    "parse_node",
    "extract_node",
    "review_extract_node",
    "quality_gate_node",
    "script_node",
    "review_script_node",
    "tts_node",
    "visual_director_node",
    "manim_render_node",
    "review_tts_node",
    "render_node",
]


def build_partial_graph(start_step: str, *, interactive: bool = False) -> StateGraph:
    """构建从指定步骤开始的子图。

    参数:
        start_step: 起始步骤 ("parse" | "extract" | "script" | "tts" | "render")

    返回:
        编译后的 StateGraph（仅包含从 start_step 开始的节点）。
    """
    if start_step not in _STEP_ORDER:
        raise ValueError(f"无效步骤: {start_step}，有效值: {_STEP_ORDER}")

    first_node = _STEP_TO_NODE[start_step]
    start_idx = _STEP_CHAIN.index(first_node)
    chain = _STEP_CHAIN[start_idx:]

    builder = StateGraph(PipelineState)
    for node_name in chain:
        builder.add_node(node_name, _ALL_NODE_FUNCS[node_name])

    builder.add_edge(START, chain[0])

    for i in range(len(chain) - 1):
        src, dst = chain[i], chain[i + 1]
        if src == "extract_node" and dst == "review_extract_node":
            builder.add_conditional_edges(
                src,
                route_after_extract,
                {"review_extract_node": dst, "extract_node": src},
            )
        else:
            builder.add_edge(src, dst)

    builder.add_edge(chain[-1], END)
    checkpointer = InMemorySaver() if interactive else None
    return builder.compile(checkpointer=checkpointer)


def run_pipeline_from(
    step: str,
    workspace: str | Path,
    *,
    existing_state: dict,
    progress: ProgressCallback | None = None,
) -> dict:
    """从指定步骤开始执行流水线（非交互模式），使用已有的中间产物。

    参数:
        step: 起始步骤 ("parse" | "extract" | "script" | "tts" | "render")
        workspace: 工作目录。
        existing_state: 已有的流水线状态（包含输入参数和中间产物）。
        progress: 进度回调。

    返回:
        包含所有结果的最终流水线状态字典。
    """
    graph = build_partial_graph(step)

    state = dict(existing_state)
    ws_str = str(Path(workspace).resolve())
    state["workspace"] = ws_str
    if progress:
        register_progress_callback(ws_str, progress)

    try:
        result = graph.invoke(state)
    finally:
        unregister_progress_callback(ws_str)

    logger.info("从步骤 '%s' 重跑完成", step)
    return result


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------


def run_pipeline(
    pdf_path: str | Path,
    output_path: str | Path | None = None,
    *,
    workspace: str | Path | None = None,
    llm_model: str | None = None,
    extract_model: str | None = None,
    scan_model: str | None = None,
    script_model: str | None = None,
    story_model: str | None = None,
    scene_model: str | None = None,
    gate_model: str | None = None,
    judge_model: str | None = None,
    language: str = "zh",
    tts_voice: str | None = None,
    mineru_backend: str = "pipeline",
    fps: int = 30,
    video_preset: str = "landscape",
    skip_tts: bool = False,
    skip_render: bool = False,
    use_cache: bool = True,
    narration_style: str = "default",
    theme: str = "academic",
    speech_rate: int = 0,
    single_pass_extraction: bool = False,
    progress: ProgressCallback | None = None,
) -> dict:
    """运行完整的论文到视频流水线。

    参数:
        pdf_path: 输入 PDF 文件路径。
        output_path: 输出视频路径。
        workspace: 工作目录（默认: ``./workspace``）。
        llm_model: LiteLLM 模型标识符（作为后备）。
        extract_model: Pass 2 信息提取模型。
        scan_model: Pass 1 快速扫描模型。
        script_model: 脚本生成模型（story + scene 的通用后备）。
        story_model: 故事架构师模型。
        scene_model: 场景编剧模型。
        gate_model: 质量门控模型。
        judge_model: L3 评估模型。
        language: 主要语言提示。设为 ``"auto"`` 自动检测。
        tts_voice: Edge TTS 声音名称（*None* 时自动选择）。
        mineru_backend: MinerU 后端（``"pipeline"`` 为 CPU 模式）。
        fps: 视频帧率。
        skip_tts: 跳过 TTS 步骤。
        skip_render: 跳过 Remotion 渲染。
        use_cache: 启用结果缓存。
        narration_style: 旁白风格。
        progress: 进度回调对象，实现 ProgressCallback 协议。

    返回:
        包含所有结果的最终流水线状态字典。
    """
    default_cfg = LLMConfig()

    def _pick(explicit: str | None, cfg_val: str) -> str:
        return explicit if explicit else cfg_val

    llm_cfg = LLMConfig(
        scan_model=_pick(scan_model, default_cfg.scan_model),
        extract_model=_pick(extract_model, default_cfg.extract_model),
        figure_model=default_cfg.figure_model,
        story_model=_pick(story_model, default_cfg.story_model),
        scene_model=_pick(scene_model, default_cfg.scene_model),
        gate_model=_pick(gate_model, default_cfg.gate_model),
        judge_model=_pick(judge_model, default_cfg.judge_model),
        script_model=_pick(script_model, default_cfg.script_model),
        scan_api_key=default_cfg.scan_api_key,
        scan_api_base=default_cfg.scan_api_base,
        extract_api_key=default_cfg.extract_api_key,
        extract_api_base=default_cfg.extract_api_base,
        figure_api_key=default_cfg.figure_api_key,
        figure_api_base=default_cfg.figure_api_base,
        story_api_key=default_cfg.story_api_key,
        story_api_base=default_cfg.story_api_base,
        scene_api_key=default_cfg.scene_api_key,
        scene_api_base=default_cfg.scene_api_base,
        gate_api_key=default_cfg.gate_api_key,
        gate_api_base=default_cfg.gate_api_base,
        judge_api_key=default_cfg.judge_api_key,
        judge_api_base=default_cfg.judge_api_base,
        script_api_key=default_cfg.script_api_key,
        script_api_base=default_cfg.script_api_base,
    )

    pdf_str = str(pdf_path)
    is_url = pdf_str.startswith("http://") or pdf_str.startswith("https://")
    resolved_pdf = pdf_str if is_url else str(Path(pdf_path).resolve())
    resolved_ws = str(Path(workspace or "./workspace").resolve())

    pipeline_input = PipelineInput(
        pdf_path=resolved_pdf,
        workspace=resolved_ws,
        llm_model=llm_model or llm_cfg.extract_model,
        extract_model=llm_cfg.extract_model,
        scan_model=llm_cfg.scan_model,
        figure_model=llm_cfg.figure_model,
        story_model=llm_cfg.story_model,
        scene_model=llm_cfg.scene_model,
        gate_model=llm_cfg.gate_model,
        judge_model=llm_cfg.judge_model,
        script_model=llm_cfg.script_model,
        extract_api_key=llm_cfg.extract_api_key,
        extract_api_base=llm_cfg.extract_api_base,
        scan_api_key=llm_cfg.scan_api_key,
        scan_api_base=llm_cfg.scan_api_base,
        figure_api_key=llm_cfg.figure_api_key,
        figure_api_base=llm_cfg.figure_api_base,
        story_api_key=llm_cfg.story_api_key,
        story_api_base=llm_cfg.story_api_base,
        scene_api_key=llm_cfg.scene_api_key,
        scene_api_base=llm_cfg.scene_api_base,
        gate_api_key=llm_cfg.gate_api_key,
        gate_api_base=llm_cfg.gate_api_base,
        judge_api_key=llm_cfg.judge_api_key,
        judge_api_base=llm_cfg.judge_api_base,
        script_api_key=llm_cfg.script_api_key,
        script_api_base=llm_cfg.script_api_base,
        language=language,
        tts_voice=tts_voice,
        mineru_backend=mineru_backend,
        fps=fps,
        video_preset=video_preset,
        skip_tts=skip_tts,
        skip_render=skip_render,
        use_cache=use_cache,
        narration_style=narration_style,
        theme=theme,
        speech_rate=speech_rate,
        single_pass_extraction=single_pass_extraction,
        output_path=str(Path(output_path).resolve()) if output_path else None,
    )

    logger.info(
        "流水线配置: extract=%s, scan=%s, figure=%s, story=%s, scene=%s, gate=%s",
        llm_cfg.extract_model,
        llm_cfg.scan_model,
        llm_cfg.figure_model,
        llm_cfg.story_model,
        llm_cfg.scene_model,
        llm_cfg.gate_model,
    )

    interactive = pipeline_input.interactive_mode
    graph = build_graph(interactive=interactive)

    initial_state: PipelineState = {
        **pipeline_input.model_dump(),
    }

    ws_str = initial_state.get("workspace", "")
    if progress and ws_str:
        register_progress_callback(ws_str, progress)

    config = {"configurable": {"thread_id": pdf_stem(resolved_pdf)}} if interactive else None
    try:
        result = graph.invoke(initial_state, config=config)
    finally:
        if ws_str:
            unregister_progress_callback(ws_str)

    logger.info("=" * 60)
    logger.info("流水线完成！")
    if result.get("output_video"):
        logger.info("输出: %s", result["output_video"])
    logger.info("=" * 60)

    return result
