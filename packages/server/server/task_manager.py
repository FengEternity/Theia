"""任务调度与进度捕获。

任务状态持久化到 SQLite，SSE 实时推送保留内存 Queue。
每个任务在独立线程中运行 run_pipeline，通过自定义 logging handler
拦截管道日志来更新进度。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import threading
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from .database import get_session
from .db_models import Task as TaskRow
from .db_models import TaskLog
from .models import (
    STAGE_LABELS,
    STAGE_PROGRESS,
    TaskConfig,
    TaskEvent,
    TaskResponse,
    TaskStage,
)

logger = logging.getLogger(__name__)

_DEFAULT_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent / "workspace"

_NAME_TO_STAGE: dict[str, TaskStage] = {
    "parse": TaskStage.PARSING,
    "extract": TaskStage.EXTRACTING,
    "script": TaskStage.SCRIPTING,
    "tts": TaskStage.TTS,
    "render": TaskStage.RENDERING,
}


def _row_to_response(row: TaskRow) -> TaskResponse:
    return TaskResponse(
        id=row.id,
        filename=row.filename,
        stage=TaskStage(row.stage),
        progress=row.progress,
        stage_label=row.stage_label,
        video_path=row.video_path,
        thumbnail_path=row.thumbnail_path,
        error=row.error,
        created_at=row.created_at,
        updated_at=row.updated_at,
        paper_title=row.paper_title,
        user_id=row.user_id,
    )


class _LiveTask:
    """运行中任务的内存状态（SSE Queue + 锁）。"""

    def __init__(self, task_id: str) -> None:
        self.id = task_id
        self.queues: list[asyncio.Queue[TaskEvent | None]] = []
        self.lock = threading.Lock()

    def push_event(
        self,
        stage: TaskStage,
        progress: int,
        stage_label: str,
        message: str = "",
        video_path: str | None = None,
        error: str | None = None,
    ) -> None:
        event = TaskEvent(
            stage=stage,
            progress=progress,
            stage_label=stage_label,
            message=message,
            video_path=video_path,
            error=error,
        )
        for q in self.queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def close_streams(self) -> None:
        for q in self.queues:
            q.put_nowait(None)


class _CancelledError(Exception):
    """任务被用户取消。"""


class _TaskProgressCallback:
    """实现 ProgressCallback 协议，将流水线进度更新到 DB + SSE。

    替代原来基于日志正则解析的 _PipelineLogHandler，
    通过结构化回调实现 agent ↔ server 解耦。
    """

    def __init__(self, mgr: TaskManager, task_id: str, cancel_event: threading.Event) -> None:
        self.mgr = mgr
        self.task_id = task_id
        self.cancel_event = cancel_event

    def on_step(self, info) -> None:
        if self.cancel_event.is_set():
            raise _CancelledError("任务已被用户取消")

        stage = _NAME_TO_STAGE.get(info.name)
        if stage and info.status == "started":
            self.mgr._update_stage(self.task_id, stage, info.message)

    def on_token(self, step_name: str, token: str) -> None:
        """LLM 流式 token 回调 — 将 token 片段推送到 SSE 客户端。"""
        live = self.mgr._live.get(self.task_id)
        if not live:
            return
        stage = _NAME_TO_STAGE.get(step_name, TaskStage.EXTRACTING)
        event = TaskEvent(
            stage=stage,
            progress=STAGE_PROGRESS.get(stage, 0),
            stage_label=STAGE_LABELS.get(stage, ""),
            token_delta=token,
            token_step=step_name,
        )
        for q in live.queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


_RUNNING_STAGES = {
    TaskStage.PARSING,
    TaskStage.EXTRACTING,
    TaskStage.SCRIPTING,
    TaskStage.TTS,
    TaskStage.RENDERING,
}


class TaskManager:
    """全局任务管理器，线程安全。DB 持久化 + 内存 SSE Queue。"""

    def __init__(self, workspace: Path | None = None) -> None:
        self._workspace = workspace or Path(os.getenv("THEIA_WORKSPACE", str(_DEFAULT_WORKSPACE)))
        self._live: dict[str, _LiveTask] = {}
        self._lock = threading.Lock()
        self._cancel_events: dict[str, threading.Event] = {}
        self._interactive_state: dict[str, dict] = {}
        self._recover_stuck_tasks()

    def _recover_stuck_tasks(self) -> None:
        """服务启动时将卡在运行状态的任务标记为失败（可重试）。"""
        try:
            with get_session() as session:
                stuck = session.query(TaskRow).filter(TaskRow.stage.in_([s.value for s in _RUNNING_STAGES])).all()
                for row in stuck:
                    logger.warning(
                        "恢复卡住的任务 %s (stage=%s) -> failed",
                        row.id,
                        row.stage,
                    )
                    row.stage = TaskStage.FAILED.value
                    row.stage_label = "服务重启中断，请重试"
                    row.error = f"任务在 {row.stage_label} 阶段被服务重启中断"
                    row.updated_at = datetime.now(UTC)
                session.commit()
                if stuck:
                    logger.info("已恢复 %d 个卡住的任务", len(stuck))
        except Exception as exc:
            logger.warning("恢复卡住任务失败: %s", exc)

    def _workspace_for(self, task_id: str) -> Path:
        return self._workspace / "tasks" / task_id

    def _get_or_create_live(self, task_id: str) -> _LiveTask:
        with self._lock:
            if task_id not in self._live:
                self._live[task_id] = _LiveTask(task_id)
            return self._live[task_id]

    def _remove_live(self, task_id: str) -> None:
        with self._lock:
            self._live.pop(task_id, None)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_task(
        self, filename: str, pdf_bytes: bytes, config: TaskConfig, user_id: str | None = None
    ) -> TaskResponse:
        task_id = uuid.uuid4().hex[:12]

        ws = self._workspace_for(task_id)
        ws.mkdir(parents=True, exist_ok=True)
        pdf_dest = ws / "input" / filename
        pdf_dest.parent.mkdir(parents=True, exist_ok=True)
        pdf_dest.write_bytes(pdf_bytes)

        now = datetime.now(UTC)
        row = TaskRow(
            id=task_id,
            user_id=user_id or "default",
            filename=filename,
            stage=TaskStage.PENDING.value,
            progress=0,
            stage_label=STAGE_LABELS[TaskStage.PENDING],
            config_json=config.model_dump_json(),
            created_at=now,
            updated_at=now,
        )
        with get_session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            resp = _row_to_response(row)

        live = self._get_or_create_live(task_id)
        cancel_event = threading.Event()
        self._cancel_events[task_id] = cancel_event
        t = threading.Thread(target=self._run, args=(task_id, live, config, pdf_dest, ws, cancel_event), daemon=True)
        t.start()

        return resp

    async def create_task_from_url(self, url: str, config: TaskConfig, user_id: str | None = None) -> TaskResponse:
        """从 URL 创建任务。自动检测是 PDF 链接还是文章链接。"""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("仅支持 http/https 链接")

        from theia.parsing.web import is_article_url

        if is_article_url(url):
            return self._create_task_from_article(url, config, user_id=user_id)

        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Theia/1.0)"})
            resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        pdf_bytes = resp.content

        if len(pdf_bytes) < 100:
            raise ValueError("下载内容为空或过小，请检查链接是否正确")
        if not pdf_bytes[:5].startswith(b"%PDF"):
            if "application/pdf" not in content_type:
                raise ValueError("链接返回的内容不是有效的 PDF 文件")

        path_part = unquote(parsed.path)
        filename = path_part.rsplit("/", 1)[-1] if "/" in path_part else "download.pdf"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        return self.create_task(filename, pdf_bytes, config, user_id=user_id)

    def _create_task_from_article(self, url: str, config: TaskConfig, user_id: str | None = None) -> TaskResponse:
        """从微信公众号或知乎文章 URL 创建任务。

        将 URL 存储为标记文件（``input/article_url.txt``），
        流水线的 ``parse_node`` 会自动检测并使用 ``web_parser``。
        """
        from theia.parsing.web import article_stem

        task_id = uuid.uuid4().hex[:12]
        stem = article_stem(url)
        filename = f"{stem}.article"

        ws = self._workspace_for(task_id)
        ws.mkdir(parents=True, exist_ok=True)
        url_file = ws / "input" / "article_url.txt"
        url_file.parent.mkdir(parents=True, exist_ok=True)
        url_file.write_text(url, encoding="utf-8")

        now = datetime.now(UTC)
        row = TaskRow(
            id=task_id,
            user_id=user_id or "default",
            filename=filename,
            stage=TaskStage.PENDING.value,
            progress=0,
            stage_label=STAGE_LABELS[TaskStage.PENDING],
            config_json=config.model_dump_json(),
            created_at=now,
            updated_at=now,
        )
        with get_session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            resp = _row_to_response(row)

        live = self._get_or_create_live(task_id)
        cancel_event = threading.Event()
        self._cancel_events[task_id] = cancel_event

        t = threading.Thread(
            target=self._run_article,
            args=(task_id, live, config, url, ws, cancel_event),
            daemon=True,
        )
        t.start()

        return resp

    def _run_article(
        self,
        task_id: str,
        live: _LiveTask,
        config: TaskConfig,
        article_url: str,
        ws: Path,
        cancel_event: threading.Event,
    ) -> None:
        """执行文章任务：将文章 URL 直接传递给流水线。"""
        progress_cb = _TaskProgressCallback(self, task_id, cancel_event)
        interactive = getattr(config, "interactive_mode", False)

        try:
            self._update_stage(task_id, TaskStage.PARSING, "开始处理文章")

            if interactive:
                self._run_interactive_article(task_id, config, article_url, ws, cancel_event, progress_cb)
            else:
                self._run_batch_article(task_id, config, article_url, ws, cancel_event, progress_cb)
        except _CancelledError:
            self._set_failed(task_id, "任务已被用户取消")
        except Exception as exc:
            logger.exception("文章任务 %s 执行失败", task_id)
            self._set_failed(task_id, str(exc))
        finally:
            self._cancel_events.pop(task_id, None)

    def _run_batch_article(
        self,
        task_id: str,
        config: TaskConfig,
        article_url: str,
        ws: Path,
        cancel_event: threading.Event,
        progress_cb: _TaskProgressCallback,
    ) -> None:
        from theia.pipeline import run_pipeline

        result = run_pipeline(
            article_url,
            workspace=str(ws),
            language=config.language,
            tts_voice=config.voice,
            fps=config.fps,
            video_preset=config.preset,
            skip_tts=config.skip_tts,
            speech_rate=config.speech_rate,
            narration_style=config.narration_style,
            theme=config.theme,
            progress=progress_cb,
        )

        if cancel_event.is_set():
            self._set_failed(task_id, "任务已被用户取消")
            return

        video = result.get("output_video")
        if video and Path(video).exists():
            self._set_completed(task_id, video, result)
        else:
            self._set_failed(task_id, "管道完成但未生成视频文件")

    def _run_interactive_article(
        self,
        task_id: str,
        config: TaskConfig,
        article_url: str,
        ws: Path,
        cancel_event: threading.Event,
        progress_cb: _TaskProgressCallback,
    ) -> None:
        from theia.llm.config import LLMConfig
        from theia.pipeline import build_graph, register_progress_callback, unregister_progress_callback
        from theia.schemas import PipelineInput

        default_cfg = LLMConfig()
        pipeline_input = PipelineInput(
            pdf_path=article_url,
            workspace=str(ws),
            language=config.language,
            tts_voice=config.voice,
            fps=config.fps,
            video_preset=config.preset,
            skip_tts=config.skip_tts,
            speech_rate=config.speech_rate,
            narration_style=config.narration_style,
            theme=config.theme,
            interactive_mode=True,
            extract_model=default_cfg.extract_model,
            scan_model=default_cfg.scan_model,
            script_model=default_cfg.script_model,
            figure_model=default_cfg.figure_model,
            extract_api_key=default_cfg.extract_api_key,
            extract_api_base=default_cfg.extract_api_base,
            script_api_key=default_cfg.script_api_key,
            script_api_base=default_cfg.script_api_base,
        )

        graph = build_graph(interactive=True)
        thread_config = {"configurable": {"thread_id": task_id}}
        initial_state = {**pipeline_input.model_dump()}

        ws_str = initial_state.get("workspace", "")
        if ws_str:
            register_progress_callback(ws_str, progress_cb)

        try:
            result = graph.invoke(initial_state, config=thread_config)
        except Exception:
            if ws_str:
                unregister_progress_callback(ws_str)
            raise

        if cancel_event.is_set():
            if ws_str:
                unregister_progress_callback(ws_str)
            self._set_failed(task_id, "任务已被用户取消")
            return

        snapshot = graph.get_state(thread_config)
        if snapshot.next:
            interrupt_values = [v.value for v in (snapshot.tasks[0].interrupts if snapshot.tasks else [])]
            interrupt_data = interrupt_values[0] if interrupt_values else {"step": "unknown", "message": "等待审核"}
            self._interactive_state[task_id] = {
                **(interrupt_data if isinstance(interrupt_data, dict) else {}),
                "_graph": graph,
                "_config": thread_config,
            }
            step_name = interrupt_data.get("step", "") if isinstance(interrupt_data, dict) else ""
            stage = _NAME_TO_STAGE.get(step_name, TaskStage.EXTRACTING)
            self._update_stage(task_id, stage, f"等待审核: {step_name}")
            return

        if ws_str:
            unregister_progress_callback(ws_str)

        video = result.get("output_video") if isinstance(result, dict) else None
        if video and Path(video).exists():
            self._set_completed(task_id, video, result)
        else:
            self._set_failed(task_id, "管道完成但未生成视频文件")

    def get_task(self, task_id: str) -> TaskResponse | None:
        with get_session() as session:
            row = session.get(TaskRow, task_id)
            return _row_to_response(row) if row else None

    def list_tasks(self, user_id: str | None = None, page: int = 1, size: int = 50) -> tuple[list[TaskResponse], int]:
        with get_session() as session:
            q = session.query(TaskRow)
            if user_id:
                q = q.filter(TaskRow.user_id == user_id)
            total = q.count()
            rows = q.order_by(TaskRow.created_at.desc()).offset((page - 1) * size).limit(size).all()
            return [_row_to_response(r) for r in rows], total

    def delete_task(self, task_id: str) -> bool:
        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if not row:
                return False
            session.delete(row)
            session.commit()
        self._remove_live(task_id)
        ws = self._workspace_for(task_id)
        if ws.exists():
            shutil.rmtree(ws, ignore_errors=True)
        return True

    def cancel_task(self, task_id: str) -> bool:
        cancel_event = self._cancel_events.get(task_id)
        if cancel_event:
            cancel_event.set()
            return True
        task_resp = self.get_task(task_id)
        if task_resp and task_resp.stage not in (TaskStage.COMPLETED, TaskStage.FAILED):
            self._set_failed(task_id, "任务已被用户取消")
            return True
        return False

    def get_pending_review(self, task_id: str) -> dict | None:
        """获取当前等待审核的中间产物（仅逐步模式）。

        当 _interactive_state 为空（如服务重启后）但任务仍处于审核标记，
        尝试从磁盘产物重建审核数据。
        """
        state = self._interactive_state.get(task_id)
        if state:
            return state

        task_resp = self.get_task(task_id)
        if not task_resp or "等待审核" not in (task_resp.stage_label or ""):
            return None

        step = "extract"
        if "script" in task_resp.stage_label:
            step = "script"
        elif "tts" in task_resp.stage_label:
            step = "tts"

        artifact_type = "summary" if step == "extract" else step
        data: dict = {}
        if step == "extract":
            summary = self.get_summary_json(task_id)
            if summary:
                data = summary if isinstance(summary, dict) else {}
        elif step == "script":
            script = self.get_script_json(task_id)
            if script:
                data = script if isinstance(script, dict) else {}

        return {
            "step": step,
            "artifact_type": artifact_type,
            "data": data,
            "message": f"步骤 {step} 已完成，请审核结果（注：LangGraph 状态已丢失，仅支持查看和重新执行）",
        }

    def approve_step(self, task_id: str, decision: dict) -> bool:
        """批准/编辑当前步骤，恢复流水线执行。

        参数:
            decision: {"action": "approve"} 或 {"action": "edit", "data": {...}}
        """
        state = self._interactive_state.pop(task_id, None)
        if not state:
            return False

        graph = state.get("_graph")
        config = state.get("_config")
        if not graph or not config:
            return False

        step = state.get("step", "")
        if decision.get("action") == "approve" and step == "extract":
            latest = self.get_summary_json(task_id)
            if latest:
                decision = {"action": "edit", "data": latest}
                logger.info("自动合并用户对 summary 的编辑")

        from langgraph.types import Command

        live = self._get_or_create_live(task_id)
        cancel_event = self._cancel_events.get(task_id, threading.Event())

        def _resume():
            try:
                result = graph.invoke(Command(resume=decision), config=config)

                if cancel_event.is_set():
                    self._set_failed(task_id, "任务已被用户取消")
                    return

                interrupts = result.get("__interrupt__") if isinstance(result, dict) else None
                if interrupts:
                    interrupt_data = interrupts[0].value if interrupts else {}
                    self._interactive_state[task_id] = {
                        **interrupt_data,
                        "_graph": graph,
                        "_config": config,
                    }
                    step_name = interrupt_data.get("step", "") if isinstance(interrupt_data, dict) else ""
                    stage = _NAME_TO_STAGE.get(step_name, TaskStage.EXTRACTING)
                    self._update_stage(task_id, stage, f"等待审核: {step_name}")
                    return

                video = result.get("output_video") if isinstance(result, dict) else None
                if video and Path(video).exists():
                    self._set_completed(task_id, video, result)
                else:
                    self._set_failed(task_id, "管道完成但未生成视频文件")
            except _CancelledError:
                self._set_failed(task_id, "任务已被用户取消")
            except Exception as exc:
                logger.exception("任务 %s 恢复执行失败", task_id)
                self._set_failed(task_id, str(exc))

        t = threading.Thread(target=_resume, daemon=True)
        t.start()
        return True

    def resume_from_step(self, task_id: str, step: str) -> TaskResponse | None:
        """从指定步骤开始重新执行，使用已有的中间产物。

        自动检测任务是否为交互模式 — 如果是，重跑后仍会在各步骤暂停等待审核。
        """
        task_resp = self.get_task(task_id)
        if not task_resp:
            return None

        ws = self._workspace_for(task_id)
        existing_state = self._collect_existing_state(task_id, ws)
        if not existing_state:
            return None

        config = self._load_task_config(task_id)
        interactive = config.get("interactive_mode", False)

        now = datetime.now(UTC)
        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if row:
                step_stage = _NAME_TO_STAGE.get(step, TaskStage.PARSING)
                row.stage = step_stage.value
                row.progress = STAGE_PROGRESS.get(step_stage, 0)
                row.stage_label = STAGE_LABELS.get(step_stage, "")
                row.error = None
                row.updated_at = now
                session.commit()
                session.refresh(row)
                resp = _row_to_response(row)

        self._interactive_state.pop(task_id, None)

        live = self._get_or_create_live(task_id)
        cancel_event = threading.Event()
        self._cancel_events[task_id] = cancel_event
        progress_cb = _TaskProgressCallback(self, task_id, cancel_event)

        if interactive:

            def _run_from_interactive():
                try:
                    from theia.pipeline import (
                        build_partial_graph,
                        register_progress_callback,
                        unregister_progress_callback,
                    )

                    graph = build_partial_graph(step, interactive=True)
                    thread_config = {"configurable": {"thread_id": task_id}}

                    state = dict(existing_state)
                    state["workspace"] = str(ws)
                    state["interactive_mode"] = True

                    ws_str = state["workspace"]
                    register_progress_callback(ws_str, progress_cb)

                    try:
                        result = graph.invoke(state, config=thread_config)
                    except Exception:
                        unregister_progress_callback(ws_str)
                        raise

                    if cancel_event.is_set():
                        unregister_progress_callback(ws_str)
                        self._set_failed(task_id, "任务已被用户取消")
                        return

                    snapshot = graph.get_state(thread_config)
                    if snapshot.next:
                        interrupt_values = [v.value for v in (snapshot.tasks[0].interrupts if snapshot.tasks else [])]
                        interrupt_data = (
                            interrupt_values[0] if interrupt_values else {"step": "unknown", "message": "等待审核"}
                        )
                        self._interactive_state[task_id] = {
                            **(interrupt_data if isinstance(interrupt_data, dict) else {}),
                            "_graph": graph,
                            "_config": thread_config,
                        }
                        step_name = interrupt_data.get("step", "") if isinstance(interrupt_data, dict) else ""
                        stage = _NAME_TO_STAGE.get(step_name, TaskStage.EXTRACTING)
                        self._update_stage(task_id, stage, f"等待审核: {step_name}")
                        logger.info("任务 %s 在 %s 步骤暂停，等待人工审核", task_id, step_name)
                        return

                    unregister_progress_callback(ws_str)
                    video = result.get("output_video") if isinstance(result, dict) else None
                    if video and Path(video).exists():
                        self._set_completed(task_id, video, result)
                    else:
                        self._set_failed(task_id, "管道完成但未生成视频文件")
                except _CancelledError:
                    self._set_failed(task_id, "任务已被用户取消")
                except Exception as exc:
                    logger.exception("任务 %s 从 %s 步骤交互重跑失败", task_id, step)
                    self._set_failed(task_id, str(exc))
                finally:
                    self._cancel_events.pop(task_id, None)

            t = threading.Thread(target=_run_from_interactive, daemon=True)
            t.start()
        else:

            def _run_from():
                try:
                    from theia.pipeline import run_pipeline_from

                    result = run_pipeline_from(
                        step,
                        ws,
                        existing_state=existing_state,
                        progress=progress_cb,
                    )

                    if cancel_event.is_set():
                        self._set_failed(task_id, "任务已被用户取消")
                        return

                    video = result.get("output_video")
                    if video and Path(video).exists():
                        self._set_completed(task_id, video, result)
                    else:
                        self._set_failed(task_id, "管道完成但未生成视频文件")
                except _CancelledError:
                    self._set_failed(task_id, "任务已被用户取消")
                except Exception as exc:
                    logger.exception("任务 %s 从 %s 步骤重跑失败", task_id, step)
                    self._set_failed(task_id, str(exc))
                finally:
                    self._cancel_events.pop(task_id, None)

            t = threading.Thread(target=_run_from, daemon=True)
            t.start()

        return resp

    def _collect_existing_state(self, task_id: str, ws: Path) -> dict | None:
        """从已有文件中收集流水线中间产物状态。"""

        input_dir = ws / "input"
        pdf_path = None
        article_url = None

        if input_dir.exists():
            url_file = input_dir / "article_url.txt"
            if url_file.exists():
                article_url = url_file.read_text(encoding="utf-8").strip()
            else:
                for f in input_dir.iterdir():
                    if f.suffix.lower() == ".pdf":
                        pdf_path = f
                        break

        if not pdf_path and not article_url:
            return None

        if article_url:
            from theia.parsing.web import article_stem

            stem = article_stem(article_url)
            state: dict = {
                "pdf_path": article_url,
                "workspace": str(ws),
            }
        else:
            stem = pdf_path.stem
            state = {
                "pdf_path": str(pdf_path),
                "workspace": str(ws),
            }

        md_path = ws / "parsed" / f"{stem}.md"
        if md_path.exists():
            state["markdown_content"] = md_path.read_text(encoding="utf-8")

        parsed_dir = ws / "parsed"
        if parsed_dir.exists():
            state["parsed_dir"] = str(parsed_dir)

        summary_path = ws / "scripts" / f"{stem}_summary.json"
        if summary_path.exists():
            state["paper_summary_json"] = summary_path.read_text(encoding="utf-8")

        script_path = ws / "scripts" / f"{stem}_script.json"
        if script_path.exists():
            import json

            state["video_script_json"] = json.dumps(
                json.loads(script_path.read_text(encoding="utf-8")),
                ensure_ascii=False,
            )

        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if row and row.config_json:
                try:
                    config = json.loads(row.config_json)
                    state.setdefault("language", config.get("language", "zh"))
                    state.setdefault("video_preset", config.get("preset", "landscape"))
                    state.setdefault("theme", config.get("theme", "academic"))
                    state.setdefault("narration_style", config.get("narration_style", "default"))
                    state.setdefault("fps", config.get("fps", 30))
                    state.setdefault("speech_rate", config.get("speech_rate", 0))
                except json.JSONDecodeError:
                    pass

        return state

    # ------------------------------------------------------------------
    # 部分重新执行 (图表分析 / 单图分析 / 摘要更新)
    # ------------------------------------------------------------------

    def rotate_figure(self, task_id: str, figure_path: str, angle: int) -> dict | None:
        """顺时针旋转指定图片并覆盖保存。"""
        images_dir = self._find_images_dir(task_id)
        if not images_dir:
            return None

        name = Path(figure_path).name
        candidates = [images_dir / name, images_dir / figure_path]
        img_path = next((p for p in candidates if p.is_file()), None)
        if not img_path:
            return None

        try:
            from PIL import Image

            with Image.open(img_path) as img:
                rotated = img.rotate(-angle, expand=True)
                if rotated.mode in ("RGBA", "P") and img_path.suffix.lower() in (".jpg", ".jpeg"):
                    rotated = rotated.convert("RGB")
                rotated.save(img_path)
            logger.info("图片已旋转 %d°: %s", angle, img_path)
            return {"ok": True, "figure_path": figure_path, "angle": angle}
        except Exception as exc:
            logger.warning("图片旋转失败 %s: %s", figure_path, exc)
            return None

    def _find_images_dir(self, task_id: str) -> Path | None:
        """递归查找 parsed 目录下的 images 子目录。"""
        ws = self._workspace_for(task_id)
        parsed_base = ws / "parsed"
        if not parsed_base.exists():
            return None
        for sub in parsed_base.rglob("images"):
            if sub.is_dir():
                return sub
        return None

    def reanalyze_figure(self, task_id: str, figure_path: str, *, caption: str = "") -> dict | None:
        """重新分析单张图片并更新 summary 中对应的 Figure。"""
        images_dir = self._find_images_dir(task_id)
        if not images_dir:
            return None

        summary_json = self.get_summary_json(task_id)
        if not summary_json or not isinstance(summary_json, dict):
            return None

        core_idea = summary_json.get("core_idea", "")

        from theia.extraction.figure_analyzer import reanalyze_single_figure
        from theia.llm.config import LLMConfig

        llm_cfg = LLMConfig()
        try:
            new_fig = reanalyze_single_figure(
                figure_path,
                images_dir,
                core_idea,
                caption=caption,
                model=llm_cfg.figure_model,
                api_key=llm_cfg.figure_api_key,
                api_base=llm_cfg.figure_api_base,
            )
        except FileNotFoundError as exc:
            logger.warning("单图重新分析失败 %s: %s", figure_path, exc)
            return None
        except Exception as exc:
            logger.warning("单图重新分析失败 %s: %s", figure_path, exc)
            msg = str(exc)
            if "429" in msg or "RateLimit" in msg:
                raise RuntimeError("模型接口频率限制，请稍后重试") from exc
            raise RuntimeError(f"图片分析失败: {msg[:200]}") from exc

        figures = summary_json.get("figures", [])
        updated = False
        for i, fig in enumerate(figures):
            fig_name = Path(fig.get("path", "")).name
            target_name = Path(figure_path).name
            if fig_name == target_name:
                figures[i] = new_fig.model_dump()
                updated = True
                break
        if not updated:
            figures.append(new_fig.model_dump())

        summary_json["figures"] = figures
        self._save_summary(task_id, summary_json)
        return new_fig.model_dump()

    def rerun_figure_analysis(self, task_id: str) -> dict | None:
        """重新分析任务中所有图片。"""
        images_dir = self._find_images_dir(task_id)
        if not images_dir:
            return None

        summary_json = self.get_summary_json(task_id)
        if not summary_json or not isinstance(summary_json, dict):
            return None

        ws = self._workspace_for(task_id)
        md_path = self.get_markdown_path(task_id)
        if not md_path or not md_path.exists():
            return None

        markdown_content = md_path.read_text(encoding="utf-8")
        core_idea = summary_json.get("core_idea", "")

        from theia._utils import extract_figures_from_markdown
        from theia.extraction.figure_analyzer import analyze_figures
        from theia.llm.config import LLMConfig
        from theia.schemas import PaperOverview

        raw_figures = extract_figures_from_markdown(markdown_content)
        if not raw_figures:
            return {"figures": [], "count": 0}

        overview = PaperOverview(
            paper_type=summary_json.get("paper_type", ""),
            core_idea=core_idea,
            key_contributions=summary_json.get("contributions", []),
            reading_focus=[],
        )

        llm_cfg = LLMConfig()
        analyzed = analyze_figures(
            raw_figures,
            images_dir,
            overview,
            model=llm_cfg.figure_model,
            api_key=llm_cfg.figure_api_key,
            api_base=llm_cfg.figure_api_base,
        )

        summary_json["figures"] = [f.model_dump() for f in analyzed]
        self._save_summary(task_id, summary_json)
        return {"figures": summary_json["figures"], "count": len(analyzed)}

    def update_summary(self, task_id: str, data: dict) -> bool:
        """直接更新任务的 summary JSON（如前端修改评分后保存）。"""
        return self._save_summary(task_id, data)

    def _save_summary(self, task_id: str, data: dict) -> bool:
        """将 summary JSON 写入磁盘和数据库。"""
        stem = self._pdf_stem(task_id)
        if not stem:
            return False
        ws = self._workspace_for(task_id)

        summary_path = ws / "scripts" / f"{stem}_summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if row:
                row.paper_summary_json = json.dumps(data, ensure_ascii=False)
                session.commit()
        return True

    def _load_task_config(self, task_id: str) -> dict:
        """从数据库加载任务配置。"""
        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if row and row.config_json:
                try:
                    return json.loads(row.config_json)
                except json.JSONDecodeError:
                    pass
        return {}

    def retry_task(self, task_id: str) -> TaskResponse | None:
        """重试任务：重置状态并重新执行管道。支持失败和已完成的任务。"""
        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if not row:
                return None
            if row.stage not in (TaskStage.FAILED.value, TaskStage.COMPLETED.value):
                return None

            config = TaskConfig()
            if row.config_json:
                try:
                    config = TaskConfig(**json.loads(row.config_json))
                except Exception:
                    pass

            row.stage = TaskStage.PENDING.value
            row.progress = 0
            row.stage_label = STAGE_LABELS[TaskStage.PENDING]
            row.error = None
            row.video_path = None
            row.thumbnail_path = None
            row.video_script_json = None
            row.updated_at = datetime.now(UTC)
            session.commit()
            session.refresh(row)
            resp = _row_to_response(row)

        ws = self._workspace_for(task_id)
        input_dir = ws / "input"
        pdf_path = None
        article_url = None

        if input_dir.exists():
            url_file = input_dir / "article_url.txt"
            if url_file.exists():
                article_url = url_file.read_text(encoding="utf-8").strip()
            else:
                for f in input_dir.iterdir():
                    if f.suffix.lower() == ".pdf":
                        pdf_path = f
                        break

        if not pdf_path and not article_url:
            self._set_failed(task_id, "原始输入不存在，无法重试")
            return self.get_task(task_id)

        for subdir in ("scripts", "audio", "output"):
            d = ws / subdir
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)

        live = self._get_or_create_live(task_id)
        cancel_event = threading.Event()
        self._cancel_events[task_id] = cancel_event

        if article_url:
            t = threading.Thread(
                target=self._run_article,
                args=(task_id, live, config, article_url, ws, cancel_event),
                daemon=True,
            )
        else:
            t = threading.Thread(
                target=self._run,
                args=(task_id, live, config, pdf_path, ws, cancel_event),
                daemon=True,
            )
        t.start()

        return resp

    def get_task_logs(self, task_id: str) -> list[dict]:
        with get_session() as session:
            logs = session.query(TaskLog).filter_by(task_id=task_id).order_by(TaskLog.created_at).all()
            return [
                {"stage": l.stage, "progress": l.progress, "message": l.message, "created_at": l.created_at.isoformat()}
                for l in logs
            ]

    def video_path(self, task_id: str) -> Path | None:
        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if not row or not row.video_path:
                return None
            p = Path(row.video_path)
            return p if p.exists() else None

    def thumbnail_path(self, task_id: str) -> Path | None:
        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if not row or not row.thumbnail_path:
                return None
            p = Path(row.thumbnail_path)
            return p if p.exists() else None

    def _pdf_stem(self, task_id: str) -> str | None:
        ws = self._workspace_for(task_id)
        input_dir = ws / "input"
        if not input_dir.exists():
            return None

        url_file = input_dir / "article_url.txt"
        if url_file.exists():
            from theia.parsing.web import article_stem

            url = url_file.read_text(encoding="utf-8").strip()
            return article_stem(url) if url else None

        for f in input_dir.iterdir():
            if f.suffix.lower() == ".pdf":
                return f.stem
        return None

    def get_markdown_path(self, task_id: str) -> Path | None:
        stem = self._pdf_stem(task_id)
        if not stem:
            return None
        p = self._workspace_for(task_id) / "parsed" / f"{stem}.md"
        return p if p.exists() else None

    def get_figures_dir(self, task_id: str) -> Path | None:
        stem = self._pdf_stem(task_id)
        if not stem:
            return None
        parsed = self._workspace_for(task_id) / "parsed" / stem
        if not parsed.exists():
            return None
        for sub in parsed.iterdir():
            if sub.is_dir():
                img_dir = sub / "images"
                if img_dir.exists():
                    return img_dir
        return None

    def get_audio_path(self, task_id: str, index: int) -> Path | None:
        p = self._workspace_for(task_id) / "audio" / f"scene_{index}.mp3"
        return p if p.exists() else None

    def get_script_json(self, task_id: str) -> dict | None:
        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if row and row.video_script_json:
                try:
                    return json.loads(row.video_script_json)
                except json.JSONDecodeError:
                    pass

        stem = self._pdf_stem(task_id)
        if stem:
            p = self._workspace_for(task_id) / "scripts" / f"{stem}_script.json"
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
        return None

    def get_summary_json(self, task_id: str) -> dict | None:
        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if row and row.paper_summary_json:
                try:
                    return json.loads(row.paper_summary_json)
                except json.JSONDecodeError:
                    pass

        stem = self._pdf_stem(task_id)
        if stem:
            p = self._workspace_for(task_id) / "scripts" / f"{stem}_summary.json"
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
        return None

    # ------------------------------------------------------------------
    # SSE
    # ------------------------------------------------------------------

    def subscribe(self, task_id: str) -> asyncio.Queue[TaskEvent | None] | None:
        task_resp = self.get_task(task_id)
        if not task_resp:
            return None
        live = self._get_or_create_live(task_id)
        q: asyncio.Queue[TaskEvent | None] = asyncio.Queue(maxsize=64)
        with live.lock:
            live.queues.append(q)
            current = TaskEvent(
                stage=task_resp.stage,
                progress=task_resp.progress,
                stage_label=task_resp.stage_label,
                video_path=task_resp.video_path,
                error=task_resp.error,
            )
            q.put_nowait(current)
        return q

    def unsubscribe(self, task_id: str, q: asyncio.Queue) -> None:
        live = self._live.get(task_id)
        if live:
            with live.lock:
                try:
                    live.queues.remove(q)
                except ValueError:
                    pass

    async def event_stream(self, task_id: str) -> AsyncGenerator[TaskEvent, None]:
        q = self.subscribe(task_id)
        if q is None:
            return
        try:
            while True:
                event = await q.get()
                if event is None:
                    break
                yield event
        finally:
            self.unsubscribe(task_id, q)

    # ------------------------------------------------------------------
    # 状态更新（DB + SSE + Log）
    # ------------------------------------------------------------------

    def _update_stage(self, task_id: str, stage: TaskStage, message: str = "") -> None:
        now = datetime.now(UTC)
        progress = STAGE_PROGRESS.get(stage, 0)
        label = message if "等待审核" in message else STAGE_LABELS.get(stage, "")

        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if row:
                row.stage = stage.value
                row.progress = progress
                row.stage_label = label
                row.updated_at = now
                session.add(
                    TaskLog(task_id=task_id, stage=stage.value, progress=progress, message=message, created_at=now)
                )
                session.commit()

        live = self._live.get(task_id)
        if live:
            live.push_event(stage, progress, label, message)

    @staticmethod
    def _generate_thumbnail(video_path: str, task_id: str) -> str | None:
        """Extract first frame from video as a JPEG thumbnail."""
        try:
            thumb = Path(video_path).parent / f"{task_id}_thumb.jpg"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-vframes",
                    "1",
                    "-q:v",
                    "2",
                    "-vf",
                    "scale=480:-1",
                    str(thumb),
                ],
                capture_output=True,
                timeout=15,
            )
            if thumb.exists() and thumb.stat().st_size > 0:
                return str(thumb)
        except Exception as exc:
            logger.warning("缩略图生成失败: %s", exc)
        return None

    def _set_completed(self, task_id: str, video_path: str, result: dict | None = None) -> None:
        now = datetime.now(UTC)
        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if row:
                row.stage = TaskStage.COMPLETED.value
                row.progress = 100
                row.stage_label = STAGE_LABELS[TaskStage.COMPLETED]
                row.video_path = video_path
                row.thumbnail_path = self._generate_thumbnail(video_path, task_id)
                row.updated_at = now
                row.completed_at = now
                if result:
                    summary = result.get("paper_summary_json")
                    if summary:
                        row.paper_summary_json = summary
                        try:
                            row.paper_title = json.loads(summary).get("title")
                        except Exception:
                            pass
                    script = result.get("video_script_json")
                    if script:
                        row.video_script_json = script
                session.add(
                    TaskLog(task_id=task_id, stage="completed", progress=100, message="视频生成完成", created_at=now)
                )
                session.commit()

        live = self._live.get(task_id)
        if live:
            live.push_event(
                TaskStage.COMPLETED, 100, STAGE_LABELS[TaskStage.COMPLETED], "视频生成完成", video_path=video_path
            )
            live.close_streams()
        self._remove_live(task_id)

    def _set_failed(self, task_id: str, error: str) -> None:
        now = datetime.now(UTC)
        with get_session() as session:
            row = session.get(TaskRow, task_id)
            if row:
                last_progress = max(row.progress, 0)
                row.stage = TaskStage.FAILED.value
                row.progress = last_progress
                row.stage_label = STAGE_LABELS[TaskStage.FAILED]
                row.error = error
                row.updated_at = now
                session.add(
                    TaskLog(task_id=task_id, stage="failed", progress=last_progress, message=error, created_at=now)
                )
                session.commit()

        live = self._live.get(task_id)
        if live:
            live.push_event(TaskStage.FAILED, -1, STAGE_LABELS[TaskStage.FAILED], error, error=error)
            live.close_streams()
        self._remove_live(task_id)

    # ------------------------------------------------------------------
    # 管道执行
    # ------------------------------------------------------------------

    def _run(
        self, task_id: str, live: _LiveTask, config: TaskConfig, pdf_path: Path, ws: Path, cancel_event: threading.Event
    ) -> None:
        progress_cb = _TaskProgressCallback(self, task_id, cancel_event)
        interactive = getattr(config, "interactive_mode", False)

        try:
            logger.info(
                "任务 %s 配置: theme=%s, narration_style=%s, language=%s, preset=%s, interactive=%s",
                task_id,
                config.theme,
                config.narration_style,
                config.language,
                config.preset,
                interactive,
            )
            self._update_stage(task_id, TaskStage.PARSING, "开始处理")

            if interactive:
                self._run_interactive(task_id, config, pdf_path, ws, cancel_event, progress_cb)
            else:
                self._run_batch(task_id, config, pdf_path, ws, cancel_event, progress_cb)
        except _CancelledError:
            self._set_failed(task_id, "任务已被用户取消")
        except Exception as exc:
            logger.exception("任务 %s 执行失败", task_id)
            self._set_failed(task_id, str(exc))
        finally:
            self._cancel_events.pop(task_id, None)

    def _run_batch(
        self,
        task_id: str,
        config: TaskConfig,
        pdf_path: Path,
        ws: Path,
        cancel_event: threading.Event,
        progress_cb: _TaskProgressCallback,
    ) -> None:
        """非交互批量执行模式。"""
        from theia.pipeline import run_pipeline

        result = run_pipeline(
            str(pdf_path),
            workspace=str(ws),
            language=config.language,
            tts_voice=config.voice,
            fps=config.fps,
            video_preset=config.preset,
            skip_tts=config.skip_tts,
            speech_rate=config.speech_rate,
            narration_style=config.narration_style,
            theme=config.theme,
            progress=progress_cb,
        )

        if cancel_event.is_set():
            self._set_failed(task_id, "任务已被用户取消")
            return

        video = result.get("output_video")
        if video and Path(video).exists():
            self._set_completed(task_id, video, result)
        else:
            self._set_failed(task_id, "管道完成但未生成视频文件")

    def _run_interactive(
        self,
        task_id: str,
        config: TaskConfig,
        pdf_path: Path,
        ws: Path,
        cancel_event: threading.Event,
        progress_cb: _TaskProgressCallback,
    ) -> None:
        """交互执行模式：遇到 interrupt 时暂停，等待用户审核。"""
        from theia.llm.config import LLMConfig
        from theia.pipeline import build_graph
        from theia.schemas import PipelineInput

        default_cfg = LLMConfig()
        resolved_pdf = str(pdf_path)
        resolved_ws = str(ws)

        pipeline_input = PipelineInput(
            pdf_path=resolved_pdf,
            workspace=resolved_ws,
            language=config.language,
            tts_voice=config.voice,
            fps=config.fps,
            video_preset=config.preset,
            skip_tts=config.skip_tts,
            speech_rate=config.speech_rate,
            narration_style=config.narration_style,
            theme=config.theme,
            interactive_mode=True,
            extract_model=default_cfg.extract_model,
            scan_model=default_cfg.scan_model,
            script_model=default_cfg.script_model,
            figure_model=default_cfg.figure_model,
            extract_api_key=default_cfg.extract_api_key,
            extract_api_base=default_cfg.extract_api_base,
            script_api_key=default_cfg.script_api_key,
            script_api_base=default_cfg.script_api_base,
        )

        graph = build_graph(interactive=True)
        thread_config = {"configurable": {"thread_id": task_id}}

        initial_state = {
            **pipeline_input.model_dump(),
        }

        from theia.pipeline import register_progress_callback, unregister_progress_callback

        ws_str = initial_state.get("workspace", "")
        if ws_str:
            register_progress_callback(ws_str, progress_cb)

        try:
            result = graph.invoke(initial_state, config=thread_config)
        except Exception:
            if ws_str:
                unregister_progress_callback(ws_str)
            raise

        if cancel_event.is_set():
            if ws_str:
                unregister_progress_callback(ws_str)
            self._set_failed(task_id, "任务已被用户取消")
            return

        # 检查是否在 interrupt 处暂停（保留回调以便恢复时继续推送进度）
        snapshot = graph.get_state(thread_config)
        if snapshot.next:
            interrupt_values = [v.value for v in (snapshot.tasks[0].interrupts if snapshot.tasks else [])]
            interrupt_data = interrupt_values[0] if interrupt_values else {"step": "unknown", "message": "等待审核"}
            self._interactive_state[task_id] = {
                **(interrupt_data if isinstance(interrupt_data, dict) else {}),
                "_graph": graph,
                "_config": thread_config,
            }
            step_name = interrupt_data.get("step", "") if isinstance(interrupt_data, dict) else ""
            stage = _NAME_TO_STAGE.get(step_name, TaskStage.EXTRACTING)
            self._update_stage(task_id, stage, f"等待审核: {step_name}")
            logger.info("任务 %s 在 %s 步骤暂停，等待人工审核", task_id, step_name)
            return

        if ws_str:
            unregister_progress_callback(ws_str)

        video = result.get("output_video") if isinstance(result, dict) else None
        if video and Path(video).exists():
            self._set_completed(task_id, video, result)
        else:
            self._set_failed(task_id, "管道完成但未生成视频文件")


manager = TaskManager()
