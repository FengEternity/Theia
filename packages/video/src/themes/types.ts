export interface SubtitleColors {
  background: string;
  text: string;
  highlight: string;
}

export interface ThemeColors {
  background: string;
  surface: string;
  primary: string;
  secondary: string;
  accent: string;
  text: string;
  textSecondary: string;
  subtitle: SubtitleColors;
  gradientStops: [string, string, string];
  accentRgb: string;
}

export interface ThemeFonts {
  title: string;
  body: string;
  code: string;
}

export interface ThemeAnimation {
  entrance: "linear" | "spring" | "bounce";
  exitStyle: "fade" | "scale" | "slide";
  speed: "slow" | "normal" | "fast";
}

export interface ThemeDecoration {
  borderRadius: number;
  showParticles: boolean;
  showOrb: boolean;
  backgroundStyle: "gradient" | "flat" | "pattern";
}

export interface ThemeCharacter {
  mascotSeries: "otter" | "pandi";
  showMascot: boolean;
  showDecorationIcons: boolean;
  showStickers: boolean;
}

export interface ThemeSpacing {
  xs: number;
  sm: number;
  md: number;
  lg: number;
  xl: number;
  xxl: number;
}

export interface ThemeShadow {
  sm: string;
  md: string;
  lg: string;
  image: string;
}

export interface ThemeTransition {
  fast: number;
  normal: number;
  slow: number;
}

export interface ThemeLayout {
  contentMaxWidth: number;
  cardPadding: number;
  sectionGap: number;
}

export interface SceneStyle {
  gradientStops: [string, string, string];
  accentRgb: string;
  accentColor: string;
  secondaryColor: string;
  accentGradient: string;
  bodyTextColor: string;
  imageShadow: string;
  imageBorder: string;
}

export interface ThemeConfig {
  id: string;
  name: string;
  mode: "dark" | "light";
  colors: ThemeColors;
  fonts: ThemeFonts;
  animation: ThemeAnimation;
  decoration: ThemeDecoration;
  character: ThemeCharacter;
  spacing: ThemeSpacing;
  shadow: ThemeShadow;
  transition: ThemeTransition;
  layout: ThemeLayout;
  sceneStyles: Record<string, Partial<SceneStyle>>;
}
