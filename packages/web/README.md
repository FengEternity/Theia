# Theia Web

Vue 3 前端界面，提供论文上传、任务管理、实时进度追踪、交互式审核和视频预览功能。

## 安装与开发

```bash
cd packages/web
pnpm install
pnpm dev          # 开发服务器（端口 5173）
pnpm build        # 生产构建（含类型检查）
pnpm preview      # 预览生产构建
```

开发模式下通过 Vite 代理将 `/api` 请求转发到后端（`localhost:8000`）。

## 页面

| 页面 | 文件 | 功能 |
|------|------|------|
| 上传 | `UploadView.vue` | 拖拽上传 PDF 或粘贴 URL，配置 LLM 模型、语音、预设等参数 |
| 任务列表 | `TaskListView.vue` | 所有任务的列表视图，支持删除、重试 |
| 任务详情 | `TaskDetailView.vue` | SSE 实时进度、流水线阶段可视化、中间产物查看/编辑、视频预览播放 |
| 设置 | `SettingsView.vue` | 全局设置管理 |

## 项目结构

```
src/
├── App.vue               # 根布局（顶栏 + 路由出口）
├── views/
│   ├── UploadView.vue    # 上传页
│   ├── TaskListView.vue  # 任务列表
│   ├── TaskDetailView.vue # 任务详情
│   └── SettingsView.vue  # 设置
├── components/           # 可复用组件
├── api/
│   ├── client.ts         # Axios API 客户端
│   └── types.ts          # TypeScript 类型定义
└── router/
    └── index.ts          # Vue Router 路由配置
```

## 核心交互流程

1. **上传** — 拖拽 PDF / 输入 URL → 选择模型、语音、预设 → 创建任务
2. **进度追踪** — 通过 SSE 实时显示流水线各阶段的进度
3. **交互审核**（可选）— 查看/编辑提取结果和视频脚本 → 批准继续
4. **图片管理** — 查看论文图片、重新分析、旋转
5. **视频预览** — 内嵌播放器预览最终视频 → 下载

## 技术栈

- [Vue 3](https://vuejs.org/) — 组合式 API
- [Element Plus](https://element-plus.org/) — UI 组件库
- [Vue Router 4](https://router.vuejs.org/) — 路由
- [Axios](https://axios-http.com/) — HTTP 客户端
- [KaTeX](https://katex.org/) — LaTeX 公式渲染
- [markdown-it](https://github.com/markdown-it/markdown-it) — Markdown 渲染
- [Vite 6](https://vite.dev/) — 构建工具
- TypeScript 5
- pnpm — 包管理器

## 更新日志

- **2026-02-28** — 迁移至 pnpm，新增 KaTeX 依赖（公式预览）
- **2026-02-25** — 交互式审核流程，图片管理，设置页
- **2026-02-23** — 任务详情页 SSE 实时进度，视频内嵌预览
- **2026-02-20** — 初始版本：上传页 + 任务列表
