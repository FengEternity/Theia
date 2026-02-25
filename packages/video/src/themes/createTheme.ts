import type { ThemeConfig, SceneStyle } from "./types";
import { baseTheme } from "./base";

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends (infer U)[]
    ? T[P]
    : T[P] extends object
      ? DeepPartial<T[P]>
      : T[P];
};

function deepMerge<T extends Record<string, unknown>>(
  base: T,
  overrides: DeepPartial<T>,
): T {
  const result = { ...base };
  for (const key in overrides) {
    const val = overrides[key];
    if (val === undefined) continue;
    if (
      typeof val === "object" &&
      val !== null &&
      !Array.isArray(val) &&
      typeof result[key] === "object" &&
      result[key] !== null &&
      !Array.isArray(result[key])
    ) {
      result[key] = deepMerge(
        result[key] as Record<string, unknown>,
        val as DeepPartial<Record<string, unknown>>,
      ) as T[Extract<keyof T, string>];
    } else {
      (result as Record<string, unknown>)[key] = val;
    }
  }
  return result;
}

export function createTheme(overrides: DeepPartial<ThemeConfig>): ThemeConfig {
  return deepMerge(baseTheme as unknown as Record<string, unknown>, overrides as DeepPartial<Record<string, unknown>>) as unknown as ThemeConfig;
}

export function extendTheme(
  parent: ThemeConfig,
  overrides: DeepPartial<ThemeConfig>,
): ThemeConfig {
  return deepMerge(parent as unknown as Record<string, unknown>, overrides as DeepPartial<Record<string, unknown>>) as unknown as ThemeConfig;
}

export function resolveSceneStyle(
  theme: ThemeConfig,
  sceneType: string,
): SceneStyle {
  const defaults: SceneStyle = {
    gradientStops: theme.colors.gradientStops,
    accentRgb: theme.colors.accentRgb,
    accentColor: theme.colors.primary,
    secondaryColor: theme.colors.secondary,
    accentGradient: `linear-gradient(90deg, ${theme.colors.primary}, ${theme.colors.secondary})`,
    bodyTextColor: theme.colors.text,
    imageShadow: theme.shadow.image,
    imageBorder:
      theme.mode === "dark"
        ? "1px solid rgba(255,255,255,0.08)"
        : `2px solid ${theme.colors.primary}20`,
  };

  const override = theme.sceneStyles[sceneType];
  if (!override) return defaults;

  return { ...defaults, ...override };
}
