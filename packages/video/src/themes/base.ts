import type { ThemeConfig } from "./types";

export const baseTheme: ThemeConfig = {
  id: "base",
  name: "Base",
  mode: "dark",

  colors: {
    background: "#0f172a",
    surface: "rgba(255,255,255,0.05)",
    primary: "#3b82f6",
    secondary: "#8b5cf6",
    accent: "#06b6d4",
    text: "#f8fafc",
    textSecondary: "#94a3b8",
    subtitle: {
      background: "rgba(0,0,0,0.55)",
      text: "rgba(255,255,255,0.7)",
      highlight: "#ffffff",
    },
    gradientStops: ["#0c1222", "#1a1f3a", "#0f172a"],
    accentRgb: "59,130,246",
  },

  fonts: {
    title: "system-ui, -apple-system, sans-serif",
    body: "system-ui, -apple-system, sans-serif",
    code: '"JetBrains Mono", "Fira Code", monospace',
  },

  animation: {
    entrance: "linear",
    exitStyle: "fade",
    speed: "normal",
  },

  decoration: {
    borderRadius: 8,
    showParticles: true,
    showOrb: true,
    backgroundStyle: "gradient",
  },

  character: {
    mascotSeries: "otter",
    showMascot: false,
    showDecorationIcons: false,
    showStickers: false,
  },

  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 40,
    xxl: 64,
  },

  shadow: {
    sm: "0 1px 3px rgba(0,0,0,0.12)",
    md: "0 4px 12px rgba(0,0,0,0.2)",
    lg: "0 10px 40px rgba(0,0,0,0.3)",
    image: "0 10px 50px rgba(0,0,0,0.5)",
  },

  transition: {
    fast: 10,
    normal: 20,
    slow: 35,
  },

  layout: {
    contentMaxWidth: 1600,
    cardPadding: 40,
    sectionGap: 30,
  },

  sceneStyles: {},
};
