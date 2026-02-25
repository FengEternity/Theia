import { useVideoConfig } from "remotion";

/**
 * 根据视频尺寸动态计算缩放系数和布局方向。
 *
 * 横屏 1920×1080: scale=1.0
 * 竖屏 1080×1920: scale=1.0（不再缩小，保证字号够大）
 */
export function useScale() {
  const { width, height } = useVideoConfig();
  const isPortrait = height > width;
  const isSquare = Math.abs(width - height) < 100;

  const scale = isPortrait || isSquare
    ? Math.max(0.8, width / 1080)
    : Math.max(0.8, width / 1920);

  const s = (px: number) => Math.round(px * scale);

  const padH = isPortrait ? s(32) : s(50);
  const padV = isPortrait ? Math.round(height * 0.12) : s(50);

  return {
    width,
    height,
    isPortrait,
    isSquare,
    scale,
    s,
    padH,
    padV,
    pad: `${padV}px ${padH}px`,
  };
}
