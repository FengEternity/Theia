# 多 Agent 视频编排设计方案

> 将当前 scriptwriter 的单次 LLM 调用替换为 4 个协作 Agent，覆盖脚本生成和视觉编排两个层面。

## 一、现状分析

当前 `packages/agent/theia/output/scriptwriter.py` 用**一次 LLM 调用**完成所有工作：

```
PaperSummary → _plan_scenes() (Python确定性规划) → 单次LLM → VideoScript
```

**问题**：

- 场景规划（what to show）、旁白创作（what to say）、视觉编排（when to show）耦合在一次调用中
- LLM 无法同时优化叙事质量、节奏控制、注意力管理这三个维度
- 动画时序完全硬编码在 Remotion 组件中，不随内容自适应
- `VIDEO_PACING_AND_ATTENTION.md` 中识别的节奏/注意力问题本质上需要**分工思考**

## 二、多 Agent 架构设计

### 2.1 数据流

```
PaperSummary
    │
    ▼
Agent 1: Story Architect ──→ StoryBlueprint
    │
    ▼
Agent 2: Scene Writer ──→ SceneNarrations（含注意力标注）
    │
    ▼
TTS Engine（现有 edge-tts）──→ word_timings
    │
    ▼
Agent 3: Visual Director ──→ VisualChoreography（动画编排）
    │
    ▼
Agent 4: Pacing Reviewer ──→ 通过 → VideoScript / 驳回 → 回到 Agent 2 或 3
```

### 2.2 各 Agent 职责

#### Agent 1: Story Architect（故事架构师）

- **输入**: `PaperSummary`
- **输出**: `StoryBlueprint`
- **职责**:
  - 决定场景列表、顺序和目标时长范围（替代当前的 `_plan_scenes()` Python 函数）
  - 定义叙事弧线（hook → 铺垫 → 高潮 → 收尾）
  - 为每个场景设定"叙事角色"（吸引注意 / 知识铺垫 / 核心论证 / 情感收束）
  - 标注关键 moment（全片最重要的 2-3 个信息点）

#### Agent 2: Scene Writer（场景编剧）

- **输入**: `StoryBlueprint` + `PaperSummary`
- **输出**: `list[SceneNarration]`（每场景的旁白 + 注意力标注）
- **职责**:
  - 按 Blueprint 的字数范围撰写旁白
  - 在旁白中标注停顿点和强调词
  - 标注注意力模式切换点
  - 确保场景间过渡自然

#### Agent 3: Visual Director（视觉导演）

- **输入**: `SceneNarrations` + `word_timings`（来自 TTS）+ `StoryBlueprint`
- **输出**: `list[VisualChoreography]`
- **职责**:
  - 为每个场景定义动画阶段（AnimationPhase）
  - 基于 word_timings 设定元素的精确出现/消失时机
  - 设定注意力模式（voice_primary / visual_primary / synced）的时间窗口
  - 实现"先看后讲"和"逐步揭示"策略
- **初始实现**: 基于规则引擎（场景类型预设模板 + word_timings 插值），后续可升级为 LLM 驱动

#### Agent 4: Pacing Reviewer（节奏审核员）

- **输入**: 完整的已组装脚本（旁白 + 视觉编排 + 时长）
- **输出**: `ReviewResult`（通过 / 不通过 + 具体修改建议）
- **职责**:
  - 检查时长约束：每个场景是否在 `SCENE_DURATION_BOUNDS` 内
  - 检查节奏均衡：最长/最短场景比是否 < 3x
  - 检查注意力冲突
  - 检查总时长是否在 2-4 分钟
  - 给出具体的修改建议

### 2.3 LangGraph 编排

TTS 位于 Scene Writer 和 Visual Director 之间（Visual Director 需要 word_timings）：

```
extract → Story Architect → Scene Writer → TTS → Visual Director → Pacing Reviewer → render
                                 ↑                                        │
                                 └──────── fail（修改旁白）────────────────┘
```

审核循环优化：
- Reviewer 只建议修改视觉编排 → 直接回到 Visual Director（无需重新 TTS）
- Reviewer 建议修改旁白 → 回到 Scene Writer → 重新 TTS → Visual Director
- 最多 2 轮审核循环

### 2.4 数据模型

新增模型定义在 `packages/agent/theia/schemas.py`：

- `ScenePlan` — 单场景规划
- `StoryBlueprint` — 故事架构师输出
- `AttentionMarker` — 旁白中的注意力标注
- `SceneNarration` — 场景编剧输出
- `AnimationPhase` — 单个动画阶段
- `VisualChoreography` — 视觉导演输出
- `ReviewResult` — 审核员输出

`Scene` 模型新增 `choreography: list[AnimationPhase]` 字段（默认空列表，向后兼容）。

### 2.5 Remotion 侧消费

新增 `useChoreography` hook 读取 `choreography` 数据驱动动画。
场景组件优先使用 choreography 数据；为空时退化为硬编码时序。

## 三、渐进式采用策略

- **Phase 0**: choreography 为空时，所有场景行为与现在完全一致
- **Phase 1**: 仅启用 Story Architect + Scene Writer（替代当前单次 LLM），Reviewer 用规则检查
- **Phase 2**: 加入 Visual Director（需配合 Remotion 侧 `useChoreography` hook）
- **Phase 3**: 完整 4-Agent 闭环 + Pacing Reviewer 的 LLM 审核

## 四、成本和延迟影响

| 维度 | 当前 | 多 Agent |
|------|------|---------|
| LLM 调用次数（script 阶段） | 1 次 | 3-4 次（+审核可能触发重做） |
| 预计 Token 消耗 | ~4K output | ~8-12K output |
| 延迟 | ~5-10s | ~15-25s |
| 质量 | 一次性输出，全凭 prompt | 分工思考 + 审核循环，质量上限更高 |

## 五、模型选择策略

- Story Architect: 轻量模型（gpt-4o-mini）— 规划任务
- Scene Writer: 中等模型（gpt-4o-mini 或 gpt-4o）— 创意写作
- Visual Director: 规则引擎（无需 LLM）— 初始版本
- Pacing Reviewer: 轻量模型（gpt-4o-mini）— 规则 + 判断

## 六、文件改动范围

### Agent 侧（Python）

| 文件 | 说明 |
|------|------|
| `schemas.py` | 新增 StoryBlueprint 等模型 |
| `output/story_architect.py`（新） | Agent 1 |
| `output/scene_writer.py`（新） | Agent 2 |
| `output/visual_director.py`（新） | Agent 3 |
| `output/pacing_reviewer.py`（新） | Agent 4 |
| `output/scriptwriter.py` | 重构为多 Agent 编排入口 |
| `pipeline.py` | script_node 替换为子图 |
| `prompts/story_architect.py`（新） | Agent 1 prompt |
| `prompts/scene_writer.py`（新） | Agent 2 prompt |

### Video 侧（TypeScript）

| 文件 | 说明 |
|------|------|
| `hooks/useChoreography.ts`（新） | 动画编排 hook |
| `types/script.ts` | 新增 AnimationPhase 类型 |
| `scenes/FigureScene.tsx` | 接入 choreography |
| `scenes/FormulaScene.tsx` | 接入 choreography |
| `scenes/MethodScene.tsx` | 接入 choreography |
