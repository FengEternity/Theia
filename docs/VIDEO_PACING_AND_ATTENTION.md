# 视频节奏与注意力焦点优化方案

> 对应 TODO #4（视频节奏）和 #5（注意力焦点）

## 一、问题定义

### 1.1 视频节奏失衡

以样例脚本（Attention Is All You Need）为例，各场景时长分布：

| 场景 | 时长 | 旁白字数 | 画面元素数 | 问题 |
|------|------|---------|-----------|------|
| title | 30.7s | 159 | 3（标题/作者/年份） | **画面 2 秒就静止，剩余 28 秒空等** |
| overview | 48.8s | 252 | 2（问题/贡献列表） | 偏长但可接受 |
| method | 44.4s | 226 | ~5（摘要+步骤） | 所有步骤同时展示，注意力分散 |
| formula | 70.6s | 337 | 2（公式+解释） | **太长；公式一次性展示** |
| figure | 7.5s | 30 | 1（图片） | **太短，来不及看图** |
| result | 38.6s | 229 | ~3（表格/图表/发现） | 中等 |
| conclusion | 35.5s | 181 | 2（结论/贡献） | 偏长 |

**总时长 276 秒（4.6 分钟）**。主要问题：

1. **Title 场景过长**：30 秒的标题页，画面信息量极低
2. **Formula 场景过长**：70 秒盯着一个公式
3. **Figure 场景过短**：7.5 秒，观众刚开始看图就切走了
4. **时长分布不均**：最长场景是最短场景的 9.4 倍

### 1.2 注意力焦点冲突

**核心问题**：在某个时刻，旁白和画面同时要求观众高强度关注，导致认知过载。

典型冲突场景：

| 场景 | 冲突描述 |
|------|---------|
| Formula | 公式整体出现 → 观众想读公式，但旁白也在讲公式 → 两路信息竞争 |
| Figure | 图片出现 → 观众想理解图，但旁白在描述图 → 无法同时处理 |
| Method | 所有步骤同时展示 → 观众目光在步骤间游走，旁白在讲其中一个 → 不同步 |
| Overview | 问题+贡献列表同时出现 → 观众在读列表，旁白在讲背景 → 分心 |

**设计原则**（Richard Mayer 多媒体学习理论）：

- **时序原则**：相关内容同时呈现（旁白提到 X 时，X 在画面上高亮）
- **冗余原则**：不要同时展示大段文字和朗读同样的内容
- **信号原则**：用视觉提示引导观众此刻应该看哪里
- **分段原则**：复杂信息分段呈现，而非一次性全部展示

## 二、方案设计

### 2.1 视频节奏优化

#### 2.1.1 场景时长约束体系

在 `scriptwriter.py` 中引入场景时长的软硬限制：

```python
SCENE_DURATION_BOUNDS: dict[str, tuple[float, float]] = {
    "title":      (4.0,  10.0),   # 名片型场景，快进快出
    "overview":   (15.0, 30.0),   # 承载 hook + 背景铺垫
    "method":     (15.0, 30.0),   # 步骤讲解
    "formula":    (12.0, 25.0),   # 公式 + 解释
    "figure":     (10.0, 20.0),   # 图片 + 解读
    "result":     (15.0, 28.0),   # 数据对比
    "conclusion": (10.0, 20.0),   # 总结收尾
}

# 旁白字数约束（中文，每秒 ~3.5 字）
SCENE_NARRATION_LIMITS_ZH: dict[str, tuple[int, int]] = {
    "title":      (15,  35),
    "overview":   (50,  105),
    "method":     (50,  105),
    "formula":    (40,  88),
    "figure":     (35,  70),
    "result":     (50,  98),
    "conclusion": (35,  70),
}
```

**实施层**：

1. **Prompt 层（一级控制）**：在 `SCRIPT_SYSTEM_PROMPT` 中明确标注每个场景的字数范围
2. **后处理层（二级校验）**：脚本生成后，检查各场景旁白字数是否在范围内；超出时记录警告
3. **渲染层（三级兜底）**：`duration_in_frames` 钳位到 `SCENE_DURATION_BOUNDS` 范围内

#### 2.1.2 Title 场景精简

**当前状态**：

```
Title 旁白 ≈ 130-160 字，包含：
  ① Hook（出人意料的事实/问题）
  ② 论文标题+年份
  ③ 成果数据预告
  ④ 过渡到下一场景
```

**目标状态**：

```
Title 旁白 ≈ 25-35 字，仅包含：
  ① 一句开场白 + 论文名称
  示例："今天来聊一篇来自 Google 的重磅论文——Attention Is All You Need。"
```

**Hook 内容迁移到 Overview 开头**：

```
Overview 旁白 ≈ 80-105 字，结构调整为：
  ① Hook 开场（2-3 句） ← 从 title 迁移
  ② 成果数据预告       ← 从 title 迁移
  ③ 研究背景铺垫
  ④ 核心思路预告
  ⑤ 过渡到方法
```

**需要修改的文件**：

| 文件 | 改动内容 |
|------|---------|
| `packages/agent/theia/prompts/scriptwriter.py` | 修改 title 和 overview 的 prompt 指引 |
| `packages/video/src/scenes/TitleScene.tsx` | 调紧动画关键帧（适配 5-8 秒时长） |

**Prompt 修改方案**：

Title 场景 prompt 改为：

```
**title 场景**（15-35 字，5-8 秒）：
- 一句简短的开场白，引出论文名称和时间
- 不要在 title 里放 hook、数据预告或背景铺垫
- 示例："今天来聊一篇 2017 年的论文——Attention Is All You Need。"
- 示例："最近 Google DeepMind 放了一篇大招，叫做 Gemini。"
```

Overview 场景 prompt 改为：

```
**overview 场景**（70-105 字，20-30 秒）：
- 【hook 开场 · 前 2-3 句】用一个出人意料的事实或问题抓住注意力
- 可以预告最亮眼的成果数据（如"准确率直接提升了 15 个百分点"）
- 【研究背景 · 中间】铺垫这个领域之前面临什么问题
- 只在概念确实抽象难懂时使用日常比喻
- 【过渡 · 最后 1 句】自然引向方法讲解
```

**TitleScene.tsx 动画调整**：

```tsx
// 当前（为 30 秒设计）
const titleOpacity  = interpolate(frame, [0, 30],  [0, 1], ...);  // 0-1.0s
const authorOpacity = interpolate(frame, [20, 50], [0, 1], ...);  // 0.67-1.67s
const yearOpacity   = interpolate(frame, [40, 60], [0, 1], ...);  // 1.33-2.0s

// 调整后（为 5-8 秒设计，动画更紧凑）
const titleOpacity  = interpolate(frame, [0, 18],  [0, 1], ...);  // 0-0.6s
const authorOpacity = interpolate(frame, [12, 30], [0, 1], ...);  // 0.4-1.0s
const yearOpacity   = interpolate(frame, [24, 38], [0, 1], ...);  // 0.8-1.27s
```

#### 2.1.3 Formula 和 Figure 时长再平衡

**Formula 场景**（当前 70.6 秒 → 目标 12-25 秒）：

- Prompt 中限制 formula 旁白为 40-88 字
- 公式解释要精炼：只说核心直觉，不逐个符号展开
- 如果论文有多个关键公式，拆分为多个 formula 场景（当前 `_plan_scenes` 已支持）

**Figure 场景**（当前 7.5 秒 → 目标 10-20 秒）：

- Prompt 中要求 figure 旁白 35-70 字
- 旁白结构："引导看图 → 短暂停顿 → 解读关键信息"
- 增加 figure 旁白字数的下限检查

### 2.2 注意力焦点管理

#### 2.2.1 注意力模式分类

定义三种注意力模式，用于指导每个场景内不同时段的视觉和旁白关系：

| 模式 | 说明 | 旁白特征 | 画面特征 |
|------|------|---------|---------|
| `voice_primary` | 语音为主，画面辅助 | 信息密度高 | 简洁背景/关键词 |
| `visual_primary` | 画面为主，语音引导 | "请看这张图" 或短暂沉默 | 完整复杂图像 |
| `synced` | 语音与画面同步推进 | 逐项讲解 | 逐项高亮/揭示 |

每个场景内部可以包含多个注意力阶段：

```
Figure 场景时间线：
  [0-2s]  visual_primary  → 图片淡入，旁白: "我们来看这张图"
  [2-5s]  visual_primary  → 观众自由看图，旁白沉默（自然停顿）
  [5-15s] synced          → 旁白逐区域描述，画面对应区域高亮

Formula 场景时间线：
  [0-2s]  voice_primary   → 旁白引入公式，画面: 标题出现
  [2-5s]  visual_primary  → 公式整体淡入，旁白短暂停顿
  [5-20s] synced          → 旁白讲解，对应符号/部分高亮
```

#### 2.2.2 Figure 场景的"先看后讲"

**当前行为**：图片和文字同时开始淡入（图 0-30 帧，文字 20-50 帧），观众还没看清图就要同时读文字。

**优化方案**：

```
阶段 1 · 图片入场（0-90 帧 ≈ 0-3 秒）：
  - 图片从 0.95x 缓慢放大到 1x + 淡入
  - 旁白: "我们来看这张图"（一句引导语）
  - caption/description 不出现

阶段 2 · 静默观察（90-150 帧 ≈ 3-5 秒）：
  - 图片保持全尺寸展示
  - 旁白暂停（利用 TTS 生成的自然停顿，或在旁白文本中加入 "..."）
  - 无新视觉元素

阶段 3 · 讲解同步（150 帧起 ≈ 5 秒起）：
  - caption 从图片下方/右侧滑入
  - 旁白开始描述图中关键信息
  - 如果有 description，在 caption 之后延迟出现
```

**FigureScene.tsx 修改思路**：

```tsx
// 三阶段动画
const phase1End = 90;   // 3s
const phase2End = 150;  // 5s

const imgOpacity = interpolate(frame, [0, phase1End], [0, 1], { extrapolateRight: "clamp" });
const imgScale   = interpolate(frame, [0, phase1End], [0.95, 1], { extrapolateRight: "clamp" });

// caption/description 延迟到阶段 3 才出现
const textOpacity = interpolate(frame, [phase2End, phase2End + 30], [0, 1], { extrapolateRight: "clamp" });
```

**Prompt 配合修改**：

```
**figure 场景**（35-70 字，10-20 秒）——关键图表专属场景：
- 第一句话必须是引导观众看图的过渡语（如"我们来看这张图"）
- 引导语之后加入 "..." 表示停顿，留给观众 2-3 秒自行观察
- 然后再描述图中的关键信息和洞察
- 旁白示例："我们来看论文中的架构图... 左边是编码器，右边是解码器，每一层都由自注意力和前馈网络组成。"
```

#### 2.2.3 Formula 场景的"渐进揭示"

**当前行为**：公式有简单的两步展示（等号左侧 → 完整公式），但 explanation 文本几乎同时出现。

**优化方案**：

```
阶段 1 · 标题入场（0-45 帧 ≈ 0-1.5 秒）：
  - 公式标题出现（如"核心公式"）
  - 旁白引出公式（如"其中最关键的就是这个公式"）

阶段 2 · 公式展示（45-120 帧 ≈ 1.5-4 秒）：
  - 公式从中心淡入 + 轻微缩放
  - 旁白暂停 1-2 秒（"..."），给观众消化时间
  - 如果公式有多步（如等号左右分两步），逐步展开

阶段 3 · 符号讲解（120 帧起 ≈ 4 秒起）：
  - 旁白开始逐个解释关键符号
  - 理想状态：被提到的符号/部分高亮显示（未来功能）
  - explanation 文本此时才开始淡入

阶段 4 · 直觉总结（最后 3-4 秒）：
  - 旁白给出直觉理解
  - 公式保持展示，explanation 完全可见
```

**FormulaScene.tsx 修改思路**：

```tsx
const phase1End = 45;    // 1.5s 标题
const phase2End = 120;   // 4s 公式展示

// 公式在阶段 2 开始出现（现在是从 0 帧开始）
const formulaOpacity = interpolate(frame, [phase1End, phase1End + 30], [0, 1], { extrapolateRight: "clamp" });

// explanation 延迟到阶段 3
const textOpacity = interpolate(frame, [phase2End, phase2End + 30], [0, 1], { extrapolateRight: "clamp" });
```

**Prompt 配合修改**：

```
**formula 场景**（40-88 字，12-25 秒）——关键公式专属场景：
- 第一句引出公式（如"最关键的是这个公式"）
- 引出后加入 "..." 停顿 2 秒，让观众先看公式全貌
- 然后用 2-3 句话解释核心含义（不逐个符号解释，只讲直觉）
- 最后一句给出类比或在方法中的作用
- 语速放慢，保持节奏从容
```

#### 2.2.4 Method 场景的"逐步展开"

**当前行为**：所有步骤通过 `spring` 动画依次弹入（间隔 18 帧 ≈ 0.6 秒），但弹入后全部保持可见。旁白从头到尾线性播放，与步骤的视觉出现时机不一定对齐。

当前实现已有 `isActive` 高亮逻辑（基于帧范围），但高亮时间是均分的，不考虑旁白对每个步骤的实际讲解时长。

**优化方案**：

```
阶段 1 · 概述（0-60 帧 ≈ 0-2 秒）：
  - summary 文本淡入
  - 旁白讲方法的核心直觉
  - 步骤尚未出现

阶段 2 · 逐步展开（60 帧起）：
  - 每讲到一个步骤时，该步骤才出现
  - 当前步骤高亮，前序步骤变为半透明
  - 步骤出现的时机由 word timings 驱动（理想状态）
  - 退化方案：按场景时长均分每步的显示时间
```

**MethodScene.tsx 修改思路**：

最简单的改动是调整 `isActive` 逻辑，使未激活的步骤更加淡化：

```tsx
// 当前: 未激活步骤 bgAlpha=0.04, borderAlpha=0.1（仍然可见）
// 改为: 未来的步骤完全隐藏，只有当前和已过的步骤可见
const stepPhaseStart = 60 + i * (durationInFrames - 60) / stepCount;
const isRevealed = frame >= stepPhaseStart;
const isActive = isRevealed && frame < stepPhaseStart + (durationInFrames - 60) / stepCount;
const opacity = isRevealed ? 1 : 0;
```

进阶方案（依赖 word timings）：

```tsx
// 使用 word timings 确定每个步骤的讲解时间段
// 当旁白提到 "第一步" 时显示步骤 1，提到 "第二步" 时显示步骤 2...
// 需要 scriptwriter 在旁白中使用明确的步骤标记词
```

#### 2.2.5 Word Timings 驱动视觉同步（进阶）

当前 `Scene` 模型已包含 `word_timings: list[WordTiming]`，由 TTS 步骤生成。这是实现精确视觉同步的关键数据。

**架构设计**：

```
                     word_timings
                         │
    ┌────────────────────┤
    │                    │
    ▼                    ▼
旁白进度追踪器      视觉元素触发器
(NarrationTracker)  (VisualTrigger)
    │                    │
    │   当前旁白位置      │   触发条件匹配
    │                    │
    └────────┬───────────┘
             │
             ▼
      视觉元素状态更新
      (哪些步骤/符号/区域应该高亮)
```

**Remotion 侧实现思路**：

```tsx
function useNarrationProgress(wordTimings: WordTiming[], fps: number) {
  const frame = useCurrentFrame();
  const currentMs = (frame / fps) * 1000;

  const currentWordIndex = wordTimings.findIndex(
    w => w.offsetMs + w.durationMs > currentMs
  );

  const spokenText = wordTimings
    .slice(0, currentWordIndex + 1)
    .map(w => w.text)
    .join('');

  return { currentWordIndex, spokenText, currentMs };
}
```

**应用场景**：

| 场景类型 | Word Timing 驱动的效果 |
|---------|----------------------|
| Method | 当旁白提到"第 N 步"时，步骤 N 出现/高亮 |
| Formula | 当旁白提到某个符号名时，公式中对应部分高亮 |
| Figure | 当旁白描述图中某区域时，该区域添加视觉标记 |
| Result | 当旁白提到某指标时，表格对应行高亮 |

**注意**：Word Timing 驱动是进阶功能，需要：
1. Scriptwriter 在旁白中使用可识别的触发词
2. 建立触发词到视觉元素的映射关系
3. 前端实现通用的 `useNarrationProgress` hook

可以先实现基于时间均分的简单版本，后续再升级为 Word Timing 驱动。

## 三、实施计划

### Phase 1：Prompt 层面的节奏控制（改动最小，收益最大）

**目标**：通过修改 prompt 控制旁白字数，间接控制场景时长。

| 步骤 | 文件 | 改动 |
|------|------|------|
| 1.1 | `prompts/scriptwriter.py` | 为每个场景类型标注旁白字数范围 |
| 1.2 | `prompts/scriptwriter.py` | 精简 title prompt，扩充 overview prompt |
| 1.3 | `prompts/scriptwriter.py` | 调整 figure/formula prompt 的旁白结构 |
| 1.4 | `scriptwriter.py` | 添加 `SCENE_NARRATION_LIMITS_ZH` 常量和超限警告 |

**预期效果**：

- Title：30s → 6-8s
- Formula：70s → 15-22s
- Figure：7.5s → 12-18s
- 总视频时长：276s → 约 150-180s（2.5-3 分钟）

### Phase 2：视觉层面的注意力管理（中等改动）

**目标**：调整各场景的动画时序，实现"先看后讲"或"逐步展开"。

| 步骤 | 文件 | 改动 |
|------|------|------|
| 2.1 | `TitleScene.tsx` | 压缩动画关键帧至 5-8 秒 |
| 2.2 | `FigureScene.tsx` | 实现三阶段展示（图片入场 → 静默 → 讲解） |
| 2.3 | `FormulaScene.tsx` | 实现三阶段展示（标题 → 公式 → 解释） |
| 2.4 | `MethodScene.tsx` | 逐步展开 + 增强当前步骤/已过步骤的视觉区分 |

### Phase 3：时长兜底机制（保险措施）

**目标**：即使 LLM 生成的旁白偏长/偏短，也能保证合理的视频时长。

| 步骤 | 文件 | 改动 |
|------|------|------|
| 3.1 | `scriptwriter.py` | 添加 `_clamp_scene_duration()` 函数 |
| 3.2 | `scriptwriter.py` | 在 `generate_video_script()` 末尾调用钳位 |
| 3.3 | `quality_gate.py` | 增加场景时长比例检查（最长 / 最短 < 4x） |

### Phase 4：Word Timing 视觉同步（进阶功能，可选）

**目标**：利用 TTS 生成的 word timings 驱动视觉元素的精确同步。

| 步骤 | 文件 | 改动 |
|------|------|------|
| 4.1 | `hooks/useNarrationProgress.ts`（新建） | 通用的旁白进度追踪 hook |
| 4.2 | `MethodScene.tsx` | 用 word timing 驱动步骤揭示 |
| 4.3 | `ResultScene.tsx` | 用 word timing 驱动表格行高亮 |
| 4.4 | `FormulaScene.tsx` | 用 word timing 驱动符号高亮（复杂，需标注映射） |

## 四、效果评估标准

### 4.1 节奏指标

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| Title 场景时长 | 30.7s | 5-10s |
| 最长/最短场景比 | 9.4x | < 3x |
| 总视频时长 | 276s | 150-200s |
| 场景平均时长 | 39.5s | 20-28s |

### 4.2 注意力指标（主观评估）

| 维度 | 评估方式 |
|------|---------|
| 旁白-画面同步性 | 旁白提到的内容是否在画面上可见 |
| 视觉先行 | 复杂图表/公式是否给了观众"先看"的时间 |
| 信息密度均匀性 | 是否有某一时刻画面和旁白同时信息爆炸 |
| 逐步揭示 | 多步骤内容是否逐步展开而非一次性堆叠 |

### 4.3 验收标准

- [ ] Title 场景时长 ≤ 10 秒
- [ ] 所有场景时长在 `SCENE_DURATION_BOUNDS` 范围内
- [ ] Figure 场景中图片至少独占展示 2 秒后文字才出现
- [ ] Formula 场景中公式至少独占展示 2 秒后解释文字才出现
- [ ] Method 场景中步骤逐步出现而非同时弹入
- [ ] 无单一场景超过 30 秒
