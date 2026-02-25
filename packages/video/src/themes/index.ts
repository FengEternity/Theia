import React, { createContext, useContext } from "react";
import type { ThemeConfig, SceneStyle } from "./types";
import { academicTheme } from "./academic";
import { popsciTheme } from "./popsci";

export type { ThemeConfig, SceneStyle } from "./types";
export { academicTheme } from "./academic";
export { popsciTheme } from "./popsci";
export { baseTheme } from "./base";
export { createTheme, extendTheme, resolveSceneStyle } from "./createTheme";
export type { DeepPartial } from "./createTheme";

const themes: Record<string, ThemeConfig> = {
  academic: academicTheme,
  popsci: popsciTheme,
};

export function registerTheme(theme: ThemeConfig): void {
  themes[theme.id] = theme;
}

export function getTheme(id: string): ThemeConfig {
  return themes[id] ?? academicTheme;
}

export function getAvailableThemes(): ThemeConfig[] {
  return Object.values(themes);
}

const ThemeContext = createContext<ThemeConfig>(academicTheme);

export const ThemeProvider: React.FC<{
  theme: ThemeConfig;
  children: React.ReactNode;
}> = ({ theme, children }) => {
  return React.createElement(ThemeContext.Provider, { value: theme }, children);
};

export function useTheme(): ThemeConfig {
  return useContext(ThemeContext);
}
