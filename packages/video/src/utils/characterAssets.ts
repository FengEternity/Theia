import { staticFile } from "remotion";

const CHAR_BASE = "characters";

export type MascotSeries = "otter" | "pandi";
export type MascotPose =
  | "explaining"
  | "happy"
  | "surprised"
  | "talking"
  | "teamwork"
  | "thinking"
  | "pointing"
  | "reading"
  | "working";

export type AIFigure = "robot-teacher" | "robot-thinking" | "robot-happy";
export type IconName = "lightbulb" | "gear" | "code" | "brain" | "rocket";
export type ArrowName = "curved-right" | "wavy-down" | "straight-right";
export type BubbleName = "speech" | "thought" | "exclaim";
export type StickerName = "star" | "checkmark" | "question" | "heart" | "warning";

const MASCOT_FILES: Record<MascotSeries, Partial<Record<MascotPose, string>>> = {
  otter: {
    explaining: "mascot/explaining.svg",
    happy: "mascot/happy.svg",
    surprised: "mascot/surprised.svg",
    talking: "mascot/talking.svg",
    teamwork: "mascot/teamwork.svg",
    thinking: "mascot/thinking.svg",
    pointing: "mascot/pointing.svg",
  },
  pandi: {
    explaining: "mascot/pandi-explaining.svg",
    reading: "mascot/pandi-reading.svg",
    working: "mascot/pandi-working.svg",
    talking: "mascot/pandi-talking.svg",
    teamwork: "mascot/pandi-teamwork.svg",
    thinking: "mascot/pandi-thinking.svg",
  },
};

export function getMascot(series: MascotSeries, pose: MascotPose): string {
  const file = MASCOT_FILES[series]?.[pose] ?? MASCOT_FILES[series]?.explaining;
  if (!file) return "";
  return staticFile(`${CHAR_BASE}/${file}`);
}

export function getAIFigure(figure: AIFigure): string {
  return staticFile(`${CHAR_BASE}/ai-figure/${figure}.svg`);
}

export function getIcon(name: IconName): string {
  return staticFile(`${CHAR_BASE}/decorations/icons/${name}.svg`);
}

export function getArrow(name: ArrowName): string {
  return staticFile(`${CHAR_BASE}/decorations/arrows/${name}.svg`);
}

export function getBubble(name: BubbleName): string {
  return staticFile(`${CHAR_BASE}/decorations/bubbles/${name}.svg`);
}

export function getSticker(name: StickerName): string {
  return staticFile(`${CHAR_BASE}/decorations/stickers/${name}.svg`);
}

const EXPRESSION_TO_POSE: Record<string, MascotPose> = {
  explaining: "explaining",
  talking: "talking",
  thinking: "thinking",
  happy: "happy",
  surprised: "surprised",
  pointing: "pointing",
  reading: "reading",
  working: "working",
  teamwork: "teamwork",
};

export function expressionToPose(expression: string): MascotPose {
  return EXPRESSION_TO_POSE[expression] ?? "explaining";
}

const SCENE_ICONS: Record<string, IconName> = {
  concept: "lightbulb",
  analogy: "brain",
  relationship: "gear",
  demo: "code",
  code_demo: "code",
  comparison: "gear",
  summary_card: "rocket",
  character_talk: "lightbulb",
};

export function getSceneIcon(sceneType: string): string {
  const name = SCENE_ICONS[sceneType];
  return name ? getIcon(name) : "";
}
