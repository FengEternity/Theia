# Theia Server

FastAPI 后端，提供 REST API + SSE 实时进度推送，管理任务的完整生命周期。

## 安装与启动

```bash
cd packages/server
uv pip install -e .
uv run uvicorn server.main:app --reload --port 8000
```

依赖 `theia` agent 包（通过 editable path 引用 `../agent`）。

## 任务生命周期

TaskManager（`task_manager.py`）管理任务的完整生命周期：

```
创建 → 排队 → 运行中 → [暂停/审核] → 完成
                ↓              ↓
              失败 ←─── 取消
              ↓
            重试
```

- **创建** — 上传 PDF 或提交 URL，生成任务 ID 和工作空间
- **执行** — 后台线程运行 agent 流水线，通过 `ProgressCallback` 推送进度
- **SSE 推送** — 前端通过 `/api/tasks/{id}/events` 订阅实时进度
- **交互审核** — 交互模式下，流水线在每步完成后暂停等待用户审批
- **产物编辑** — 用户可编辑 PaperSummary、VideoScript 等中间产物
- **恢复执行** — 从指定步骤重新运行（编辑后）
- **取消/重试** — 随时取消运行中任务，失败任务可重试
- **启动恢复** — 服务重启时自动将卡住的任务标记为失败

## 数据库

SQLite（`workspace/theia.db`），通过 SQLAlchemy ORM 管理，支持自动迁移（`database.py`）。

| 表 | 说明 |
|----|------|
| `tasks` | 任务记录（阶段、进度、配置 JSON、产物路径、结构化数据） |
| `task_logs` | 任务日志（分阶段的进度消息） |
| `users` | 用户 |
| `user_settings` | 用户设置（KV 存储） |

## API 端点

### 任务管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks` | 上传 PDF + 配置，创建任务 |
| POST | `/api/tasks/from-url` | 从 URL 创建任务 |
| GET | `/api/tasks` | 分页获取任务列表 |
| GET | `/api/tasks/{id}` | 获取任务详情 |
| DELETE | `/api/tasks/{id}` | 删除任务及其产物 |
| POST | `/api/tasks/{id}/cancel` | 取消任务 |
| POST | `/api/tasks/{id}/retry` | 重试失败任务 |

### 实时进度与日志

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks/{id}/events` | SSE 实时进度流 |
| GET | `/api/tasks/{id}/logs` | 获取任务历史日志 |

### 产物访问

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks/{id}/video` | 下载最终视频 |
| GET | `/api/tasks/{id}/thumbnail` | 视频缩略图 |
| GET | `/api/tasks/{id}/script` | 视频脚本 JSON |
| GET | `/api/tasks/{id}/summary` | 论文摘要 JSON |
| GET | `/api/tasks/{id}/markdown` | 解析后的 Markdown |
| GET | `/api/tasks/{id}/figures` | 图片列表 |
| GET | `/api/tasks/{id}/figures/{filename}` | 单张图片文件 |
| GET | `/api/tasks/{id}/audio/{index}` | 场景音频文件 |

### 交互式审核

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks/{id}/pending-review` | 获取待审核内容 |
| POST | `/api/tasks/{id}/approve` | 审批通过当前步骤 |
| PUT | `/api/tasks/{id}/artifacts/{type}` | 编辑中间产物（summary/script） |
| POST | `/api/tasks/{id}/resume-from` | 从指定步骤恢复执行 |
| POST | `/api/tasks/{id}/reanalyze-figure` | 重新分析指定图片 |
| POST | `/api/tasks/{id}/rotate-figure` | 旋转图片 |
| POST | `/api/tasks/{id}/rerun-figures` | 重跑全部图片分析 |
| POST | `/api/tasks/{id}/update-summary` | 更新论文摘要 |

### 配置与用户

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/presets` | 视频预设列表 |
| GET | `/api/voices` | TTS 语音列表 |
| GET | `/api/voices/{id}/preview` | 语音预览音频 |
| POST | `/api/users` | 创建用户 |
| GET | `/api/users` | 用户列表 |
| GET | `/api/users/{id}` | 用户详情 |
| GET | `/api/users/{id}/settings` | 用户设置 |
| PUT | `/api/users/{id}/settings` | 更新用户设置 |

## 模块说明

```
server/
├── main.py            # FastAPI 应用入口、CORS 配置、数据库初始化
├── routes.py          # 所有 API 路由定义
├── task_manager.py    # 任务调度、生命周期管理、SSE 进度推送
├── models.py          # Pydantic 请求/响应模型、预设/语音列表
├── db_models.py       # SQLAlchemy ORM 模型定义
├── database.py        # SQLite 引擎、会话管理、自动迁移
└── voice_preview.py   # Edge TTS 语音预览生成与缓存
```

## 依赖

- [FastAPI](https://fastapi.tiangolo.com/) — Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) — ORM
- [Uvicorn](https://www.uvicorn.org/) — ASGI 服务器
- [SSE-Starlette](https://github.com/sysid/sse-starlette) — Server-Sent Events
- [edge-tts](https://github.com/rany2/edge-tts) — 语音预览
- `theia` — Agent 管道包

## 更新日志

- **2026-02-25** — 交互式审核 API（approve/edit/resume），图片管理端点，用户设置
- **2026-02-24** — URL 导入任务，任务取消/重试，TTS 语音预览
- **2026-02-22** — SQLite 持久化 + 自动迁移，SSE 进度推送
- **2026-02-18** — 初始版本：基础任务 CRUD + 文件上传
