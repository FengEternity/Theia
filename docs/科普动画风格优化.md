# 「小白debug风格」技术科普动画视频生成优化方案

> 参考视频：[7分钟速通Agent Skills是什么？](https://www.bilibili.com/video/BV162cPzhEGU/)（小白debug）
>
> 目标：让 Theia 具备生成此类「卡通角色 + 动画演示 + 技术科普」风格视频的能力。

---

## 一、目标风格特征分析

### 1.1 视觉风格

| 特征 | 描述 |
|------|------|
| **卡通吉祥物** | 可爱 Q 版二次元角色（银发丸子头女孩 + 黄色上衣），坐在笔记本电脑前，始终出现在画面中 |
| **模拟浏览器窗口** | 用仿浏览器 UI 框（地址栏、按钮、标签页）作为内容的视觉容器 |
| **火柴人/简笔 AI 角色** | 用关节点火柴人 + AI 人脸徽章表示抽象概念（如"AI在打篮球"表示Skills） |
| **配色方案** | 青绿（#5BB5B0）+ 明黄（#F5D76E）+ 白底，整体明亮活泼 |
| **字体风格** | 大号粗体中文标题（如思源黑体/阿里巴巴普惠体），关键词高亮加粗 |
| **底部字幕条** | 黄色/橙色底色的字幕条，文字清晰醒目 |
| **视觉隐喻** | 用具象物品（篮球、浏览器、电脑）来类比抽象技术概念 |
| **角标/水印** | 角落放置频道 logo、bilibili 水印 |
| **平面设计风格** | 扁平化、简洁、色块分明，无过度渐变 |

### 1.2 内容结构

| 特征 | 描述 |
|------|------|
| **Hook 开场** | 前 3 秒用一个有趣的问题或反常识吸引注意 |
| **概念拆解** | 把复杂概念拆成"是什么→为什么→怎么做"的三段式 |
| **类比教学** | 大量使用生活类比（如"就像餐厅点菜一样"） |
| **模拟界面演示** | 用模拟的 GPT/代码界面展示实际交互过程 |
| **递进式揭秘** | 一层层揭开概念关系，制造"原来如此"的感觉 |
| **总结收尾** | 简洁的关系图/总结卡收尾 |

### 1.3 动效节奏

| 特征 | 描述 |
|------|------|
| **快节奏剪辑** | 每个画面停留 3-8 秒，信息密度高 |
| **元素逐步出现** | 关键概念一个一个弹出，配合旁白节奏 |
| **弹性动画** | 元素入场带弹性（overshoot/spring），活泼感强 |
| **缩放强调** | 关键词放大缩小产生强调效果 |
| **手绘风箭头/连线** | 用手绘风格的箭头连接概念关系 |
| **表情包/meme** | 适当穿插搞笑表情和 meme 元素 |

---

## 二、现状与差距分析

### 2.1 Theia 当前能力

```
PDF → MinerU → LLM 提取 → LLM 脚本 → Edge TTS → Remotion 渲染 → MP4
```

- 7 种学术场景（title / overview / method / formula / figure / result / conclusion）
- 深色学术风格（#0f172a 深蓝背景，蓝紫渐变）
- 基础动画（线性淡入、弹入、呼吸效果）
- system-ui 默认字体
- 粒子 + 光球背景

### 2.2 差距矩阵

| 维度 | 当前 Theia | 目标风格 | 差距等级 |
|------|-----------|---------|---------|
| **场景类型** | 7 种学术场景 | 概念解释/界面演示/关系图/角色对话 等 | 🔴 大 |
| **视觉风格** | 深色学术信息图 | 明亮卡通扁平化 | 🔴 大 |
| **角色系统** | 无 | 吉祥物 + AI 角色 + 表情系统 | 🔴 大 |
| **UI 模拟** | 无 | 浏览器/终端/代码编辑器模拟 | 🟡 中 |
| **字体** | system-ui | 品牌化中文粗体 | 🟢 小 |
| **动画** | 线性淡入 | 弹性 spring + 缩放 + 手绘箭头 | 🟡 中 |
| **字幕** | 半透明底色 | 彩色底条字幕 | 🟢 小 |
| **旁白风格** | 口语化/学术/故事 3 种 | 趣味科普风（更轻松、更多梗） | 🟡 中 |
| **节奏** | 场景间匀速 | 快剪、信息密度高 | 🟡 中 |

---

## 三、优化方案架构

### 3.1 总体目标

在保留现有学术论文讲解能力的基础上，新增「技术科普动画」视频风格，使 Theia 支持**多风格（theme）**视频生成。

### 3.2 架构调整方向

```
  PDF → MinerU → LLM 提取 → LLM 脚本生成器 → Edge TTS → Remotion → MP4
                                  │                          │
                          ┌───────┴────────┐         ┌──────┴──────────┐
                          │ + 风格模板      │         │ Theme System    │
                          │   academic     │         │ ├─ academic     │
                          │   popsci       │         │ └─ popsci (新增)│
                          │ + 扩展场景类型  │         │ + 新场景组件    │
                          └────────────────┘         │ + 角色系统      │
                                                     │ + 弹性动画库    │
                                                     └─────────────────┘
```

输入源保持不变（PDF 论文），改造集中在**脚本风格模板**和**视觉渲染层**。

---

## 四、分阶段实施方案

### Phase 1：主题系统 + 视觉改造（预计 2 周）

**目标**：建立 Theme 系统，实现科普风格的视觉基础。

#### 1.1 Theme 系统设计

在 `packages/video/src/` 下新增主题配置：

```typescript
// themes/index.ts
interface ThemeConfig {
  id: 'academic' | 'popsci';
  name: string;
  colors: {
    background: string;        // 页面背景
    surface: string;           // 卡片/面板背景
    primary: string;           // 主色
    secondary: string;         // 辅助色
    accent: string;            // 强调色
    text: string;              // 正文颜色
    textSecondary: string;     // 次要文字
    subtitle: {
      background: string;      // 字幕条背景
      text: string;            // 字幕文字
      highlight: string;       // 高亮词
    };
  };
  fonts: {
    title: string;             // 标题字体
    body: string;              // 正文字体
    code: string;              // 代码字体
  };
  animation: {
    entrance: 'linear' | 'spring' | 'bounce';
    exitStyle: 'fade' | 'scale' | 'slide';
    speed: 'slow' | 'normal' | 'fast';
  };
  decoration: {
    borderRadius: number;
    showParticles: boolean;
    backgroundStyle: 'gradient' | 'flat' | 'pattern';
  };
}
```

```typescript
// themes/popsci.ts — 科普卡通主题
export const popsciTheme: ThemeConfig = {
  id: 'popsci',
  name: '科普卡通',
  colors: {
    background: '#F0F9F7',       // 浅青绿
    surface: '#FFFFFF',          // 白色卡片
    primary: '#5BB5B0',          // 青绿
    secondary: '#F5D76E',        // 明黄
    accent: '#FF6B6B',           // 强调红
    text: '#2D3436',             // 深灰文字
    textSecondary: '#636E72',
    subtitle: {
      background: '#F5D76E',
      text: '#2D3436',
      highlight: '#E17055',
    },
  },
  fonts: {
    title: '"Alibaba PuHuiTi Bold", "Source Han Sans CN Bold", system-ui',
    body: '"Alibaba PuHuiTi", "Source Han Sans CN", system-ui',
    code: '"JetBrains Mono", "Fira Code", monospace',
  },
  animation: {
    entrance: 'spring',
    exitStyle: 'scale',
    speed: 'fast',
  },
  decoration: {
    borderRadius: 16,
    showParticles: false,
    backgroundStyle: 'flat',
  },
};
```

#### 1.2 「模拟浏览器窗口」组件

新增核心视觉容器组件，模拟小白debug视频中的浏览器窗口框架：

```typescript
// components/BrowserFrame.tsx
interface BrowserFrameProps {
  title?: string;          // 地址栏文字
  children: React.ReactNode;
  width?: number;
  height?: number;
  style?: 'chrome' | 'minimal' | 'code-editor';
}
```

特征：
- 顶部窗口控制按钮（红/黄/绿圆点）
- 地址栏（可显示 URL 或标题文字）
- 白色内容区域
- 圆角 + 轻微阴影
- 支持 chrome / minimal / code-editor 三种变体

#### 1.3 配色与字体替换

- 引入阿里巴巴普惠体（开源免费商用）作为中文标题字体
- 引入 JetBrains Mono 作为代码字体
- DynamicBackground 增加 `flat` 模式（纯色/浅色背景）

#### 1.4 字幕条改造

当前字幕为半透明黑底白字，改为支持主题色彩字幕条：

```typescript
// 科普风格字幕：黄底黑字，圆角，底部居中
<SubtitleBar
  background="#F5D76E"
  textColor="#2D3436"
  borderRadius={12}
  position="bottom-center"
/>
```

---

### Phase 2：新场景类型 + 角色系统（预计 3 周）

**目标**：扩展场景类型以适应技术概念讲解，引入角色系统。

#### 2.1 新增科普场景类型

在现有 7 种学术场景基础上，新增面向科普内容的场景：

| 场景类型 | 用途 | 视觉描述 |
|---------|------|---------|
| `concept` | 概念定义 | 浏览器框内显示大字标题 + 简短解释 + 图标 |
| `analogy` | 类比教学 | 左右对比布局：抽象概念 ←→ 生活类比 |
| `demo` | 界面模拟演示 | 模拟 GPT/终端/IDE 界面的交互过程 |
| `relationship` | 关系图 | 概念间的连线/层级关系图 |
| `comparison` | 对比表格 | 多个概念的横向特征对比 |
| `character_talk` | 角色对话 | 吉祥物角色提出问题或总结 |
| `summary_card` | 总结卡片 | 关键要点的卡片式总结 |
| `code_demo` | 代码演示 | 代码编辑器模拟，逐行高亮 |

#### 2.2 角色系统

引入静态角色素材系统（非实时生成，预制素材库）：

```
packages/video/public/characters/
├── mascot/                    # 吉祥物角色
│   ├── thinking.png           # 思考
│   ├── explaining.png         # 讲解
│   ├── surprised.png          # 惊讶
│   ├── happy.png              # 开心
│   └── pointing.png           # 指向
├── ai-figure/                 # AI 火柴人角色
│   ├── standing.png
│   ├── walking.png
│   └── working.png
└── decorations/               # 装饰元素
    ├── arrows/                # 手绘风箭头
    ├── bubbles/               # 对话气泡
    ├── icons/                 # 技术图标（齿轮、灯泡、火箭等）
    └── stickers/              # 贴纸（星星、感叹号等）
```

角色组件：

```typescript
// components/Character.tsx
interface CharacterProps {
  character: 'mascot' | 'ai-figure';
  expression: string;         // thinking | explaining | surprised | ...
  position: 'left' | 'right' | 'center' | 'bottom-right';
  scale?: number;
  enterAnimation?: 'bounce' | 'slide' | 'pop';
}
```

#### 2.3 「关系图」场景组件

用于展示 Agent Skills / MCP / Workflow 等概念间关系：

```typescript
// scenes/RelationshipScene.tsx
interface RelationshipData {
  nodes: Array<{
    id: string;
    label: string;
    icon?: string;          // 技术图标
    color?: string;
    description?: string;
  }>;
  edges: Array<{
    from: string;
    to: string;
    label?: string;
    style?: 'solid' | 'dashed' | 'arrow';
  }>;
  layout: 'tree' | 'radial' | 'flow';  // 布局方式
}
```

动效：节点逐个出现（弹入），边逐条连线（描线动画），配合旁白节奏。

#### 2.4 「界面模拟」场景组件

模拟 ChatGPT / 终端 / 代码编辑器的交互：

```typescript
// scenes/DemoScene.tsx
interface DemoData {
  interface: 'chat' | 'terminal' | 'code-editor' | 'browser';
  steps: Array<{
    action: 'type' | 'response' | 'highlight' | 'scroll';
    content: string;
    delay?: number;          // 帧延迟
  }>;
}
```

动效：打字机效果输入、逐行出现回复、代码高亮等。

---

### Phase 3：脚本生成引擎升级（预计 2 周）

**目标**：扩展脚本生成器以支持科普内容和新场景类型。

#### 3.1 科普脚本旁白风格

在现有的 `NARRATION_STYLE_OVERRIDES` 中新增 `popsci` 风格：

```python
NARRATION_STYLE_OVERRIDES["popsci"] = """\
### 写作风格：
- 活泼有趣，像跟好朋友聊天，语气轻松自然
- 善于用生活中的类比解释抽象概念（如"就像外卖员送餐一样"）
- 复杂概念拆成"是什么 → 为什么需要 → 怎么工作"的递进式结构
- 适当用夸张和反转制造趣味感
- 制造"原来如此！"的恍然大悟感
- 每个场景节奏更快（3-8 秒），信息密度更高
- 英文术语首次出现时给出中文翻译 + 英文原名，后续仅用中文简称
- **每个场景的最后一句话必须能自然过渡到下一个场景**"""
```

同时，当 `narration_style="popsci"` 时，脚本生成器应使用扩展的场景类型集合（见 Phase 2）。

#### 3.2 场景智能编排

根据内容主题自动选择场景组合：

```python
def _plan_popsci_scenes(topic_analysis: dict) -> list[str]:
    """科普视频场景编排策略"""
    scenes = ["character_talk"]  # hook 开场

    for concept in topic_analysis["key_concepts"]:
        scenes.append("concept")       # 概念定义
        if concept.get("needs_analogy"):
            scenes.append("analogy")   # 类比辅助

    if topic_analysis.get("relationships"):
        scenes.append("relationship")  # 关系图

    if topic_analysis.get("demo_scenarios"):
        scenes.append("demo")          # 界面演示

    if len(topic_analysis["key_concepts"]) >= 3:
        scenes.append("comparison")    # 对比总结

    scenes.append("summary_card")      # 总结
    return scenes
```

---

### Phase 4：动画引擎增强（预计 2 周）

**目标**：提升动画质量，匹配科普短视频的活泼节奏。

#### 4.1 Spring 动画系统

替换现有线性 interpolate，引入 spring 物理动画：

```typescript
// utils/spring.ts
import { spring, useCurrentFrame, useVideoConfig } from 'remotion';

interface SpringConfig {
  mass?: number;       // 质量（默认 1）
  stiffness?: number;  // 刚度（默认 100）
  damping?: number;    // 阻尼（默认 10）
  overshootClamping?: boolean;
}

// 预设动画曲线
export const SPRING_PRESETS = {
  bouncy: { mass: 0.5, stiffness: 150, damping: 8 },       // 弹性活泼
  gentle: { mass: 1, stiffness: 80, damping: 15 },         // 柔和
  snappy: { mass: 0.3, stiffness: 200, damping: 12 },      // 干脆利落
  popIn:  { mass: 0.4, stiffness: 180, damping: 10 },      // 弹出效果
};
```

#### 4.2 文字动画增强

```typescript
// 逐字弹入
export const TypewriterText: React.FC<{
  text: string;
  charDelay?: number;  // 每字延迟帧数
  style?: 'typewriter' | 'popIn' | 'slideUp';
}>;

// 关键词缩放强调
export const EmphasisText: React.FC<{
  text: string;
  emphasize: string[];  // 需要强调的词
  emphasisStyle: 'scale' | 'color' | 'glow' | 'underline';
}>;
```

#### 4.3 手绘风装饰动画

```typescript
// 手绘箭头（SVG 路径描绘动画）
export const HandDrawnArrow: React.FC<{
  from: { x: number; y: number };
  to: { x: number; y: number };
  color?: string;
  drawDuration?: number;  // 描绘时长（帧）
  style?: 'straight' | 'curved' | 'wavy';
}>;

// 圆圈标注
export const CircleHighlight: React.FC<{
  center: { x: number; y: number };
  radius: number;
  color?: string;
  drawDuration?: number;
}>;
```

---

### Phase 5：管道与界面集成（预计 1 周）

**目标**：将新风格接入现有 CLI / API / Web 界面。

#### 5.1 CLI 扩展

```bash
# 现有命令新增 --narration-style popsci 选项
theia render paper.pdf -o output.mp4 --narration-style popsci --theme popsci

# 也可通过环境变量设置
THEIA_NARRATION_STYLE=popsci THEIA_THEME=popsci theia render paper.pdf
```

#### 5.2 Web 界面扩展

在上传页面配置区新增风格选择：

```
┌─────────────────────────────────┐
│  上传 PDF 论文                  │
│  [拖拽或点击上传]               │
│                                 │
│  视频风格：                     │
│  ○ 学术严谨  ● 科普卡通        │
│                                 │
│  [🚀 开始生成]                  │
└─────────────────────────────────┘
```

---

## 五、技术实现要点

### 5.1 字体资源

| 字体 | 用途 | 许可 |
|------|------|------|
| 阿里巴巴普惠体 3.0 | 中文标题/正文 | 免费商用 |
| JetBrains Mono | 代码/等宽 | 开源 OFL |
| Noto Sans SC | 备选中文 | 开源 OFL |

字体文件放入 `packages/video/public/fonts/`，通过 `@font-face` 在 Remotion 中加载。

### 5.2 角色与装饰素材获取

素材库是科普风格视频的核心资产。以下按可行性排序列出开源/低成本方案：

#### 方案 A：开源 SVG 插画库（零成本，推荐先用）

| 资源 | 类型 | 许可证 | 适用场景 |
|------|------|--------|---------|
| [Open Peeps](https://www.openpeeps.com/) | 手绘人物插画，可混搭组合 584,688+ 种造型 | **CC0（公共领域）** | 角色替代方案，风格统一的人物插画 |
| [svgapp.ai Mascots](https://svgapp.ai/mascots/) | 预制吉祥物集合（仓鼠/水獭/熊猫等），每套 16-32 个姿势 | **MIT** | 直接用作视频吉祥物角色 |
| [unDraw](https://undraw.co/) | 场景插画，支持自定义配色 | **MIT** | 概念说明、背景装饰 |
| [Open Doodles](https://www.opendoodles.com/) | 涂鸦风格人物插画 | **CC0** | 轻松有趣的装饰元素 |
| [SVG Repo](https://svgrepo.com/) | 500,000+ SVG 图标 | **多种开源许可** | 技术图标（齿轮、灯泡、服务器等） |

**推荐组合**：svgapp.ai 吉祥物（如 Pandi 熊猫，26 个姿势）+ Open Peeps 人物 + SVG Repo 技术图标。

#### 方案 B：Lottie 动画素材（零成本，带动效）

| 资源 | 特点 | 许可证 |
|------|------|--------|
| [LottieFiles 免费动画](https://lottiefiles.com/free-animations/cartoon) | 440+ 免费卡通动画，JSON 格式 | **Lottie Simple License（允许商用）** |
| [LottieFiles 吉祥物动画](https://lottiefiles.com/free-animations/mascot) | 吉祥物专题动画 | 同上 |

Lottie 格式天然支持动画（入场、循环、交互），且体积极小（通常 < 100KB）。Remotion 通过 `@remotion/lottie` 原生支持。

**优势**：无需自己做动画，直接嵌入带动效的角色。
**劣势**：风格统一性不如定制素材，需要筛选风格一致的资源。

#### 方案 C：AI 生成定制角色（低成本，高定制）

使用 Stable Diffusion / ComfyUI 生成一套风格统一的角色素材：

1. **设计参考图**：先用 Midjourney/SD 生成一张满意的角色设计
2. **训练 LoRA**：用 8-15 张参考图训练角色 LoRA 模型（约 15 分钟）
3. **批量生成姿势**：通过 ControlNet + OpenPose 控制姿势，批量生成不同表情/动作
4. **后处理**：使用 rembg 去背景，导出为 PNG

工具链：
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)：开源 SD 工作流编辑器
- [AutoSprite](https://www.autosprite.io/)：AI 精灵表生成器，自动对齐+导出
- [rembg](https://github.com/danielgatis/rembg)：开源 AI 去背景

**优势**：完全定制、风格统一、有品牌辨识度。
**劣势**：需要一次性投入时间（约 1-2 天），需要 GPU。

#### 方案 D：委托插画师绘制（中等成本，最高品质）

在 Fiverr / 猪八戒网 / 米画师等平台定制角色设计：
- 费用：约 500-2000 元/套（15-20 个姿势）
- 周期：约 1-2 周
- 交付：PSD/AI 源文件 + PNG/SVG 导出

**推荐实施路径**：先用**方案 A + B** 快速验证效果 → 效果满意后用**方案 C 或 D** 制作定制角色。

### 5.3 性能考量

| 关注点 | 策略 |
|--------|------|
| 角色素材体积 | SVG 优先（< 50KB/个）；PNG 压缩至 < 500KB/张；Lottie JSON < 100KB/个 |
| 字体体积 | 使用子集化字体（font-spider），只包含用到的字符 |
| 渲染速度 | spring 动画在 Remotion 中是纯函数计算，无性能问题 |
| 场景复杂度 | 关系图使用 SVG 渲染，避免 Canvas |

### 5.4 兼容性保证

- 所有改动以**增量方式**进行，不修改现有学术风格组件
- 通过 `theme` 参数切换风格
- 现有 CLI / API / Web 界面保持完全向后兼容
- 新场景类型与旧场景类型共存于 `sceneComponentMap`

---

## 六、实施路线图

```
Week 1-2  ┃ Phase 1: Theme 系统 + 视觉基础
          ┃ ├─ ThemeProvider + popsci 主题配置
          ┃ ├─ BrowserFrame 组件
          ┃ ├─ 字体引入（阿里巴巴普惠体）
          ┃ └─ 彩色字幕条
          ┃
Week 3-5  ┃ Phase 2: 新场景 + 角色系统
          ┃ ├─ concept / analogy / demo / relationship 场景
          ┃ ├─ 开源素材筛选 + Character 组件
          ┃ ├─ HandDrawnArrow + CircleHighlight
          ┃ └─ comparison / summary_card / code_demo 场景
          ┃
Week 6-7  ┃ Phase 3: 脚本生成引擎
          ┃ ├─ popsci 旁白风格模板
          ┃ ├─ 扩展场景类型 Schema
          ┃ └─ 科普场景编排策略
          ┃
Week 8-9  ┃ Phase 4: 动画引擎增强
          ┃ ├─ Spring 动画系统 + 预设
          ┃ ├─ TypewriterText + EmphasisText
          ┃ └─ SVG 描线动画
          ┃
Week 10   ┃ Phase 5: 管道与界面集成
          ┃ ├─ CLI --narration-style / --theme 参数
          ┃ ├─ Web 界面风格选择
          ┃ └─ 端到端测试 + 优化
```

**总工期**：约 **10 周**（一人全职投入），可根据优先级裁剪。

### 快速出效果的最小 MVP（建议先做）

如果希望 **2 周内看到效果**，建议先集中做以下子集：

1. ✅ Theme 系统 + popsci 配色
2. ✅ BrowserFrame 容器组件
3. ✅ 中文品牌字体（阿里巴巴普惠体）
4. ✅ Spring 弹性动画替换线性动画
5. ✅ 彩色字幕条
6. ✅ 从 svgapp.ai / Open Peeps 下载一套开源角色素材
7. ✅ `concept` 场景（最基础的科普场景）

这些改动可以在**现有论文讲解流程**中通过 `--theme popsci` 切换风格即可看到变化，无需改动管道逻辑。

---

## 七、效果预期

### 优化前（当前学术风格）

```
┌─────────────────────────────────┐
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │  深蓝背景
│           ● 光球                │  + 粒子
│                                 │
│   📄 Attention is All You Need  │  白色标题
│      Vaswani et al. 2017       │  灰色作者
│                                 │
│  ▓▓▓ 半透明字幕条 ▓▓▓▓▓▓▓▓▓▓  │
└─────────────────────────────────┘
```

### 优化后（科普卡通风格）

```
┌──────────────────────────────────────┐
│  ╭─ ● ● ●  Skills到底是什么？ ─╮    │  浅青背景
│  │                              │    │
│  │   🤖  ← AI 火柴人角色       │    │  浏览器框容器
│  │   「Skills 就像是给 AI       │    │
│  │     写的工作手册」           │    │  大号粗体文字
│  │                              │    │
│  ╰──────────────────────────────╯    │
│                          👩‍💻 角色   │  角落吉祥物
│  ████ 黄色字幕条：Skills是什么  ████ │  彩色字幕
└──────────────────────────────────────┘
```

---

## 附录 A：参考资源

- [小白debug B站频道](https://space.bilibili.com/)：风格参考
- [Remotion Spring 动画文档](https://www.remotion.dev/docs/spring)
- [阿里巴巴普惠体下载](https://www.alibabafonts.com/)
- [Lottie for Remotion](https://www.remotion.dev/docs/lottie/)
- [KaTeX 文档](https://katex.org/)

## 附录 B：扩展场景 JSON Schema 示例

```json
{
  "type": "concept",
  "narration": "Skills，翻译过来就是技能。简单来说，它就是给 AI 写的一份工作手册。",
  "data": {
    "title": "Skills 是什么？",
    "definition": "给 AI 准备的标准化工作手册",
    "icon": "book",
    "keywords": ["技能", "工作手册", "标准化"]
  }
}
```

```json
{
  "type": "analogy",
  "narration": "就好比你去餐厅吃饭，菜单就是 Prompt，而厨师的烹饪技能就是 Skills。",
  "data": {
    "concept": { "label": "Skills", "description": "AI 的专业技能" },
    "analogy": { "label": "厨师技能", "description": "按菜谱做出美食" },
    "mapping": "菜单 = Prompt，厨艺 = Skills"
  }
}
```

```json
{
  "type": "relationship",
  "narration": "那 Skills、MCP、Workflow、Prompt 之间到底是什么关系呢？",
  "data": {
    "nodes": [
      { "id": "agent", "label": "Agent", "color": "#5BB5B0" },
      { "id": "skills", "label": "Skills", "color": "#F5D76E" },
      { "id": "mcp", "label": "MCP", "color": "#FF6B6B" },
      { "id": "prompt", "label": "Prompt", "color": "#A29BFE" }
    ],
    "edges": [
      { "from": "agent", "to": "skills", "label": "具备" },
      { "from": "agent", "to": "mcp", "label": "通过" },
      { "from": "agent", "to": "prompt", "label": "接收" }
    ],
    "layout": "radial"
  }
}
```
