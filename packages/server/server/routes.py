"""API 路由定义。"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse

from .database import get_session
from .db_models import User, UserSetting
from .models import (
    PRESET_LIST,
    VOICE_LIST,
    PendingReview,
    PresetInfo,
    ReviewDecision,
    TaskConfig,
    TaskFromUrlRequest,
    TaskListResponse,
    TaskLogResponse,
    TaskResponse,
    UserCreate,
    UserResponse,
    UserSettingResponse,
    UserSettingUpdate,
    VoiceInfo,
)
from .task_manager import manager
from .voice_preview import get_or_generate_preview

router = APIRouter(prefix="/api")


# ------------------------------------------------------------------
# 预设
# ------------------------------------------------------------------


@router.get("/presets", response_model=list[PresetInfo])
async def get_presets():
    return PRESET_LIST


# ------------------------------------------------------------------
# 声音
# ------------------------------------------------------------------


@router.get("/voices", response_model=list[VoiceInfo])
async def list_voices(language: str | None = Query(None)):
    if language:
        return [v for v in VOICE_LIST if v.language == language]
    return VOICE_LIST


@router.get("/voices/{voice_id}/preview")
async def voice_preview(voice_id: str, rate: int = Query(0, ge=-50, le=100)):
    voice = next((v for v in VOICE_LIST if v.id == voice_id), None)
    if not voice:
        raise HTTPException(status_code=404, detail="声音不存在")

    try:
        path = await get_or_generate_preview(voice.id, voice.preview_text, rate=rate)
    except Exception:
        logger.exception("语音预览生成失败: voice_id=%s", voice_id)
        raise HTTPException(status_code=500, detail="生成预览失败") from None

    return FileResponse(path, media_type="audio/mpeg", filename=f"{voice_id}.mp3")


# ------------------------------------------------------------------
# 任务
# ------------------------------------------------------------------

MAX_PDF_SIZE = 100 * 1024 * 1024  # 100 MB


@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    file: UploadFile = File(...),
    config: str = Form("{}"),
    user_id: str = Form("default"),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="请上传 PDF 文件")

    try:
        cfg = TaskConfig(**json.loads(config))
    except Exception:
        cfg = TaskConfig()

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(pdf_bytes) > MAX_PDF_SIZE:
        size_mb = len(pdf_bytes) / 1024 / 1024
        raise HTTPException(status_code=400, detail=f"文件过大（{size_mb:.1f} MB），最大支持 100 MB")
    if not pdf_bytes[:5].startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="文件不是有效的 PDF 格式")

    return manager.create_task(file.filename, pdf_bytes, cfg, user_id=user_id or "default")


@router.post("/tasks/from-url", response_model=TaskResponse)
async def create_task_from_url(body: TaskFromUrlRequest):
    """从 URL 创建任务。支持 PDF 直链、微信公众号和知乎文章链接。"""
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="请提供链接（支持 PDF、微信公众号、知乎文章）")

    try:
        return await manager.create_task_from_url(url, body.config, user_id=body.user_id or "default")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except Exception:
        logger.exception("从 URL 创建任务失败: url=%s", url)
        raise HTTPException(status_code=500, detail="处理链接失败，请检查链接是否可访问") from None


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    user_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
):
    items, total = manager.list_tasks(user_id=user_id, page=page, size=size)
    return TaskListResponse(items=items, total=total, page=page, size=size)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    if not manager.delete_task(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"ok": True}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.stage in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="任务已结束，无法取消")
    if not manager.cancel_task(task_id):
        raise HTTPException(status_code=400, detail="取消失败")
    return {"ok": True}


@router.post("/tasks/{task_id}/retry", response_model=TaskResponse)
async def retry_task(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.stage not in ("failed", "completed"):
        raise HTTPException(status_code=400, detail="正在运行的任务请先取消再重试")
    result = manager.retry_task(task_id)
    if not result:
        raise HTTPException(status_code=500, detail="重试失败")
    return result


@router.get("/tasks/{task_id}/events")
async def task_events(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def generate():
        async for event in manager.event_stream(task_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/tasks/{task_id}/logs", response_model=list[TaskLogResponse])
async def get_task_logs(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    logs = manager.get_task_logs(task_id)
    return [TaskLogResponse(**l) for l in logs]


@router.get("/tasks/{task_id}/script")
async def get_task_script(task_id: str):
    data = manager.get_script_json(task_id)
    if data is None:
        raise HTTPException(status_code=404, detail="脚本尚未生成")
    return data


@router.get("/tasks/{task_id}/markdown")
async def get_task_markdown(task_id: str):
    p = manager.get_markdown_path(task_id)
    if not p:
        raise HTTPException(status_code=404, detail="Markdown 尚未生成")
    return PlainTextResponse(p.read_text(encoding="utf-8"))


@router.get("/tasks/{task_id}/summary")
async def get_task_summary(task_id: str):
    data = manager.get_summary_json(task_id)
    if data is None:
        raise HTTPException(status_code=404, detail="论文摘要尚未生成")
    return data


@router.get("/tasks/{task_id}/figures")
async def get_task_figures(task_id: str):
    img_dir = manager.get_figures_dir(task_id)
    if not img_dir:
        return []
    exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
    files = sorted(f.name for f in img_dir.iterdir() if f.suffix.lower() in exts)
    return files


@router.get("/tasks/{task_id}/figures/{filename:path}")
async def get_task_figure(task_id: str, filename: str):
    img_dir = manager.get_figures_dir(task_id)
    if not img_dir:
        raise HTTPException(status_code=404, detail="图片目录不存在")
    p = (img_dir / filename).resolve()
    if not p.is_relative_to(img_dir.resolve()):
        raise HTTPException(status_code=403, detail="禁止访问")
    if not p.exists() or not p.is_file():
        # 哈希不匹配时尝试前缀匹配（缓存的图片路径可能与新下载的不同）
        from pathlib import Path as _Path
        stem = _Path(filename).stem[:12]
        suffix = _Path(filename).suffix
        candidates = [f for f in img_dir.iterdir() if f.stem.startswith(stem) and f.suffix == suffix]
        if candidates:
            p = candidates[0]
        else:
            raise HTTPException(status_code=404, detail="图片不存在")
    ext = p.suffix.lower()
    media_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    return FileResponse(p, media_type=media_map.get(ext, "application/octet-stream"))


@router.get("/tasks/{task_id}/audio/{index}")
async def get_task_audio(task_id: str, index: int):
    p = manager.get_audio_path(task_id, index)
    if not p:
        raise HTTPException(status_code=404, detail="音频文件不存在")
    return FileResponse(p, media_type="audio/mpeg")


@router.get("/tasks/{task_id}/thumbnail")
async def get_thumbnail(task_id: str):
    p = manager.thumbnail_path(task_id)
    if not p:
        raise HTTPException(status_code=404, detail="缩略图不存在")
    return FileResponse(p, media_type="image/jpeg")


@router.get("/tasks/{task_id}/video")
async def download_video(task_id: str):
    path = manager.video_path(task_id)
    if not path:
        raise HTTPException(status_code=404, detail="视频不存在或任务未完成")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
    )


# ------------------------------------------------------------------
# 人工审核（Interactive Mode）
# ------------------------------------------------------------------


@router.get("/tasks/{task_id}/pending-review")
async def get_pending_review(task_id: str):
    """获取当前等待审核的中间产物（仅逐步模式）。"""
    review = manager.get_pending_review(task_id)
    if not review:
        raise HTTPException(status_code=404, detail="当前没有等待审核的内容")
    return PendingReview(
        step=review.get("step", ""),
        artifact_type=review.get("artifact_type", ""),
        data=review.get("data", {}),
        message=review.get("message", ""),
    )


@router.post("/tasks/{task_id}/approve")
async def approve_and_continue(task_id: str, body: ReviewDecision | None = None):
    """批准当前步骤结果（可附带编辑），继续下一步。"""
    decision = body.model_dump() if body else {"action": "approve"}
    ok = manager.approve_step(task_id, decision)
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在或未在等待审核状态")
    return {"status": "resumed", "task_id": task_id}


@router.put("/tasks/{task_id}/artifacts/{artifact_type}")
async def update_artifact(task_id: str, artifact_type: str, body: dict):
    """编辑指定类型的中间产物并继续执行。

    artifact_type: summary | script
    """
    decision = {"action": "edit", "data": body}
    ok = manager.approve_step(task_id, decision)
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在或未在等待审核状态")
    return {"status": "updated_and_resumed", "task_id": task_id, "artifact_type": artifact_type}


@router.post("/tasks/{task_id}/resume-from")
async def resume_from_step(task_id: str, step: str = Query(..., description="parse|extract|script|tts|render")):
    """从指定步骤开始重新执行（使用已有的中间产物）。

    适用于用户手动编辑了 summary/script 后只重跑后续步骤。
    """
    valid_steps = {"parse", "extract", "script", "tts", "render"}
    if step not in valid_steps:
        raise HTTPException(status_code=400, detail=f"无效步骤: {step}，有效值: {valid_steps}")
    resp = manager.resume_from_step(task_id, step)
    if not resp:
        raise HTTPException(status_code=404, detail="任务不存在或缺少必要的中间产物")
    return resp


@router.post("/tasks/{task_id}/reanalyze-figure")
async def reanalyze_figure(task_id: str, body: dict):
    """重新分析单张图片。

    body: {"figure_path": "images/xxx.jpg", "caption": "..."}
    """
    figure_path = body.get("figure_path")
    if not figure_path:
        raise HTTPException(status_code=400, detail="缺少 figure_path")
    try:
        result = manager.reanalyze_figure(task_id, figure_path, caption=body.get("caption", ""))
    except RuntimeError:
        logger.exception("图片重分析失败: task_id=%s, figure=%s", task_id, figure_path)
        raise HTTPException(status_code=502, detail="图片分析服务暂时不可用") from None
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在或图片文件未找到")
    return result


@router.post("/tasks/{task_id}/rotate-figure")
async def rotate_figure(task_id: str, body: dict):
    """旋转指定图片。

    body: {"figure_path": "images/xxx.jpg", "angle": 90}
    angle: 顺时针旋转角度，支持 90/180/270
    """
    figure_path = body.get("figure_path")
    angle = body.get("angle", 90)
    if not figure_path:
        raise HTTPException(status_code=400, detail="缺少 figure_path")
    if angle not in (90, 180, 270):
        raise HTTPException(status_code=400, detail="angle 必须为 90、180 或 270")
    result = manager.rotate_figure(task_id, figure_path, angle)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在或图片文件未找到")
    return result


@router.post("/tasks/{task_id}/rerun-figures")
async def rerun_figures(task_id: str):
    """重新分析该任务的所有图表。"""
    result = manager.rerun_figure_analysis(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="任务不存在或缺少必要数据")
    return result


@router.post("/tasks/{task_id}/update-summary")
async def update_summary(task_id: str, body: dict):
    """直接更新任务的 summary JSON（用于前端编辑评分等）。"""
    ok = manager.update_summary(task_id, body)
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"status": "updated", "task_id": task_id}


# ------------------------------------------------------------------
# 用户
# ------------------------------------------------------------------


@router.post("/users", response_model=UserResponse)
async def create_user(body: UserCreate):
    user_id = uuid.uuid4().hex[:12]
    user = User(id=user_id, name=body.name, email=body.email)
    with get_session() as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        return UserResponse(id=user.id, name=user.name, email=user.email, created_at=user.created_at)


@router.get("/users", response_model=list[UserResponse])
async def list_users():
    with get_session() as session:
        users = session.query(User).order_by(User.created_at).all()
        return [UserResponse(id=u.id, name=u.name, email=u.email, created_at=u.created_at) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return UserResponse(id=user.id, name=user.name, email=user.email, created_at=user.created_at)


@router.get("/users/{user_id}/settings", response_model=list[UserSettingResponse])
async def get_user_settings(user_id: str):
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        settings = session.query(UserSetting).filter_by(user_id=user_id).all()
        return [UserSettingResponse(key=s.key, value=s.value_json, updated_at=s.updated_at) for s in settings]


@router.put("/users/{user_id}/settings", response_model=UserSettingResponse)
async def update_user_setting(user_id: str, body: UserSettingUpdate):
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        value_str = body.value if isinstance(body.value, str) else json.dumps(body.value, ensure_ascii=False)
        existing = session.query(UserSetting).filter_by(user_id=user_id, key=body.key).first()
        if existing:
            existing.value_json = value_str
            session.commit()
            session.refresh(existing)
            return UserSettingResponse(key=existing.key, value=existing.value_json, updated_at=existing.updated_at)
        else:
            setting = UserSetting(user_id=user_id, key=body.key, value_json=value_str)
            session.add(setting)
            session.commit()
            session.refresh(setting)
            return UserSettingResponse(key=setting.key, value=setting.value_json, updated_at=setting.updated_at)
