import "katex/dist/katex.min.css";
import { interpolate, useCurrentFrame, useVideoConfig, spring } from "remotion";
import katex from "katex";
import { useScale } from "../hooks/useScale";
import { useTheme } from "../themes";

function renderKatex(latex: string): { html: string; ok: boolean } {
  try {
    let s = latex.trim();
    if (s.startsWith("\\[")) s = s.slice(2);
    if (s.endsWith("\\]")) s = s.slice(0, -2);
    if (s.startsWith("$$")) s = s.slice(2);
    if (s.endsWith("$$")) s = s.slice(0, -2);
    return {
      html: katex.renderToString(s.trim(), {
        displayMode: true,
        throwOnError: false,
        output: "html",
      }),
      ok: true,
    };
  } catch {
    return { html: latex, ok: false };
  }
}

type OverlayPosition = "top" | "bottom" | "top-right" | "bottom-right";

export const FormulaOverlay: React.FC<{
  formula: string;
  position?: OverlayPosition;
  delayFrames?: number;
  showLabel?: string;
}> = ({ formula, position = "top-right", delayFrames = 15, showLabel }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useScale();
  const theme = useTheme();

  const rendered = renderKatex(formula);
  const progress = spring({
    frame: frame - delayFrames,
    fps,
    config: { damping: 15, stiffness: 120 },
  });

  if (progress < 0.01) return null;

  const slideOffset = interpolate(progress, [0, 1], [20, 0]);
  const positionStyle = getPositionStyle(position, s);
  const formulaLen = formula.length;
  const fontSize = s(formulaLen > 80 ? 24 : formulaLen > 40 ? 28 : 32);

  return (
    <div
      style={{
        ...positionStyle,
        opacity: progress,
        transform: `translateY(${slideOffset}px)`,
      }}
    >
      <div
        style={{
          background: "rgba(10, 10, 30, 0.75)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          border: `1px solid rgba(255, 255, 255, 0.12)`,
          borderRadius: s(16),
          padding: `${s(16)}px ${s(24)}px`,
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
        }}
      >
        {showLabel && (
          <div
            style={{
              color: theme.colors.primary,
              fontSize: s(18),
              fontWeight: 700,
              textTransform: "uppercase" as const,
              letterSpacing: 2,
              marginBottom: s(10),
              fontFamily: theme.fonts.title,
              textShadow: "0 1px 4px rgba(0,0,0,0.6)",
            }}
          >
            {showLabel}
          </div>
        )}
        {rendered.ok ? (
          <span
            style={{
              fontSize,
              color: "#ffffff",
              display: "block",
            }}
            dangerouslySetInnerHTML={{ __html: rendered.html }}
          />
        ) : (
          <span
            style={{
              color: "#ffffff",
              fontSize,
              fontFamily: "'Times New Roman', serif",
              fontStyle: "italic",
            }}
          >
            {formula}
          </span>
        )}
      </div>
    </div>
  );
};

function getPositionStyle(
  position: OverlayPosition,
  s: (px: number) => number,
): React.CSSProperties {
  const base: React.CSSProperties = {
    position: "absolute",
    zIndex: 10,
    maxWidth: "45%",
  };

  switch (position) {
    case "top":
      return { ...base, top: s(40), left: "50%", transform: "translateX(-50%)", maxWidth: "80%" };
    case "bottom":
      return { ...base, bottom: s(90), left: "50%", transform: "translateX(-50%)", maxWidth: "80%" };
    case "top-right":
      return { ...base, top: s(50), right: s(50) };
    case "bottom-right":
      return { ...base, bottom: s(90), right: s(50) };
    default:
      return { ...base, top: s(50), right: s(50) };
  }
}
