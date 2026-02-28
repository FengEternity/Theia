import { z } from "zod";

export const SceneType = z.enum([
  "title",
  "overview",
  "method",
  "formula",
  "figure",
  "result",
  "conclusion",
  "concept",
  "analogy",
  "relationship",
  "demo",
  "comparison",
  "character_talk",
  "summary_card",
  "code_demo",
]);
export type SceneType = z.infer<typeof SceneType>;

export const TitleData = z.object({
  title: z.string(),
  authors: z.array(z.string()).default([]),
  year: z.number().nullable().default(null),
});
export type TitleData = z.infer<typeof TitleData>;

export const OverviewData = z.object({
  problem: z.string(),
  contributions: z.array(z.string()).default([]),
});
export type OverviewData = z.infer<typeof OverviewData>;

export const MethodData = z.object({
  summary: z.string(),
  steps: z.array(z.string()).default([]),
  formulas: z.array(z.string()).default([]),
});
export type MethodData = z.infer<typeof MethodData>;

export const FormulaData = z.object({
  formula: z.string(),
  explanation: z.string().default(""),
  title: z.string().default(""),
});
export type FormulaData = z.infer<typeof FormulaData>;

export const FigureData = z.object({
  figurePath: z.string().default(""),
  caption: z.string().default(""),
  description: z.string().default(""),
});
export type FigureData = z.infer<typeof FigureData>;

export const ResultData = z.object({
  datasets: z.array(z.string()).default([]),
  metrics: z.array(z.string()).default([]),
  findings: z.string(),
});
export type ResultData = z.infer<typeof ResultData>;

export const ConclusionData = z.object({
  conclusion: z.string(),
  contributions: z.array(z.string()).default([]),
});
export type ConclusionData = z.infer<typeof ConclusionData>;

export const WordTiming = z.object({
  text: z.string(),
  offsetMs: z.number(),
  durationMs: z.number(),
});
export type WordTiming = z.infer<typeof WordTiming>;

export const AnimationPhase = z.object({
  startMs: z.number(),
  endMs: z.number(),
  attentionMode: z.string().default("synced"),
  elementsToShow: z.array(z.string()).default([]),
  highlightElement: z.string().nullable().default(null),
  transitionType: z.string().default("fade_in"),
});
export type AnimationPhase = z.infer<typeof AnimationPhase>;

export const ManimClip = z.object({
  clipPath: z.string(),
  startMs: z.number().default(0),
  durationMs: z.number(),
  position: z.string().default("center"),
  opacity: z.number().default(1.0),
});
export type ManimClip = z.infer<typeof ManimClip>;

export const Scene = z.object({
  type: SceneType,
  durationInFrames: z.number().int().positive(),
  narration: z.string(),
  audioFile: z.string().nullable().default(null),
  data: z.record(z.string(), z.unknown()),
  wordTimings: z.array(WordTiming).default([]),
  choreography: z.array(AnimationPhase).default([]),
  manimClips: z.array(ManimClip).default([]),
});
export type Scene = z.infer<typeof Scene>;

export const VideoMeta = z.object({
  fps: z.number().int().default(30),
  width: z.number().int().default(1920),
  height: z.number().int().default(1080),
  theme: z.string().default("academic"),
});
export type VideoMeta = z.infer<typeof VideoMeta>;

export const ConceptData = z.object({
  title: z.string(),
  definition: z.string(),
  icon: z.string().default(""),
  keywords: z.array(z.string()).default([]),
});
export type ConceptData = z.infer<typeof ConceptData>;

export const AnalogyData = z.object({
  concept: z.object({
    label: z.string(),
    description: z.string(),
  }),
  analogy: z.object({
    label: z.string(),
    description: z.string(),
  }),
  mapping: z.string().default(""),
});
export type AnalogyData = z.infer<typeof AnalogyData>;

export const RelationshipNode = z.object({
  id: z.string(),
  label: z.string(),
  icon: z.string().default(""),
  color: z.string().default(""),
  description: z.string().default(""),
});

export const RelationshipEdge = z.object({
  from: z.string(),
  to: z.string(),
  label: z.string().default(""),
  style: z.enum(["solid", "dashed", "arrow"]).default("arrow"),
});

export const RelationshipData = z.object({
  nodes: z.array(RelationshipNode),
  edges: z.array(RelationshipEdge),
  layout: z.enum(["tree", "radial", "flow"]).default("radial"),
});
export type RelationshipData = z.infer<typeof RelationshipData>;

export const DemoStep = z.object({
  action: z.enum(["type", "response", "highlight", "scroll"]),
  content: z.string(),
  delay: z.number().default(0),
});

export const DemoData = z.object({
  interface: z.enum(["chat", "terminal", "code-editor", "browser"]),
  steps: z.array(DemoStep),
});
export type DemoData = z.infer<typeof DemoData>;

export const ComparisonItem = z.object({
  name: z.string(),
  features: z.record(z.string(), z.string()),
});

export const ComparisonData = z.object({
  items: z.array(ComparisonItem),
  featureLabels: z.array(z.string()).default([]),
});
export type ComparisonData = z.infer<typeof ComparisonData>;

export const CharacterTalkData = z.object({
  character: z.enum(["mascot", "ai-figure"]).default("mascot"),
  expression: z.string().default("explaining"),
  text: z.string(),
  bubbleStyle: z.enum(["speech", "thought"]).default("speech"),
});
export type CharacterTalkData = z.infer<typeof CharacterTalkData>;

export const SummaryCardData = z.object({
  title: z.string().default("总结"),
  points: z.array(z.string()),
});
export type SummaryCardData = z.infer<typeof SummaryCardData>;

export const CodeDemoData = z.object({
  language: z.string().default("python"),
  code: z.string(),
  highlights: z.array(z.number()).default([]),
  filename: z.string().default(""),
});
export type CodeDemoData = z.infer<typeof CodeDemoData>;

export const VideoScript = z.object({
  meta: VideoMeta,
  scenes: z.array(Scene),
});
export type VideoScript = z.infer<typeof VideoScript>;
