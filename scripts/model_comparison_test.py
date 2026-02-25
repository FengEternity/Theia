"""模型对比测试 v3：三层评估框架（L1 规则 + L2 NLP + L3 LLM-as-Judge）。

测试维度：
  - L1 规则检查：Schema 合规、字段完整性、数值可验证性
  - L2 NLP 指标：事实锚定率、实体匹配、章节覆盖率、多样性
  - L3 LLM-as-Judge：忠实度、覆盖、洞察质量、视频适配度
  - 推理模型 vs 非推理模型效果对比
  - 生成速度与成本

用法：
    cd /Users/montylee/code/Theia
    PYTHONUNBUFFERED=1 PYTHONPATH=packages/agent \\
        packages/agent/.venv/bin/python scripts/model_comparison_test.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import litellm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "agent"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from theia.evaluator import ExtractionEvaluator, EvalResult
from theia.llm_config import (
    split_sections_with_labels,
    budget_truncate,
    get_section_headings,
)
from theia.schemas import PaperSummary, PaperOverview
from theia.extractor import (
    PASS1_SYSTEM_PROMPT,
    PASS2_SYSTEM_PROMPT,
    _strip_json_fences,
)

SF_API_KEY = os.environ["SILICONFLOW_API_KEY"]
SF_API_BASE = os.environ["SILICONFLOW_API_BASE"]

AZURE_API_KEY = os.environ.get("OPENAI_API_KEY", "")
AZURE_API_BASE = os.environ.get("OPENAI_API_BASE", "")

PAPER_PATH = Path("workspace/tasks/9493d9ed7480/parsed/2512.22047.md")

# ===================================================================
# 模型列表（按推理/非推理分类）
# ===================================================================

MODELS_TO_TEST: list[dict[str, Any]] = [
    # --- 非推理模型 ---
    {
        "name": "DeepSeek-V3.2",
        "model_id": "openai/deepseek-ai/DeepSeek-V3.2",
        "api_key": SF_API_KEY,
        "api_base": SF_API_BASE,
        "reasoning": False,
        "input_price_rmb": 2.0,
        "output_price_rmb": 3.0,
        "provider": "SiliconFlow",
    },
    {
        "name": "DeepSeek-V3",
        "model_id": "openai/deepseek-ai/DeepSeek-V3",
        "api_key": SF_API_KEY,
        "api_base": SF_API_BASE,
        "reasoning": False,
        "input_price_rmb": 2.0,
        "output_price_rmb": 8.0,
        "provider": "SiliconFlow",
    },
    {
        "name": "GLM-4.7",
        "model_id": "openai/Pro/zai-org/GLM-4.7",
        "api_key": SF_API_KEY,
        "api_base": SF_API_BASE,
        "reasoning": False,
        "input_price_rmb": 4.0,
        "output_price_rmb": 16.0,
        "provider": "SiliconFlow",
    },
    {
        "name": "MiniMax-M2.5",
        "model_id": "openai/Pro/MiniMaxAI/MiniMax-M2.5",
        "api_key": SF_API_KEY,
        "api_base": SF_API_BASE,
        "reasoning": False,
        "input_price_rmb": 2.1,
        "output_price_rmb": 8.4,
        "provider": "SiliconFlow",
    },
    {
        "name": "Kimi-K2.5",
        "model_id": "openai/Pro/moonshotai/Kimi-K2.5",
        "api_key": SF_API_KEY,
        "api_base": SF_API_BASE,
        "reasoning": False,
        "input_price_rmb": 4.0,
        "output_price_rmb": 21.0,
        "provider": "SiliconFlow",
    },
    {
        "name": "Qwen3-235B-Instruct",
        "model_id": "openai/Qwen/Qwen3-235B-A22B-Instruct-2507",
        "api_key": SF_API_KEY,
        "api_base": SF_API_BASE,
        "reasoning": False,
        "input_price_rmb": 0.63,
        "output_price_rmb": 4.2,
        "provider": "SiliconFlow",
    },
    {
        "name": "Qwen3-32B",
        "model_id": "openai/Qwen/Qwen3-32B",
        "api_key": SF_API_KEY,
        "api_base": SF_API_BASE,
        "reasoning": False,
        "input_price_rmb": 0.98,
        "output_price_rmb": 4.0,
        "provider": "SiliconFlow",
    },
    # --- 推理模型 ---
    {
        "name": "DeepSeek-R1",
        "model_id": "openai/deepseek-ai/DeepSeek-R1",
        "api_key": SF_API_KEY,
        "api_base": SF_API_BASE,
        "reasoning": True,
        "input_price_rmb": 4.0,
        "output_price_rmb": 16.0,
        "provider": "SiliconFlow",
    },
    {
        "name": "Kimi-K2-Thinking",
        "model_id": "openai/moonshotai/Kimi-K2-Thinking",
        "api_key": SF_API_KEY,
        "api_base": SF_API_BASE,
        "reasoning": True,
        "input_price_rmb": 4.0,
        "output_price_rmb": 16.0,
        "provider": "SiliconFlow",
    },
    {
        "name": "QwQ-32B",
        "model_id": "openai/Qwen/QwQ-32B",
        "api_key": SF_API_KEY,
        "api_base": SF_API_BASE,
        "reasoning": True,
        "input_price_rmb": 1.05,
        "output_price_rmb": 4.06,
        "provider": "SiliconFlow",
    },
    {
        "name": "Qwen3-235B-Thinking",
        "model_id": "openai/Qwen/Qwen3-235B-A22B-Thinking-2507",
        "api_key": SF_API_KEY,
        "api_base": SF_API_BASE,
        "reasoning": True,
        "input_price_rmb": 0.91,
        "output_price_rmb": 4.2,
        "provider": "SiliconFlow",
    },
    # --- Baseline ---
    {
        "name": "GPT-5.2-chat (Azure)",
        "model_id": "openai/gpt-5.2-chat",
        "api_key": AZURE_API_KEY,
        "api_base": AZURE_API_BASE,
        "reasoning": False,
        "input_price_rmb": 17.5,
        "output_price_rmb": 70.0,
        "provider": "Azure",
    },
]


# ===================================================================
# 宽容 JSON 解析
# ===================================================================

def _extract_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    nums = re.findall(r"-?\d+\.?\d*", str(value))
    return float(nums[0]) if nums else None


def _strip_thinking_tags(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _fix_baselines(data: dict) -> dict:
    if "results" in data and "baselines" in data["results"]:
        fixed = []
        for b in data["results"]["baselines"]:
            if not isinstance(b, dict):
                continue
            v = _extract_number(b.get("value"))
            if v is not None:
                b["value"] = v
                fixed.append(b)
        data["results"]["baselines"] = fixed
    return data


def _lenient_parse_summary(raw_json: str) -> PaperSummary:
    raw_json = _strip_thinking_tags(raw_json)
    raw_json = _strip_json_fences(raw_json)
    data = json.loads(raw_json)
    data = _fix_baselines(data)
    if "method" in data and isinstance(data["method"], str):
        data["method"] = {"summary": data["method"], "key_steps": [], "formulas": []}
    if "results" in data and isinstance(data["results"], str):
        data["results"] = {"findings": data["results"]}
    return PaperSummary(**data)


def _lenient_parse_overview(raw_json: str) -> PaperOverview:
    raw_json = _strip_thinking_tags(raw_json)
    raw_json = _strip_json_fences(raw_json)
    return PaperOverview(**json.loads(raw_json))


# ===================================================================
# LLM 调用
# ===================================================================

def _call_llm(
    messages: list[dict],
    *,
    model_id: str,
    api_key: str,
    api_base: str,
    reasoning: bool = False,
    max_tokens: int = 4096,
    temperature: float = 0.1,
) -> tuple[str, float, dict]:
    kwargs: dict = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "api_key": api_key,
        "api_base": api_base,
    }
    if not reasoning:
        kwargs["temperature"] = temperature
        kwargs["response_format"] = {"type": "json_object"}

    removable = ["temperature", "response_format"]
    t0 = time.time()
    while True:
        try:
            resp = litellm.completion(**kwargs)
            break
        except Exception as exc:
            msg = str(exc).lower()
            removed_any = False
            for param in list(removable):
                if param in msg and param in kwargs:
                    print(f"  [retry] 移除不支持的参数 '{param}'")
                    kwargs.pop(param)
                    removable.remove(param)
                    removed_any = True
            if not removed_any:
                raise
    elapsed = time.time() - t0
    text = resp.choices[0].message.content or ""
    usage = {
        "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
        "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
    }
    return text, elapsed, usage


# ===================================================================
# Pass 1 / Pass 2
# ===================================================================

def run_pass1(scan_text: str, model_cfg: dict) -> tuple[PaperOverview | None, float, dict]:
    messages = [
        {"role": "system", "content": PASS1_SYSTEM_PROMPT},
        {"role": "user", "content": f"请快速扫描以下论文并生成阅读指南：\n\n{scan_text}"},
    ]
    try:
        raw, elapsed, usage = _call_llm(
            messages,
            model_id=model_cfg["model_id"],
            api_key=model_cfg["api_key"],
            api_base=model_cfg["api_base"],
            reasoning=model_cfg.get("reasoning", False),
            max_tokens=4096,
        )
        return _lenient_parse_overview(raw), elapsed, usage
    except Exception as exc:
        print(f"  Pass 1 失败: {type(exc).__name__}: {exc}")
        return None, 0, {}


def run_pass2(
    focused_text: str, overview: PaperOverview, model_cfg: dict,
) -> tuple[PaperSummary | None, float, dict]:
    overview_json = json.dumps(
        {"paper_type": overview.paper_type, "core_idea": overview.core_idea},
        ensure_ascii=False,
    )
    focus_list = (
        "\n".join(f"- {q}" for q in overview.reading_focus)
        if overview.reading_focus else "- 提取核心方法和实验结果"
    )
    system_prompt = PASS2_SYSTEM_PROMPT.format(
        overview_json=overview_json, reading_focus=focus_list,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请对以下论文章节进行深度阅读和信息提取：\n\n{focused_text}"},
    ]
    try:
        raw, elapsed, usage = _call_llm(
            messages,
            model_id=model_cfg["model_id"],
            api_key=model_cfg["api_key"],
            api_base=model_cfg["api_base"],
            reasoning=model_cfg.get("reasoning", False),
            max_tokens=8192,
        )
        return _lenient_parse_summary(raw), elapsed, usage
    except Exception as exc:
        print(f"  Pass 2 失败: {type(exc).__name__}: {exc}")
        return None, 0, {}


def estimate_cost(usage: dict, model_cfg: dict) -> float:
    inp = usage.get("prompt_tokens", 0) / 1_000_000 * model_cfg["input_price_rmb"]
    out = usage.get("completion_tokens", 0) / 1_000_000 * model_cfg["output_price_rmb"]
    return inp + out


# ===================================================================
# 单模型测试（L1+L2 即时评估）
# ===================================================================

def test_single_model(
    cfg: dict,
    scan_text: str,
    focused_text: str,
    evaluator: ExtractionEvaluator,
) -> dict:
    print(f"\n{'─' * 60}")
    cat = "[推理]" if cfg.get("reasoning") else "[非推理]"
    print(f"测试模型: {cfg['name']}  {cat}  ({cfg['provider']})")
    print(f"{'─' * 60}")

    # Pass 1
    print("  [Pass 1] 快速扫描...")
    overview, p1_time, p1_usage = run_pass1(scan_text, cfg)
    if overview is None:
        print("  X Pass 1 失败")
        return {"model": cfg["name"], "reasoning": cfg.get("reasoning", False), "status": "FAIL@P1"}

    print(f"  + Pass 1: {p1_time:.1f}s, type={overview.paper_type}")
    print(f"    core_idea: {overview.core_idea[:80]}...")

    # Pass 2
    print("  [Pass 2] 深度提取...")
    summary, p2_time, p2_usage = run_pass2(focused_text, overview, cfg)
    if summary is None:
        return {"model": cfg["name"], "reasoning": cfg.get("reasoning", False), "status": "FAIL@P2"}

    total_time = p1_time + p2_time
    total_usage = {
        "prompt_tokens": p1_usage.get("prompt_tokens", 0) + p2_usage.get("prompt_tokens", 0),
        "completion_tokens": p1_usage.get("completion_tokens", 0) + p2_usage.get("completion_tokens", 0),
    }
    cost = estimate_cost(p1_usage, cfg) + estimate_cost(p2_usage, cfg)

    # L1 + L2 评估
    eval_result = evaluator.evaluate_fast(summary)
    l1d = eval_result.l1.detail()
    l2d = eval_result.l2.detail()

    print(f"  + Pass 2: {p2_time:.1f}s")
    print(f"  标题: {summary.title}")
    print(f"  数据: steps={len(summary.method.key_steps)} formulas={len(summary.method.formulas)} "
          f"datasets={len(summary.results.datasets)} metrics={len(summary.results.metrics)} "
          f"baselines={len(summary.results.baselines)} contribs={len(summary.contributions)}")
    print(f"  L1({eval_result.l1.total:.2f}/2): "
          f"schema={l1d['schema_compliance']:.2f} complete={l1d['field_completeness']:.2f} "
          f"numeric={l1d['numeric_verifiability']:.2f}")
    print(f"  L2({eval_result.l2.total:.2f}/4): "
          f"ground={l2d['grounding']:.2f} entity={l2d['entity_match']:.2f} "
          f"coverage={l2d['section_coverage']:.2f} diversity={l2d['diversity']:.2f}")
    print(f"  Fast总分: {eval_result.fast_total:.2f}/6.0")
    print(f"  耗时: {total_time:.1f}s  Token: {total_usage['prompt_tokens']:,}+{total_usage['completion_tokens']:,}  "
          f"成本: ¥{cost:.4f}")

    return {
        "model": cfg["name"],
        "reasoning": cfg.get("reasoning", False),
        "provider": cfg.get("provider", ""),
        "status": "OK",
        "title": summary.title,
        "summary_obj": summary,
        "l1": l1d,
        "l2": l2d,
        "fast_total": round(eval_result.fast_total, 3),
        "p1_time": round(p1_time, 1),
        "p2_time": round(p2_time, 1),
        "total_time": round(total_time, 1),
        "prompt_tokens": total_usage["prompt_tokens"],
        "completion_tokens": total_usage["completion_tokens"],
        "cost_rmb": round(cost, 4),
        "key_steps": len(summary.method.key_steps),
        "formulas": len(summary.method.formulas),
        "datasets": len(summary.results.datasets),
        "metrics": len(summary.results.metrics),
        "baselines": len(summary.results.baselines),
        "contributions": len(summary.contributions),
    }


# ===================================================================
# L3 Judge 批量评估
# ===================================================================

def run_l3_judge(
    ok_results: list[dict],
    evaluator: ExtractionEvaluator,
    judge_model: str = "openai/gpt-5.2-chat",
    judge_api_key: str | None = None,
    judge_api_base: str | None = None,
) -> None:
    """对所有成功结果运行 L3 LLM-as-Judge 评估（原地更新 dict）。"""
    print(f"\n{'=' * 70}")
    print(f"L3 LLM-as-Judge 评估 (judge={judge_model})")
    print(f"{'=' * 70}")

    for r in ok_results:
        summary: PaperSummary = r.get("summary_obj")
        if summary is None:
            continue
        print(f"\n  评估: {r['model']}...", end=" ", flush=True)
        t0 = time.time()
        try:
            l3 = evaluator.evaluate_l3(
                summary,
                judge_model=judge_model,
                judge_api_key=judge_api_key,
                judge_api_base=judge_api_base,
            )
        except Exception as exc:
            print(f"失败: {exc}")
            r["l3"] = {"l3_total": 0, "error": str(exc)}
            r["full_total"] = r["fast_total"]
            continue

        elapsed = time.time() - t0
        r["l3"] = l3.detail()
        r["full_total"] = round(r["fast_total"] + l3.total, 3)
        print(f"{elapsed:.1f}s -> faith={l3.faithfulness:.2f} cover={l3.coverage:.2f} "
              f"insight={l3.insight:.2f} video={l3.video_ready:.2f} = {l3.total:.2f}/4")
        if l3.issues:
            print(f"    issues: {l3.issues[:3]}")
        if l3.missing:
            print(f"    missing: {l3.missing[:3]}")


# ===================================================================
# 主函数
# ===================================================================

def main():
    print("=" * 70)
    print("模型对比测试 v3 — 三层评估框架")
    print("=" * 70)

    paper = PAPER_PATH.read_text(encoding="utf-8")
    print(f"\n论文: {PAPER_PATH.name}")
    print(f"长度: {len(paper):,} 字符")

    labeled = split_sections_with_labels(paper)
    headings = get_section_headings(paper)
    truncated = budget_truncate(dict(labeled), max_chars=80_000)
    focused_text = "\n\n".join(truncated.values())

    scan_parts = ["=== 章节结构 ===", "\n".join(headings) if headings else "(无)"]
    for label in ("preamble", "abstract", "introduction"):
        c = labeled.get(label, "")
        if c:
            scan_parts.append(f"\n=== {label.upper()} ===\n{c[:8000]}")
    conclusion = labeled.get("conclusion", "")
    if conclusion:
        scan_parts.append(f"\n=== CONCLUSION ===\n{conclusion[:5000]}")
    scan_text = "\n".join(scan_parts)[:20_000]

    print(f"扫描文本: {len(scan_text):,} 字符")
    print(f"深度提取文本: {len(focused_text):,} 字符")
    print(f"\n待测模型: {len(MODELS_TO_TEST)} 个")
    print(f"  非推理: {sum(1 for m in MODELS_TO_TEST if not m.get('reasoning'))}")
    print(f"  推理:   {sum(1 for m in MODELS_TO_TEST if m.get('reasoning'))}")

    evaluator = ExtractionEvaluator(paper, labeled)

    # ---- Phase 1: 所有模型提取 + L1/L2 评估 ----
    results: list[dict] = []
    for cfg in MODELS_TO_TEST:
        try:
            r = test_single_model(cfg, scan_text, focused_text, evaluator)
        except Exception as exc:
            print(f"  X 模型异常: {type(exc).__name__}: {exc}")
            r = {"model": cfg["name"], "reasoning": cfg.get("reasoning", False), "status": f"ERROR: {exc}"}
        results.append(r)

    ok = [r for r in results if r["status"] == "OK"]
    fail = [r for r in results if r["status"] != "OK"]

    # ---- Phase 2: L3 Judge 评估 ----
    if ok:
        run_l3_judge(
            ok, evaluator,
            judge_model="openai/gpt-5.2-chat",
            judge_api_key=AZURE_API_KEY,
            judge_api_base=AZURE_API_BASE,
        )

    # ---- Phase 3: 汇总 ----
    print("\n\n" + "=" * 70)
    print("对比结果汇总（三层评估）")
    print("=" * 70)

    has_l3 = any("full_total" in r for r in ok)
    score_key = "full_total" if has_l3 else "fast_total"
    max_score = "10" if has_l3 else "6"

    if ok:
        for group_name, is_reasoning in [("--- 非推理模型 ---", False), ("--- 推理模型 ---", True)]:
            group = [r for r in ok if r["reasoning"] == is_reasoning]
            if not group:
                continue
            print(f"\n{group_name}")
            header = f"  {'模型':<28} {'L1':>4} {'L2':>4}"
            if has_l3:
                header += f" {'L3':>4} {'总分':>5}"
            else:
                header += f" {'总分':>5}"
            header += f" {'耗时':>6} {'成本¥':>8}"
            print(header)
            print(f"  {'─' * 78}")

            for r in sorted(group, key=lambda x: x.get(score_key, 0), reverse=True):
                l1t = r["l1"]["l1_total"]
                l2t = r["l2"]["l2_total"]
                line = f"  {r['model']:<28} {l1t:>4.1f} {l2t:>4.1f}"
                if has_l3:
                    l3t = r.get("l3", {}).get("l3_total", 0)
                    line += f" {l3t:>4.1f} {r.get(score_key, 0):>5.1f}"
                else:
                    line += f" {r.get(score_key, 0):>5.1f}"
                line += f" {r['total_time']:>5.1f}s {r['cost_rmb']:>8.4f}"
                print(line)

    if fail:
        print(f"\nX 失败的模型:")
        for r in fail:
            print(f"  - {r['model']}: {r['status']}")

    if ok:
        best = max(ok, key=lambda x: x.get(score_key, 0))
        cheapest = min(ok, key=lambda x: x["cost_rmb"])
        fastest = min(ok, key=lambda x: x["total_time"])
        best_value = max(ok, key=lambda x: x.get(score_key, 0) / max(x["cost_rmb"], 0.001))

        print(f"\n{'─' * 50}")
        print(f"  最高质量: {best['model']} ({best.get(score_key, 0):.1f}/{max_score})")
        print(f"  最低成本: {cheapest['model']} (¥{cheapest['cost_rmb']:.4f})")
        print(f"  最快速度: {fastest['model']} ({fastest['total_time']:.1f}s)")
        print(f"  最高性价比: {best_value['model']} "
              f"(分数{best_value.get(score_key, 0):.1f}/成本¥{best_value['cost_rmb']:.4f})")

    # 清理不可序列化的对象后保存
    for r in results:
        r.pop("summary_obj", None)

    output_path = Path("scripts/model_comparison_results.json")
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n详细结果已保存至: {output_path}")


if __name__ == "__main__":
    main()
