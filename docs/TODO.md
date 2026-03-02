# 功能需求 (Features)

## ✅ 已实现

| # | 功能 | 实现位置 |
|---|------|---------|
| 4 | 视频节奏根据内容自动调整 | `output/pacing_reviewer.py` + `scene_registry.py` |
| 5 | 注意力焦点管理（旁白/画面切换） | `output/visual_director.py`, `hooks/useChoreography.ts` |
| 6 | 生成的 UI 界面可视化展示 | `packages/web`（任务详情页 + 视频预览） |
| 8 | 视频节奏不再死板，根据内容调整 | `pacing_reviewer.py` 动态时长 + 场景注册表 |
| 10 | 抽象概念/公式使用类比方法解释 | `AnalogyScene.tsx` + analogy 场景类型 |
| 16 | 视频时长不再硬限制，根据内容调整 | `pacing_reviewer.py` TOTAL_DURATION_RANGE |
| 17 | 质量门控后端独立 LangGraph 节点 | `pipeline.py`: `review_extract_node`, `review_script_node`, `review_tts_node` |
| 20 | 设计不同场景间的动画跳转 | `PaperVideo.tsx` TRANSITION_CONFIG（fade/slide/wipe） |

## ⚠️ 部分实现（需继续完善）

| # | 功能 | 当前状态 | 待完善内容 |
|---|------|---------|-----------|
| 1 | 适配知乎/微信公众号文章解读 prompt | `parsing/zhihu.py`, `parsing/web.py` 抓取已实现 | prompt 尚未针对非学术文章优化，提取结果不适配 |
| 2 | 语音优化 | edge-tts 基础功能完整，支持 speech_rate | 停顿点、强调词语音控制；更多 TTS 引擎支持 |
| 9 | 第二轮修复（质量门控修复轮次） | `gate.py` ReAct 修复循环已重写，已接入流水线 | 建议实测验证修复是否真正执行（参见 Bug #3） |
| 11 | Remotion 内容填充有效性检测 | Pydantic/Zod 模型校验基础存在 | 缺少运行时 fallback 渲染、空数据/异常数据的 UI 降级显示 |
| 13 | 分片段渲染拼接 | Manim 片段预渲染 + `ManimClip` 播放组件已有 | 通用 Remotion 片段缓存复用尚未实现 |
| 19 | 空镜头动画设计 | `manim_renderer.py` + `manim_templates.py` 基础框架已有 | 模板类型有限（仅 transformer/attention/formula），需扩充动画库 |

## ❌ 未实现

| # | 功能 | 优先级建议 | 相关文档 |
|---|------|-----------|---------|
| 17b | 质量门控前端独立页面（可查看/跳过/对话式反馈每个门控环节） | 高 | [重构实施计划.md](重构实施计划.md) Phase 3 |
| 3 | 构建知识库，实现问答系统 | 低 | — |
| 7 | 绘制原型图（设计稿工具集成） | 低 | — |
| 12 | 把 Remotion 封装成 Cursor Skill | 低 | — |
| 14 | 集成 Agent 训练框架（AgentScope） | 低 | — |
| 15 | 爬取 B 站优秀博主视频脚本用于优化 | 低 | — |
| 18 | A2A（Agent-to-Agent）设计模式集成 | 中 | — |

---

# Bug

| # | 问题 | 状态 | 备注 |
|---|------|------|------|
| 1 | 视频中图和文本对应不上 | ❌ 未修复 | 图片路径映射逻辑需排查 |
| 2 | 实验结果提取内容不完整 | ⚠️ 部分修复 | `table_analyst.py` 已加入；图表数值结构化提取方案见 `信息提取优化方案.md` |
| 3 | 公式出现前有一帧卡顿（非 useCurrentFrame 驱动） | ⚠️ 待验证 | `FormulaScene.tsx` 已改用 useCurrentFrame；需实测确认 |

---

# Done（已完成并关闭）

| # | 功能/Bug |
|---|---------|
| — | 浅色背景下研究问题字体颜色问题 |
| — | 文本中数学公式渲染问题（KaTeX 集成） |
| — | 重构 `packages/agent/theia` 代码结构（extraction/llm/output/parsing/quality 子模块） |
