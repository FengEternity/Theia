import "katex/dist/katex.min.css";
import katex from "katex";
import { Img, interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import type { MethodData, AnimationPhase, ManimClip } from "../types/script";
import { DynamicBackground } from "../components/DynamicBackground";
import { FormulaOverlay } from "../components/FormulaOverlay";
import { ManimClipPlayer } from "../components/ManimClip";
import { useChoreography } from "../hooks/useChoreography";
import { useScale } from "../hooks/useScale";
import { useTheme, resolveSceneStyle } from "../themes";
import { getIcon } from "../utils/characterAssets";

function renderFormulaHtml(latex: string): string | null {
  try {
    let s = latex.trim();
    if (s.startsWith("\\[")) s = s.slice(2);
    if (s.endsWith("\\]")) s = s.slice(0, -2);
    if (s.startsWith("$$")) s = s.slice(2);
    if (s.endsWith("$$")) s = s.slice(0, -2);
    return katex.renderToString(s.trim(), {
      displayMode: false,
      throwOnError: false,
      output: "html",
    });
  } catch {
    return null;
  }
}

export const MethodScene: React.FC<{
  data: Record<string, unknown>;
  durationInFrames: number;
  choreography?: AnimationPhase[];
}> = ({ data, durationInFrames, choreography }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s, pad, isPortrait } = useScale();
  const theme = useTheme();
  const scene = resolveSceneStyle(theme, "method");
  const choreo = useChoreography(choreography);
  const { summary, steps } = data as unknown as MethodData;
  const manimClips = ((data as Record<string, unknown>).manimClips ?? []) as ManimClip[];
  const hasManim = manimClips.length > 0;
  const formulas = ((data as Record<string, unknown>).formulas ?? []) as string[];

  const headerOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const summaryLen = (summary || "").length;
  const summaryFontSize = s(summaryLen > 150 ? 36 : summaryLen > 80 ? 40 : 44);
  const stepCount = (steps || []).length;
  const stepFontSize = s(stepCount > 4 ? 32 : stepCount > 2 ? 36 : 38);
  const useGrid = !isPortrait && stepCount > 2;

  const showDecorations = theme.character.showDecorationIcons;
  const primaryColor = theme.colors.primary;
  const secondaryColor = scene.secondaryColor;

  return (
    <DynamicBackground
      colors={scene.gradientStops}
      accentColor={theme.colors.accentRgb}
      particleCount={theme.decoration.showParticles ? undefined : 0}
      showOrb={theme.decoration.showOrb}
      mode={theme.decoration.backgroundStyle === "flat" ? "flat" : undefined}
    >
      {/* Manim 动画底层（当有预渲染片段时） */}
      {hasManim && manimClips.map((clip, i) => (
        <ManimClipPlayer key={`mc-${i}`} clip={clip} durationInFrames={durationInFrames} />
      ))}

      {/* 公式浮层：仅在有 Manim 动画时作为叠加层显示 */}
      {hasManim && formulas.length > 0 && (
        <FormulaOverlay
          formula={formulas[0]}
          position="top-right"
          delayFrames={15}
          showLabel="Key Formula"
        />
      )}

      <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", flexDirection: "column", justifyContent: isPortrait ? "center" : "flex-start", padding: pad, fontFamily: theme.fonts.body, ...(hasManim ? { maxWidth: "55%", background: "linear-gradient(90deg, rgba(10,10,30,0.88) 0%, rgba(10,10,30,0.5) 80%, transparent 100%)" } : {}) }}>
        <div style={{ display: "flex", alignItems: "center", gap: s(14), marginBottom: s(20), opacity: headerOpacity, flexShrink: 0 }}>
          {showDecorations ? (
            <Img src={getIcon("gear")} style={{ width: s(32), height: s(32) }} />
          ) : (
            <div style={{ width: s(5), height: s(32), background: `linear-gradient(180deg, ${primaryColor}, ${secondaryColor})`, borderRadius: 3 }} />
          )}
          <span style={{ color: primaryColor, fontSize: s(30), fontWeight: 600, fontFamily: theme.fonts.title, textTransform: "uppercase" as const, letterSpacing: 4 }}>方法论</span>
        </div>

        <p style={{ color: theme.colors.text, fontSize: summaryFontSize, fontFamily: theme.fonts.body, lineHeight: 1.6, maxWidth: "95%", marginBottom: s(30), opacity: interpolate(frame, [10, 35], [0, 1], { extrapolateRight: "clamp" }), transform: `translateY(${interpolate(frame, [10, 35], [20, 0], { extrapolateRight: "clamp" })}px)`, flexShrink: 0 }}>
          {summary}
        </p>

        <div style={{ display: "grid", gridTemplateColumns: useGrid ? "1fr 1fr" : "1fr", gap: `${s(18)}px ${s(40)}px`, alignContent: "start" }}>
          {steps?.map((step, i) => {
            const stepId = `step_${i}`;
            const isRevealed = choreo.hasChoreography ? choreo.isElementVisible(stepId) : true;
            const delay = 35 + i * 18;
            const prog = choreo.hasChoreography
              ? (isRevealed ? 1 : 0)
              : spring({ frame: frame - delay, fps, config: { damping: 14 } });
            const highlightStart = delay + 10;
            const highlightEnd = highlightStart + Math.max(durationInFrames / stepCount - 18, 30);
            const isActive = choreo.hasChoreography
              ? choreo.isElementHighlighted(stepId)
              : (frame >= highlightStart && frame < highlightEnd);
            const bgAlpha = isActive ? 0.12 : 0.04;
            const borderAlpha = isActive ? 0.4 : 0.1;
            const pairedFormula = !hasManim && formulas[i] ? renderFormulaHtml(formulas[i]) : null;

            return (
              <div key={i} style={{
                display: "flex",
                alignItems: "flex-start",
                gap: s(16),
                opacity: prog,
                transform: `translateX(${(1 - prog) * 40}px)`,
                background: `${primaryColor}${Math.round(bgAlpha * 255).toString(16).padStart(2, "0")}`,
                border: `1px solid ${primaryColor}${Math.round(borderAlpha * 255).toString(16).padStart(2, "0")}`,
                borderRadius: s(14),
                padding: `${s(14)}px ${s(20)}px`,
              }}>
                <div style={{
                  width: s(44),
                  height: s(44),
                  borderRadius: s(12),
                  background: `linear-gradient(135deg, ${primaryColor}, ${secondaryColor})`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#fff",
                  fontSize: s(20),
                  fontWeight: 700,
                  flexShrink: 0,
                  boxShadow: isActive ? `0 0 ${s(12)}px ${primaryColor}66` : "none",
                }}>
                  {i + 1}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ color: isActive ? theme.colors.text : theme.colors.textSecondary, fontSize: stepFontSize, fontFamily: theme.fonts.body, lineHeight: 1.5, marginTop: s(4) }}>{step}</p>
                  {pairedFormula && (
                    <div style={{
                      marginTop: s(10),
                      padding: `${s(8)}px ${s(14)}px`,
                      background: "rgba(255,255,255,0.06)",
                      borderRadius: s(8),
                      borderLeft: `3px solid ${primaryColor}`,
                      overflow: "hidden",
                    }}>
                      <span
                        style={{ fontSize: s(26), color: "#e0e0e0", display: "block" }}
                        dangerouslySetInnerHTML={{ __html: pairedFormula }}
                      />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* 多余的公式（步骤数少于公式数时）显示在底部 */}
        {!hasManim && formulas.length > (steps?.length ?? 0) && (
          <div style={{ marginTop: s(24), display: "flex", flexWrap: "wrap", gap: s(16), opacity: interpolate(frame, [40, 60], [0, 1], { extrapolateRight: "clamp" }) }}>
            {formulas.slice(steps?.length ?? 0).map((f, j) => {
              const html = renderFormulaHtml(f);
              if (!html) return null;
              return (
                <div key={`extra-f-${j}`} style={{
                  padding: `${s(10)}px ${s(18)}px`,
                  background: "rgba(255,255,255,0.06)",
                  borderRadius: s(10),
                  border: `1px solid rgba(255,255,255,0.1)`,
                }}>
                  <span
                    style={{ fontSize: s(28), color: "#e0e0e0", display: "block" }}
                    dangerouslySetInnerHTML={{ __html: html }}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </DynamicBackground>
  );
};
