# Theia Video

基于 Remotion 的视频渲染引擎。将 VideoScript JSON 渲染为带动画、旁白、字幕的讲解视频。

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

生产环境中由 agent 的 `renderer.py` 通过子进程自动调用 `remotion render`。

## 场景组件（15 种）

场景是视频的基本单元，每个场景对应 VideoScript 中的一个条目：

| 场景 | 文件 | 用途 |
|------|------|------|
| Title | `TitleScene.tsx` | 标题页（论文标题、作者、期刊） |
| Overview | `OverviewScene.tsx` | 论文概述 |
| Method | `MethodScene.tsx` | 方法/技术介绍 |
| Figure | `FigureScene.tsx` | 图表展示与解说 |
| Formula | `FormulaScene.tsx` | 公式推导（KaTeX 渲染） |
| Result | `ResultScene.tsx` | 实验结果展示 |
| Conclusion | `ConclusionScene.tsx` | 总结与展望 |
| Concept | `ConceptScene.tsx` | 概念解释 |
| Analogy | `AnalogyScene.tsx` | 类比说明 |
| Comparison | `ComparisonScene.tsx` | 对比分析 |
| Relationship | `RelationshipScene.tsx` | 关系图谱 |
| SummaryCard | `SummaryCardScene.tsx` | 摘要卡片 |
| CodeDemo | `CodeDemoScene.tsx` | 代码演示 |
| Demo | `DemoScene.tsx` | 演示动画 |
| CharacterTalk | `CharacterTalkScene.tsx` | 角色讲述 |

## 通用组件（18 个）

可在场景中复用的 UI 组件：

| 组件 | 用途 |
|------|------|
| Subtitle | 字幕（跟随旁白同步） |
| BarChart | 柱状图动画 |
| DataTable | 数据表格 |
| FormulaBlock | LaTeX 公式渲染（KaTeX） |
| FigureDisplay | 图片展示（缩放、边框） |
| BulletList | 列表逐项出现 |
| HighlightText | 关键词高亮 |
| AnimatedText | 文字动画 |
| TypewriterText | 打字机效果 |
| EmphasisText | 强调文本 |
| ProgressBar | 进度条 |
| SceneWrapper | 场景统一包装器（背景、内边距） |
| SceneLabel | 场景标签（步骤编号） |
| DynamicBackground | 动态背景 |
| BrowserFrame | 浏览器框架样式 |
| ComparisonBadge | 对比标签 |
| CircleHighlight | 圆圈高亮标注 |
| HandDrawnArrow | 手绘箭头 |

## 项目结构

```
src/
├── Root.tsx              # Remotion Composition 注册（PaperVideo, PopsciVideo）
├── PaperVideo.tsx        # 主 Composition：场景路由 + 转场动画
├── scenes/               # 15 种场景组件
├── components/           # 18 个通用组件
├── themes/               # 主题定义（academic, popsci）
├── hooks/                # useScale 响应式缩放
└── types/
    └── script.ts         # Zod schema（VideoScript 类型，与 Python 端对齐）
```

## 多尺寸适配

所有组件通过 `useScale` hook 自动适配不同视频尺寸：

| 预设 | 分辨率 |
|------|--------|
| landscape | 1920×1080 |
| portrait | 1080×1920 |
| xiaohongshu | 1080×1440 |
| square | 1080×1080 |

## 技术栈

- [Remotion 4](https://www.remotion.dev/) — 代码驱动视频渲染
- [React 19](https://react.dev/) — UI 组件
- [KaTeX](https://katex.org/) — LaTeX 数学公式
- [Zod](https://zod.dev/) — 运行时类型校验
- TypeScript 5

## 更新日志

- **2026-02-25** — 新增 8 种场景（Formula/Comparison/Relationship/CodeDemo/CharacterTalk 等），主题系统
- **2026-02-23** — 通用组件库扩展至 18 个，多尺寸预设自动适配
- **2026-02-20** — 初始版本：7 种基础场景 + Remotion 渲染集成
