"""请求/响应数据模型。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TaskStage(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    SCRIPTING = "scripting"
    TTS = "tts"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


STAGE_PROGRESS: dict[TaskStage, int] = {
    TaskStage.PENDING: 0,
    TaskStage.PARSING: 10,
    TaskStage.EXTRACTING: 30,
    TaskStage.SCRIPTING: 50,
    TaskStage.TTS: 70,
    TaskStage.RENDERING: 85,
    TaskStage.COMPLETED: 100,
    TaskStage.FAILED: -1,
}

STAGE_LABELS: dict[TaskStage, str] = {
    TaskStage.PENDING: "等待开始",
    TaskStage.PARSING: "内容解析中",
    TaskStage.EXTRACTING: "信息提取中",
    TaskStage.SCRIPTING: "脚本生成中",
    TaskStage.TTS: "语音合成中",
    TaskStage.RENDERING: "视频渲染中",
    TaskStage.COMPLETED: "已完成",
    TaskStage.FAILED: "失败",
}


# ------------------------------------------------------------------
# 任务
# ------------------------------------------------------------------


class TaskConfig(BaseModel):
    preset: str = "landscape"
    language: str = "zh"
    fps: int = 30
    skip_tts: bool = False
    voice: str | None = None
    extract_mode: str = "multi_pass"
    speech_rate: int = Field(default=0, ge=-50, le=100)
    narration_style: str = "default"
    theme: str = "academic"
    interactive_mode: bool = False


class ReviewDecision(BaseModel):
    """人工审核决策。"""

    action: str = Field(description="approve | edit | retry")
    data: dict | None = Field(default=None, description="编辑后的数据（action=edit 时必填）")


class PendingReview(BaseModel):
    """等待审核的中间产物。"""

    step: str = Field(description="当前步骤: extract | script | tts")
    artifact_type: str = Field(description="产物类型: paper_summary | video_script | audio")
    data: dict = Field(description="当前产物数据")
    message: str = Field(default="")


class TaskFromUrlRequest(BaseModel):
    url: str
    config: TaskConfig = TaskConfig()
    user_id: str = "default"


class VoiceInfo(BaseModel):
    id: str
    name: str
    language: str
    gender: str
    preview_text: str


_ZH_PREVIEW = "你好，欢迎使用 Theia 论文视频生成工具。"
_EN_PREVIEW = "Hello, welcome to Theia, the paper-to-video tool."
_JA_PREVIEW = "こんにちは、Theiaへようこそ。論文からビデオを自動生成するツールです。"

VOICE_LIST: list[VoiceInfo] = [
    # 中文
    VoiceInfo(id="zh-CN-XiaoxiaoNeural", name="晓晓", language="zh", gender="female", preview_text=_ZH_PREVIEW),
    VoiceInfo(id="zh-CN-XiaoyiNeural", name="晓伊", language="zh", gender="female", preview_text=_ZH_PREVIEW),
    VoiceInfo(id="zh-CN-YunxiNeural", name="云希", language="zh", gender="male", preview_text=_ZH_PREVIEW),
    VoiceInfo(id="zh-CN-YunjianNeural", name="云健", language="zh", gender="male", preview_text=_ZH_PREVIEW),
    VoiceInfo(id="zh-CN-YunyangNeural", name="云扬", language="zh", gender="male", preview_text=_ZH_PREVIEW),
    VoiceInfo(id="zh-CN-YunxiaNeural", name="云夏（少年）", language="zh", gender="male", preview_text=_ZH_PREVIEW),
    VoiceInfo(
        id="zh-CN-liaoning-XiaobeiNeural", name="晓北（东北）", language="zh", gender="female", preview_text=_ZH_PREVIEW
    ),
    VoiceInfo(
        id="zh-CN-shaanxi-XiaoniNeural", name="晓妮（陕西）", language="zh", gender="female", preview_text=_ZH_PREVIEW
    ),
    # 日语
    VoiceInfo(id="ja-JP-NanamiNeural", name="七海（ななみ）", language="ja", gender="female", preview_text=_JA_PREVIEW),
    VoiceInfo(id="ja-JP-KeitaNeural", name="慶太（けいた）", language="ja", gender="male", preview_text=_JA_PREVIEW),
    # 英文
    VoiceInfo(id="en-US-JennyNeural", name="Jenny", language="en", gender="female", preview_text=_EN_PREVIEW),
    VoiceInfo(id="en-US-GuyNeural", name="Guy", language="en", gender="male", preview_text=_EN_PREVIEW),
    VoiceInfo(id="en-US-AriaNeural", name="Aria", language="en", gender="female", preview_text=_EN_PREVIEW),
    VoiceInfo(id="en-US-AndrewNeural", name="Andrew", language="en", gender="male", preview_text=_EN_PREVIEW),
    VoiceInfo(id="en-US-AvaNeural", name="Ava", language="en", gender="female", preview_text=_EN_PREVIEW),
    VoiceInfo(id="en-US-BrianNeural", name="Brian", language="en", gender="male", preview_text=_EN_PREVIEW),
    VoiceInfo(id="en-US-EmmaNeural", name="Emma", language="en", gender="female", preview_text=_EN_PREVIEW),
    VoiceInfo(id="en-US-EricNeural", name="Eric", language="en", gender="male", preview_text=_EN_PREVIEW),
    VoiceInfo(id="en-US-AnaNeural", name="Ana（童声）", language="en", gender="female", preview_text=_EN_PREVIEW),
    VoiceInfo(id="en-US-ChristopherNeural", name="Christopher", language="en", gender="male", preview_text=_EN_PREVIEW),
    VoiceInfo(id="en-US-MichelleNeural", name="Michelle", language="en", gender="female", preview_text=_EN_PREVIEW),
    VoiceInfo(id="en-US-RogerNeural", name="Roger", language="en", gender="male", preview_text=_EN_PREVIEW),
]


class TaskResponse(BaseModel):
    id: str
    filename: str
    stage: TaskStage
    progress: int = 0
    stage_label: str = ""
    video_path: str | None = None
    thumbnail_path: str | None = None
    error: str | None = None
    paper_title: str | None = None
    user_id: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    size: int


class TaskEvent(BaseModel):
    """SSE 推送的单条事件。"""

    stage: TaskStage
    progress: int
    stage_label: str
    message: str = ""
    video_path: str | None = None
    error: str | None = None
    token_delta: str | None = None
    token_step: str | None = None


class TaskLogResponse(BaseModel):
    stage: str
    progress: int
    message: str
    created_at: str


# ------------------------------------------------------------------
# 用户
# ------------------------------------------------------------------


class UserCreate(BaseModel):
    name: str
    email: str | None = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str | None = None
    created_at: datetime


class UserSettingUpdate(BaseModel):
    key: str
    value: str | dict | list


class UserSettingResponse(BaseModel):
    key: str
    value: str
    updated_at: datetime


# ------------------------------------------------------------------
# 预设
# ------------------------------------------------------------------


class PresetInfo(BaseModel):
    key: str
    label: str
    width: int
    height: int


PRESET_LIST: list[PresetInfo] = [
    PresetInfo(key="landscape", label="横屏 16:9（B站/YouTube）", width=1920, height=1080),
    PresetInfo(key="bilibili", label="B站 16:9", width=1920, height=1080),
    PresetInfo(key="portrait", label="竖屏 9:16（抖音）", width=1080, height=1920),
    PresetInfo(key="douyin", label="抖音 9:16", width=1080, height=1920),
    PresetInfo(key="xiaohongshu", label="小红书 3:4", width=1080, height=1440),
    PresetInfo(key="square", label="正方形 1:1", width=1080, height=1080),
]
