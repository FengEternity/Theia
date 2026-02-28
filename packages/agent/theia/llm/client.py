"""统一的 LLM 调用层。

提供带参数降级、API 故障转移和推理模型兼容的 LLM 调用接口。
所有模块（extractor、scriptwriter、evaluator、figure_analyzer）共享此层，
避免重复实现。
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time as _time
from typing import Callable

import litellm

litellm.drop_params = True

logger = logging.getLogger(__name__)

_FALLBACK_MODEL = "deepseek-ai/DeepSeek-R1"
_FALLBACK_VLM_MODEL = "Qwen/Qwen3-VL-32B-Instruct"


def _estimate_input_chars(messages: list) -> int:
    """估算消息列表中的总文本字符数（含多模态消息的文本部分）。"""
    total = 0
    for m in messages:
        if not isinstance(m, dict):
            continue
        content = m.get("content", "")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += len(part.get("text", ""))
    return total


def _has_image_content(messages: list) -> bool:
    """检查消息是否包含图片内容。"""
    for m in messages:
        if not isinstance(m, dict):
            continue
        content = m.get("content", "")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return True
    return False

# ---------------------------------------------------------------------------
# 全局速率限制器 — 控制所有线程的 LLM 并发与请求间隔
# ---------------------------------------------------------------------------

_MAX_CONCURRENT = int(os.getenv("THEIA_LLM_MAX_CONCURRENT", "3"))
_MIN_INTERVAL = float(os.getenv("THEIA_LLM_MIN_INTERVAL", "0.5"))

_semaphore = threading.Semaphore(_MAX_CONCURRENT)
_last_call_lock = threading.Lock()
_last_call_time: float = 0.0


def _throttle() -> None:
    """在发起 API 调用前执行限流：控制并发数 + 请求最小间隔。"""
    global _last_call_time
    _semaphore.acquire()
    try:
        with _last_call_lock:
            now = _time.monotonic()
            wait = _MIN_INTERVAL - (now - _last_call_time)
            if wait > 0:
                _time.sleep(wait)
            _last_call_time = _time.monotonic()
    except Exception:
        _semaphore.release()
        raise


def _throttle_release() -> None:
    _semaphore.release()


def robust_completion(
    kwargs: dict,
    *,
    max_retries: int = 3,
    on_token: Callable[[str], None] | None = None,
):
    """调用 LLM completion，带参数降级、API 故障转移和自适应恢复。

    调用策略：
    1. ``openai/`` 前缀模型优先走直连（绕过 litellm 大小写问题）
    2. 推理模型遇到 400 时自动移除 temperature / response_format 重试
    3. 主 API 不可用（503/超时等）时降级到备选 API
    4. RecoveryStrategy 自适应重试（频率限制退避、输入截断等）

    参数:
        on_token: 流式回调。提供时启用 ``stream=True``，每收到一个
                  token 片段就调用 ``on_token(text)``。函数仍返回完整
                  的 ``ModelResponse``。
    """
    _ensure_direct_openai_kwargs(kwargs)
    _normalize_model_params(kwargs)

    model_tag = kwargs.get("model", "unknown")
    api_base_tag = kwargs.get("api_base", "default")
    input_chars = _estimate_input_chars(kwargs.get("messages", []))
    max_tok = kwargs.get("max_tokens") or kwargs.get("max_completion_tokens", "?")
    has_images = _has_image_content(kwargs.get("messages", []))
    img_label = " [含图片]" if has_images else ""
    logger.info(
        "LLM 请求: model=%s, api_base=%s, input_chars=%d%s, max_tokens=%s",
        model_tag, api_base_tag, input_chars, img_label, max_tok,
    )

    removable = ["temperature", "response_format"]
    attempt = 0
    t0 = _time.monotonic()
    while True:
        _throttle()
        try:
            if on_token is not None:
                result = _streaming_dispatch(kwargs, on_token)
            elif kwargs.get("api_base"):
                result = _direct_openai_completion(kwargs)
            else:
                result = litellm.completion(**kwargs)
            _throttle_release()
            elapsed = _time.monotonic() - t0
            _log_response(result, model_tag, elapsed)
            return result
        except Exception as exc:
            _throttle_release()
            elapsed = _time.monotonic() - t0
            logger.warning(
                "LLM 调用失败: model=%s, elapsed=%.1fs, attempt=%d, error=%s: %s",
                model_tag, elapsed, attempt + 1, type(exc).__name__, str(exc)[:200],
            )
            msg = str(exc).lower()
            removed_any = False

            if "max_tokens" in msg and "max_tokens" in kwargs:
                val = kwargs.pop("max_tokens")
                kwargs["max_completion_tokens"] = val
                logger.debug("转换 max_tokens → max_completion_tokens=%d", val)
                continue

            for param in list(removable):
                if param in msg and param in kwargs:
                    logger.debug("移除不支持的参数 '%s' 后重试", param)
                    kwargs.pop(param)
                    removable.remove(param)
                    removed_any = True
            if removed_any:
                continue

            fallback = _try_fallback(kwargs, exc)
            if fallback is not None:
                return fallback

            strategy = RecoveryStrategy.classify(exc)
            if strategy != RecoveryStrategy.ABORT and attempt < max_retries:
                logger.info("恢复策略: %s (第 %d 次重试)", strategy, attempt + 1)
                kwargs = RecoveryStrategy.execute(strategy, kwargs, exc, attempt)
                attempt += 1
                continue

            raise


def _log_response(response, model_tag: str, elapsed: float) -> None:
    """记录 LLM 响应的 token 用量和耗时。"""
    usage = getattr(response, "usage", None)
    if usage:
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        total_tokens = getattr(usage, "total_tokens", 0) or (prompt_tokens + completion_tokens)
        cache_hit = getattr(usage, "prompt_tokens_details", None)
        cache_info = ""
        if cache_hit and hasattr(cache_hit, "cached_tokens"):
            cached = getattr(cache_hit, "cached_tokens", 0) or 0
            if cached > 0:
                cache_info = f", cached={cached}"
        logger.info(
            "LLM 响应: model=%s, elapsed=%.1fs, input=%d, output=%d, total=%d%s",
            model_tag, elapsed, prompt_tokens, completion_tokens, total_tokens, cache_info,
        )
    else:
        content = ""
        if hasattr(response, "choices") and response.choices:
            content = getattr(response.choices[0].message, "content", "") or ""
        logger.info(
            "LLM 响应: model=%s, elapsed=%.1fs, output_chars=%d (无 usage 信息)",
            model_tag, elapsed, len(content),
        )


def extract_json_from_response(response) -> str:
    """从 LLM 响应中提取 JSON。

    推理模型（DeepSeek-R1 等）的 content 可能被 reasoning_content
    占用，最终 JSON 在 content 字段中。此函数兼容普通模型和推理模型。
    """
    msg = response.choices[0].message
    content = getattr(msg, "content", None) or ""
    content = strip_json_fences(content.strip())

    if content and content.lstrip().startswith("{"):
        return content

    reasoning = getattr(msg, "reasoning_content", None) or ""
    if reasoning:
        json_blocks = re.findall(r"\{[\s\S]*\}", reasoning)
        if json_blocks:
            return strip_json_fences(json_blocks[-1])

    return content


def strip_json_fences(text: str) -> str:
    """去除 Markdown 代码围栏（```json ... ```）。"""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.index("\n") if "\n" in text else 3
        text = text[first_newline + 1 :]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# ---------------------------------------------------------------------------
# 自适应错误恢复策略
# ---------------------------------------------------------------------------


class RecoveryStrategy:
    """根据错误类型自动分类并执行恢复策略。"""

    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    REDUCE_INPUT = "reduce_input"
    FALLBACK_MODEL = "fallback_model"
    SKIP = "skip"
    ABORT = "abort"

    @staticmethod
    def classify(exc: Exception) -> str:
        msg = str(exc).lower()

        if any(kw in msg for kw in ("rate limit", "429", "ratelimit", "quota")):
            return RecoveryStrategy.RETRY_WITH_BACKOFF
        if any(kw in msg for kw in ("context_length", "too large", "tokens_limit", "413", "maximum context")):
            return RecoveryStrategy.REDUCE_INPUT
        if any(kw in msg for kw in ("timeout", "timed out", "connection")):
            return RecoveryStrategy.RETRY
        if any(kw in msg for kw in ("500", "502", "503", "internal server")):
            return RecoveryStrategy.FALLBACK_MODEL
        if any(kw in msg for kw in ("invalid", "format", "400")):
            return RecoveryStrategy.RETRY

        return RecoveryStrategy.ABORT

    @staticmethod
    def execute(strategy: str, kwargs: dict, exc: Exception, attempt: int) -> dict:
        """执行恢复策略，返回修改后的 kwargs。

        Raises:
            原始异常 — 当策略为 abort 或不可恢复时
        """
        import time

        if strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            delay = min(2**attempt, 60)
            logger.info("频率限制，等待 %ds 后重试 (第 %d 次)", delay, attempt + 1)
            time.sleep(delay)
            return kwargs

        if strategy == RecoveryStrategy.REDUCE_INPUT:
            messages = kwargs.get("messages", [])
            reduced = False
            for msg in messages:
                content = msg.get("content")
                if isinstance(content, str) and len(content) > 10000:
                    msg["content"] = content[: len(content) // 2] + "\n\n[... 已截断 ...]"
                    reduced = True
            if reduced:
                logger.warning("输入过长，已截断后重试 (第 %d 次)", attempt + 1)
                return kwargs
            raise exc

        if strategy == RecoveryStrategy.FALLBACK_MODEL:
            return kwargs

        if strategy == RecoveryStrategy.RETRY:
            delay = min(2**attempt, 30)
            logger.info("网络错误，等待 %ds 后重试 (第 %d 次)", delay, attempt + 1)
            time.sleep(delay)
            return kwargs

        raise exc


# ---------------------------------------------------------------------------
# 内部实现
# ---------------------------------------------------------------------------


def _streaming_dispatch(kwargs: dict, on_token: Callable[[str], None]):
    """以流式模式调用 LLM，逐 token 触发回调，最终返回完整 ModelResponse。"""
    if kwargs.get("api_base"):
        return _direct_openai_streaming(kwargs, on_token)
    return _litellm_streaming(kwargs, on_token)


def _collect_stream(stream, on_token: Callable[[str], None]) -> tuple[str, dict | None]:
    """遍历流式迭代器，收集完整内容并触发回调。返回 (content, usage_dict)。"""
    collected: list[str] = []
    usage_dict: dict | None = None
    for chunk in stream:
        usage = getattr(chunk, "usage", None)
        if usage:
            usage_dict = {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
                "total_tokens": getattr(usage, "total_tokens", 0) or 0,
            }
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = choices[0].delta
        text = getattr(delta, "content", None) or ""
        if text:
            collected.append(text)
            try:
                on_token(text)
            except Exception:
                pass
    return "".join(collected), usage_dict


def _litellm_streaming(kwargs: dict, on_token: Callable[[str], None]):
    """通过 litellm 进行流式调用。"""
    stream_kwargs = dict(kwargs, stream=True, stream_options={"include_usage": True})
    stream = litellm.completion(**stream_kwargs)
    content, usage = _collect_stream(stream, on_token)
    return _build_response_from_content(content, kwargs.get("model", ""), usage)


def _direct_openai_streaming(kwargs: dict, on_token: Callable[[str], None]):
    """通过 openai 直连进行流式调用。"""
    from openai import OpenAI

    call_kwargs = {k: v for k, v in kwargs.items() if k not in ("api_base", "api_key", "model")}
    api_base = kwargs["api_base"]
    api_key = kwargs.get("api_key")
    model = kwargs["model"]

    if model.startswith("openai/"):
        model = model[len("openai/"):]

    extra_headers: dict[str, str] = {}
    if "cognitiveservices.azure.com" in api_base or "azure.com" in api_base:
        extra_headers["api-key"] = api_key or ""

    client = OpenAI(
        api_key=api_key,
        base_url=api_base,
        max_retries=1,
        timeout=120,
        default_headers=extra_headers or None,
    )
    stream = client.chat.completions.create(
        model=model, stream=True, stream_options={"include_usage": True}, **call_kwargs,
    )
    content, usage = _collect_stream(stream, on_token)
    return _build_response_from_content(content, model, usage)


def _build_response_from_content(content: str, model: str, usage: dict | None = None):
    """从收集到的完整文本构造 ModelResponse。"""
    resp_kwargs: dict = {
        "choices": [
            litellm.Choices(
                message=litellm.Message(content=content, role="assistant"),
                index=0,
                finish_reason="stop",
            )
        ],
        "model": model,
    }
    if usage:
        resp_kwargs["usage"] = litellm.Usage(**usage)
    return litellm.ModelResponse(**resp_kwargs)


def _direct_openai_completion(kwargs: dict):
    """直接使用 openai 库调用自定义 API 端点，绕过 litellm 的模型名处理。

    自动检测 Azure 端点并使用 ``api-key`` 头认证。
    """
    from openai import OpenAI

    call_kwargs = {k: v for k, v in kwargs.items() if k not in ("api_base", "api_key", "model")}
    api_base = kwargs["api_base"]
    api_key = kwargs.get("api_key")
    model = kwargs["model"]

    if model.startswith("openai/"):
        model = model[len("openai/") :]

    extra_headers: dict[str, str] = {}
    if "cognitiveservices.azure.com" in api_base or "azure.com" in api_base:
        extra_headers["api-key"] = api_key or ""

    client = OpenAI(
        api_key=api_key,
        base_url=api_base,
        max_retries=1,
        timeout=120,
        default_headers=extra_headers or None,
    )
    response = client.chat.completions.create(model=model, **call_kwargs)

    return litellm.ModelResponse(**response.model_dump())


def _normalize_model_params(kwargs: dict) -> None:
    """根据模型名称主动调整不兼容的参数。

    - gpt-5.x / o3 / o4 系列: max_completion_tokens 而非 max_tokens
    - kimi-k2.5: 不支持自定义 temperature（仅允许 1）
    """
    model = kwargs.get("model", "")
    model_lower = model.lower().replace("openai/", "")
    needs_completion_tokens = any(model_lower.startswith(p) for p in ("gpt-5", "o3", "o4", "gpt-audio"))
    if needs_completion_tokens and "max_tokens" in kwargs:
        kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")

    if model_lower == "kimi-k2.5" and "temperature" in kwargs:
        kwargs.pop("temperature")
        logger.debug("kimi-k2.5 不支持自定义 temperature，已移除")


def _ensure_direct_openai_kwargs(kwargs: dict) -> None:
    """为非 litellm 原生模型补全 api_base / api_key，确保走直连路径。

    litellm 不认识 kimi-* 等模型名，会抛出 Provider NOT provided 错误。
    此函数检测此类模型并自动从环境变量补全 api_base / api_key。
    """
    model = kwargs.get("model", "")
    if kwargs.get("api_base"):
        return
    needs_direct = model.startswith("openai/") or model.startswith("kimi-")
    if not needs_direct:
        return
    env_base = os.getenv("THEIA_API_BASE") or os.getenv("THEIA_EXTRACT_API_BASE")
    if env_base:
        kwargs["api_base"] = env_base
        if not kwargs.get("api_key"):
            kwargs.setdefault("api_key", os.getenv("THEIA_API_KEY") or os.getenv("THEIA_EXTRACT_API_KEY"))


def _try_fallback(kwargs: dict, original_exc: Exception) -> object | None:
    """主 API 失败后尝试降级到备选 API。

    主 API (Azure) 失败 → 降级到 SiliconFlow；
    主 API (SiliconFlow) 失败 → 降级到 Azure。
    仅对服务端错误（5xx / 超时）触发，客户端错误（4xx）不降级。
    """
    from openai import APIStatusError

    is_server_error = False
    if (
        (isinstance(original_exc, APIStatusError) and original_exc.status_code >= 500)
        or "timeout" in str(original_exc).lower()
        or "timed out" in str(original_exc).lower()
        or (hasattr(original_exc, "status_code") and getattr(original_exc, "status_code", 0) >= 500)
    ):
        is_server_error = True

    if not is_server_error:
        return None

    current_base = kwargs.get("api_base", "") or ""
    is_azure = "azure.com" in current_base

    if is_azure:
        fallback_base = os.getenv("SILICONFLOW_API_BASE")
        fallback_key = os.getenv("SILICONFLOW_API_KEY")
        fallback_label = "SiliconFlow"
        fb_model = _FALLBACK_MODEL
        fb_vlm = _FALLBACK_VLM_MODEL
    else:
        fallback_base = os.getenv("OPENAI_API_BASE")
        fallback_key = os.getenv("OPENAI_API_KEY")
        fallback_label = "Azure OpenAI"
        fb_model = "DeepSeek-R1"
        fb_vlm = "Llama-3.2-90B-Vision-Instruct"

    if not fallback_base or not fallback_key:
        return None

    if kwargs.get("api_base") == fallback_base:
        return None

    has_images = any(
        isinstance(m.get("content"), list)
        and any(c.get("type") == "image_url" for c in m["content"] if isinstance(c, dict))
        for m in kwargs.get("messages", [])
        if isinstance(m, dict)
    )
    chosen_model = fb_vlm if has_images else fb_model

    logger.warning(
        "主 API 不可用 (%s)，降级到 %s (model=%s)",
        type(original_exc).__name__,
        fallback_label,
        chosen_model,
    )

    fallback_kwargs = dict(kwargs)
    fallback_kwargs["model"] = chosen_model
    fallback_kwargs["api_base"] = fallback_base
    fallback_kwargs["api_key"] = fallback_key

    try:
        return _direct_openai_completion(fallback_kwargs)
    except Exception as fallback_exc:
        logger.error("%s 降级也失败: %s", fallback_label, fallback_exc)
        return None
