import { createTheme } from "./createTheme";

export const academicTheme = createTheme({
  id: "academic",
  name: "学术严谨",
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

  shadow: {
    image: "0 10px 50px rgba(0,0,0,0.5)",
  },

  sceneStyles: {
    overview: {
      gradientStops: ["#0a1628", "#132744", "#0d1b30"],
      accentRgb: "34,197,94",
      secondaryColor: "#8b5cf6",
      bodyTextColor: "#cbd5e1",
    },
    method: {
      gradientStops: ["#100e24", "#1a1640", "#0f1230"],
      secondaryColor: "#8b5cf6",
    },
    formula: {
      gradientStops: ["#0c1625", "#141e3e", "#0e1a2e"],
      accentRgb: "139,92,246",
      accentColor: "#8b5cf6",
      bodyTextColor: "#cbd5e1",
    },
    figure: {
      gradientStops: ["#0a0f20", "#15193a", "#0d1328"],
      imageShadow: "0 10px 50px rgba(0,0,0,0.5)",
      imageBorder: "1px solid rgba(255,255,255,0.08)",
    },
    result: {
      gradientStops: ["#0a1418", "#0f2420", "#0c1a1e"],
      accentRgb: "34,197,94",
      accentColor: "#10b981",
      accentGradient: "linear-gradient(180deg, #10b981, #059669)",
    },
    conclusion: {
      gradientStops: ["#121014", "#201810", "#14100e"],
      accentRgb: "245,158,11",
      accentColor: "#f59e0b",
      accentGradient: "linear-gradient(90deg, #f59e0b, #ef4444)",
      bodyTextColor: "#fcd34d",
    },
  },
});
