import { createTheme } from "./createTheme";

export const popsciTheme = createTheme({
  id: "popsci",
  name: "科普卡通",
  mode: "light",

  colors: {
    background: "#F0F9F7",
    surface: "#FFFFFF",
    primary: "#5BB5B0",
    secondary: "#F5D76E",
    accent: "#FF6B6B",
    text: "#2D3436",
    textSecondary: "#636E72",
    subtitle: {
      background: "#F5D76E",
      text: "#2D3436",
      highlight: "#E17055",
    },
    gradientStops: ["#F0F9F7", "#E8F5F3", "#F0F9F7"],
    accentRgb: "91,181,176",
  },

  fonts: {
    title:
      '"Noto Sans SC", "Alibaba PuHuiTi 3.0 Bold", "Source Han Sans CN Bold", system-ui, sans-serif',
    body: '"Noto Sans SC", "Alibaba PuHuiTi 3.0", "Source Han Sans CN", system-ui, sans-serif',
  },

  animation: {
    entrance: "spring",
    exitStyle: "scale",
    speed: "fast",
  },

  decoration: {
    borderRadius: 16,
    showParticles: false,
    showOrb: false,
    backgroundStyle: "flat",
  },

  character: {
    mascotSeries: "pandi",
    showMascot: true,
    showDecorationIcons: true,
    showStickers: true,
  },

  shadow: {
    sm: "0 2px 8px rgba(0,0,0,0.06)",
    md: "0 4px 16px rgba(0,0,0,0.1)",
    lg: "0 8px 30px rgba(0,0,0,0.12)",
    image: "0 8px 32px rgba(0,0,0,0.1)",
  },
});
