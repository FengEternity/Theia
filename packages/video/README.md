# Theia Video

基于 Remotion 的视频渲染引擎。将 VideoScript JSON 渲染为带动画、旁白、字幕的讲解视频，支持编舞驱动的注意力管理系统。

## 安装与开发

```bash
cd packages/video
pnpm install

# 打开 Remotion Studio（开发预览）
pnpm dev

# 渲染视频
pnpm build                    # 默认渲染
pnpm render PaperVideo out/video.mp4   # 指定输出
```

生产环境中由 agent 的 `output/renderer.py` 通过子进程自动调用 `remotion render`。

## 场景组件（15 种）

场景是视频的基本单元，每个场景对应 VideoScript 中的一个条目：

| 场景 | 文件 | 用途 |
|------|------|------|
| Title | `TitleScene.tsx` | 标题页（论文标题、作者、期刊） |
| Overview | `OverviewScene.tsx` | 论文概述（问题 + 贡献） |
| Method | `MethodScene.tsx` | 方法/技术介绍（步骤 + 公式） |
| Figure | `FigureScene.tsx` | 图表展示与解说 |
| Formula | `FormulaScene.tsx` | 公式推导（KaTeX 渲染） |
| Result | `ResultScene.tsx` | 实验结果展示（数据集 + 指标） |
| Conclusion | `ConclusionScene.tsx` | 总结与展望 |
| Concept | `ConceptScene.tsx` | 概念解释（定义 + 关键词） |
| Analogy | `AnalogyScene.tsx` | 类比说明（概念↔类比映射） |
| Comparison | `ComparisonScene.tsx` | 对比分析（多项目特征矩阵） |
| Relationship | `RelationshipScene.tsx` | 关系图谱（节点 + 边，tree/radial/flow） |
| SummaryCard | `SummaryCardScene.tsx` | 摘要卡片（要点列表） |
| CodeDemo | `CodeDemoScene.tsx` | 代码演示（语法高亮 + 行高亮） |
| Demo | `DemoScene.tsx` | 演示动画（chat/terminal/code-editor/browser） |
| CharacterTalk | `CharacterTalkScene.tsx` | 角色讲述（对话气泡） |

## 通用组件（21 个）

可在场景中复用的 UI 组件：

| 组件 | 用途 |
|------|------|
| Subtitle | 字幕（跟随旁白同步） |
| BarChart | 柱状图动画 |
| DataTable | 数据表格 |
| FormulaBlock | LaTeX 公式渲染（KaTeX） |
| FormulaOverlay | 公式浮层（覆盖在场景上） |
| FigureDisplay | 图片展示（缩放、边框） |
| BulletList | 列表逐项出现 |
| HighlightText | 关键词高亮 |
| AnimatedText | 文字动画 |
| TypewriterText | 打字机效果 |
| EmphasisText | 强调文本 |
| InlineLatex | 行内 LaTeX（文本与公式混排） |
| ManimClip | Manim 动画片段播放 |
| ProgressBar | 进度条 |
| SceneWrapper | 场景统一包装器（背景、内边距） |
| SceneLabel | 场景标签（步骤编号） |
| DynamicBackground | 动态背景 |
| BrowserFrame | 浏览器框架样式 |
| ComparisonBadge | 对比标签 |
| CircleHighlight | 圆圈高亮标注 |
| HandDrawnArrow | 手绘箭头 |

## Hooks

| Hook | 用途 |
|------|------|
| `useScale` | 响应式缩放，自动适配不同视频尺寸（基于 1920×1080 设计稿） |
| `useChoreography` | 读取 AnimationPhase 编排数据，返回当前帧的视觉状态（注意力模式、可见元素、高亮目标、阶段进度） |

### useChoreography

编舞 hook 是注意力管理系统的前端核心，从 `choreography: AnimationPhase[]` 数据中派生出当前帧的渲染状态：

- `attentionMode` — 当前注意力模式：`voice_primary`（语音主导）/ `visual_primary`（视觉主导）/ `synced`（同步）
- `visibleElements` — 当前阶段应显示的元素列表
- `highlightElement` — 当前高亮元素
- `phaseProgress` — 当前阶段内进度（0-1）
- `isElementVisible(id)` / `isElementHighlighted(id)` — 元素状态查询

当 `choreography` 为空时，所有元素默认可见（向后兼容硬编码动画）。

## 数据类型

VideoScript 的 Zod schema 定义在 `types/script.ts`，与 Python 端 Pydantic 模型保持同步：

| 类型 | 说明 |
|------|------|
| `VideoScript` | 顶层结构：`meta` + `scenes[]` |
| `VideoMeta` | 视频元数据：fps、宽高、主题 |
| `Scene` | 单场景：类型、时长、旁白、音频、data、wordTimings、choreography、manimClips |
| `WordTiming` | 单词时序：文本、偏移量、持续时间 |
| `AnimationPhase` | 动画阶段：时间范围、注意力模式、元素、转场 |
| `ManimClip` | Manim 片段：路径、时间、位置、透明度 |
| `SceneType` | 15 种场景类型枚举 |

## 项目结构

```
src/
├── Root.tsx              # Remotion Composition 注册（PaperVideo, PopsciVideo）
├── PaperVideo.tsx        # 主 Composition：场景路由 + 转场动画
├── scenes/               # 15 种场景组件
├── components/           # 21 个通用组件
├── themes/               # 主题定义（academic, popsci）
├── hooks/
│   ├── useScale.ts       # 响应式缩放
│   └── useChoreography.ts # AnimationPhase 编排驱动
└── types/
    └── script.ts         # Zod schema（与 Python 端对齐）
```

## 多尺寸适配

所有组件通过 `useScale` hook 自动适配不同视频尺寸：

| 预设 | 分辨率 |
|------|--------|
| landscape | 1920×1080 |
| bilibili | 1920×1080 |
| portrait | 1080×1920 |
| douyin | 1080×1920 |
| xiaohongshu | 1080×1440 |
| square | 1080×1080 |

## 技术栈

- [Remotion 4](https://www.remotion.dev/) — 代码驱动视频渲染
- [React 19](https://react.dev/) — UI 组件
- [KaTeX](https://katex.org/) — LaTeX 数学公式
- [Zod](https://zod.dev/) — 运行时类型校验
- TypeScript 5

## 更新日志

- **2026-02-28** — 新增 InlineLatex、FormulaOverlay、ManimClip 组件；useChoreography hook（注意力管理系统）；WordTiming / AnimationPhase / ManimClip 类型
- **2026-02-25** — 新增 8 种场景（Formula/Comparison/Relationship/CodeDemo/CharacterTalk 等），主题系统
- **2026-02-23** — 通用组件库扩展，多尺寸预设自动适配
- **2026-02-20** — 初始版本：7 种基础场景 + Remotion 渲染集成
