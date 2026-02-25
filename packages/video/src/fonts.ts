/**
 * 字体加载与注册。
 *
 * 在 Remotion 中加载自定义字体（通过 public/ 目录的静态文件）。
 *
 * 已内置字体文件（packages/video/public/fonts/）：
 * - Noto Sans SC（Google 开源中文黑体）
 * - JetBrains Mono（代码等宽字体）
 */

import { staticFile } from "remotion";

function buildFontFaces(): string {
  return `
@font-face {
  font-family: "Noto Sans SC";
  src: url("${staticFile("fonts/NotoSansSC-Regular.ttf")}") format("truetype");
  font-weight: 400;
  font-style: normal;
  font-display: block;
}

@font-face {
  font-family: "Noto Sans SC";
  src: url("${staticFile("fonts/NotoSansSC-Medium.ttf")}") format("truetype");
  font-weight: 500;
  font-style: normal;
  font-display: block;
}

@font-face {
  font-family: "Noto Sans SC";
  src: url("${staticFile("fonts/NotoSansSC-SemiBold.ttf")}") format("truetype");
  font-weight: 600;
  font-style: normal;
  font-display: block;
}

@font-face {
  font-family: "Noto Sans SC";
  src: url("${staticFile("fonts/NotoSansSC-Bold.ttf")}") format("truetype");
  font-weight: 700;
  font-style: normal;
  font-display: block;
}

@font-face {
  font-family: "JetBrains Mono";
  src: url("${staticFile("fonts/JetBrainsMono-Regular.woff2")}") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: block;
}

@font-face {
  font-family: "JetBrains Mono";
  src: url("${staticFile("fonts/JetBrainsMono-Bold.woff2")}") format("woff2");
  font-weight: 700;
  font-style: normal;
  font-display: block;
}
`;
}

let injected = false;

export function ensureFontsLoaded(): void {
  if (injected || typeof document === "undefined") return;
  const style = document.createElement("style");
  style.textContent = buildFontFaces();
  document.head.appendChild(style);
  injected = true;
}
