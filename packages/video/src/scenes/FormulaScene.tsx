import "katex/dist/katex.min.css";
import { interpolate, useCurrentFrame } from "remotion";
import katex from "katex";
import { DynamicBackground } from "../components/DynamicBackground";
import { InlineLatex } from "../components/InlineLatex";
import { FormulaOverlay } from "../components/FormulaOverlay";
import { ManimClipPlayer } from "../components/ManimClip";
import { useChoreography } from "../hooks/useChoreography";
import { useScale } from "../hooks/useScale";
import { useTheme, resolveSceneStyle } from "../themes";
import type { AnimationPhase, ManimClip } from "../types/script";

function cleanLatex(latex: string): string {
  let s = latex.trim();
  if (s.startsWith("\\[")) s = s.slice(2);
  if (s.endsWith("\\]")) s = s.slice(0, -2);
  if (s.startsWith("$$")) s = s.slice(2);
  if (s.endsWith("$$")) s = s.slice(0, -2);
  return s.trim();
}

function renderKatex(latex: string): { html: string; ok: boolean } {
  try {
    const cleaned = cleanLatex(latex);
    return { html: katex.renderToString(cleaned, { displayMode: true, throwOnError: false, output: "html" }), ok: true };
  } catch {
    return { html: latex, ok: false };
  }
}

function splitFormulaParts(formula: string): string[] {
  if (formula.includes("=")) {
    const eqIdx = formula.indexOf("=");
    return [formula.slice(0, eqIdx + 1).trim(), formula.trim()];
  }
  if (formula.length > 50) {
    const mid = Math.floor(formula.length / 2);
    let splitAt = formula.indexOf("+", mid - 15);
    if (splitAt < 0) splitAt = formula.indexOf("-", mid - 15);
    if (splitAt > 0 && splitAt < formula.length - 5) {
      return [formula.slice(0, splitAt).trim(), formula.trim()];
    }
  }
  return [formula];
}

export const FormulaScene: React.FC<{
  data: Record<string, unknown>;
  durationInFrames: number;
  choreography?: AnimationPhase[];
}> = ({ data, durationInFrames, choreography }) => {
  const frame = useCurrentFrame();
  const { s, pad, isPortrait } = useScale();
  const theme = useTheme();
  const scene = resolveSceneStyle(theme, "formula");
  const choreo = useChoreography(choreography);
  const { formula, explanation, title } = data as { formula: string; explanation: string; title: string };
  const manimClips = ((data as Record<string, unknown>).manimClips ?? []) as ManimClip[];
  const hasManim = manimClips.length > 0;

  const parts = splitFormulaParts(formula || "");
  const isMultiStep = parts.length > 1;

  const step1Opacity = interpolate(frame, [0, 35], [0, 1], { extrapolateRight: "clamp" });
  const step1Scale = interpolate(frame, [0, 35], [0.92, 1], { extrapolateRight: "clamp" });
  const step2Opacity = isMultiStep
    ? interpolate(frame, [40, 70], [0, 1], { extrapolateRight: "clamp" })
    : 1;
  const step2Scale = isMultiStep
    ? interpolate(frame, [40, 70], [0.95, 1], { extrapolateRight: "clamp" })
    : 1;
  const defaultTextDelay = isMultiStep ? 75 : 25;
  const textDelay = choreo.hasChoreography ? 0 : defaultTextDelay;
  const textOpacity = choreo.hasChoreography
    ? (choreo.isElementVisible("explanation") ? interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" }) : 0)
    : interpolate(frame, [defaultTextDelay, defaultTextDelay + 30], [0, 1], { extrapolateRight: "clamp" });

  const currentFormula = isMultiStep && frame < 40 ? parts[0] : parts[parts.length - 1];
  const currentScale = isMultiStep && frame < 40 ? step1Scale : step2Scale;
  const currentOpacity = isMultiStep && frame < 40 ? step1Opacity : step2Opacity;

  const rendered = renderKatex(currentFormula);
  const formulaLen = (currentFormula || "").length;
  const formulaFontSize = s(formulaLen > 80 ? 38 : formulaLen > 50 ? 42 : formulaLen > 30 ? 46 : 52);
  const explainLen = (explanation || "").length;
  const explainFontSize = s(explainLen > 150 ? 34 : explainLen > 80 ? 38 : 42);
  const hasExplanation = explanation && explanation.length > 0;
  const flexDir = isPortrait ? "column" as const : "row" as const;

  const formulaAccent = scene.accentColor;
  const formulaBg = `${formulaAccent}0F`;
  const formulaBorder = `${formulaAccent}33`;
  const glowOpacity = 0.1 + Math.sin(frame * 0.04) * 0.05;

  return (
    <DynamicBackground
      colors={scene.gradientStops}
      accentColor={scene.accentRgb}
      particleCount={theme.decoration.showParticles ? 10 : 0}
      showOrb={theme.decoration.showOrb}
      mode={theme.decoration.backgroundStyle === "flat" ? "flat" : undefined}
    >
      <div style={{ position: "absolute", top: "40%", left: "30%", width: s(500), height: s(500), borderRadius: "50%", background: `radial-gradient(circle, rgba(${scene.accentRgb},${glowOpacity}) 0%, transparent 70%)`, transform: "translate(-50%,-50%)" }} />

      {hasManim ? (
        <>
          {/* 底层: Manim 语义可视化动画 */}
          {manimClips.map((clip, i) => (
            <ManimClipPlayer key={i} clip={{...clip, position: "center"}} durationInFrames={durationInFrames} />
          ))}

          {/* 上层: KaTeX 精确公式浮层（玻璃面板） */}
          {formula && (
            <FormulaOverlay
              formula={formula}
              position={isPortrait ? "top" : "top-right"}
              delayFrames={10}
              showLabel={title || undefined}
            />
          )}

          {/* 底部: 解释文字（始终显示，帮助理解公式） */}
          {hasExplanation && (
            <div style={{
              position: "absolute",
              bottom: s(60),
              left: "15%",
              right: "15%",
              opacity: textOpacity,
              background: "rgba(10, 10, 30, 0.7)",
              backdropFilter: "blur(10px)",
              WebkitBackdropFilter: "blur(10px)",
              borderRadius: s(14),
              padding: `${s(18)}px ${s(28)}px`,
            }}>
              <InlineLatex text={explanation} color={scene.bodyTextColor} fontSize={explainFontSize} fontFamily={theme.fonts.body} lineHeight={1.7} textAlign="center" />
            </div>
          )}
        </>
      ) : (
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", flexDirection: flexDir, alignItems: "center", justifyContent: "center", padding: pad, gap: s(isPortrait ? 40 : 60) }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flexShrink: 0, opacity: currentOpacity, transform: `scale(${currentScale})`, maxWidth: isPortrait ? "95%" : "55%" }}>
            {title && <div style={{ color: formulaAccent, fontSize: s(24), fontWeight: 600, fontFamily: theme.fonts.title, textTransform: "uppercase" as const, letterSpacing: 5, marginBottom: s(30) }}>{title}</div>}

            {isMultiStep && (
              <div style={{ display: "flex", gap: s(10), marginBottom: s(16) }}>
                {parts.map((_, idx) => (
                  <div key={idx} style={{ width: s(8), height: s(8), borderRadius: "50%", background: (frame >= 40 || idx === 0) ? formulaAccent : `${formulaAccent}4D` }} />
                ))}
              </div>
            )}

            <div style={{ background: formulaBg, border: `1px solid ${formulaBorder}`, borderRadius: s(24), padding: `${s(36)}px ${s(44)}px`, maxWidth: "100%", overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>
              {rendered.ok ? (
                <span style={{ fontSize: formulaFontSize, color: theme.colors.text, display: "block", overflow: "hidden" }} dangerouslySetInnerHTML={{ __html: rendered.html }} />
              ) : (
                <span style={{ color: theme.colors.text, fontSize: formulaFontSize, fontFamily: "'Times New Roman', serif", fontStyle: "italic", wordBreak: "break-all" as const }}>{currentFormula}</span>
              )}
            </div>
          </div>

          {hasExplanation && (
            <div style={{ maxWidth: isPortrait ? "95%" : undefined, flex: isPortrait ? undefined : 2, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: isPortrait ? "center" : "flex-start", opacity: textOpacity, transform: isPortrait ? `translateY(${interpolate(frame, [textDelay, textDelay + 30], [30, 0], { extrapolateRight: "clamp" })}px)` : `translateX(${interpolate(frame, [textDelay, textDelay + 30], [40, 0], { extrapolateRight: "clamp" })}px)` }}>
              <div style={{ width: s(50), height: s(4), background: `linear-gradient(90deg, ${formulaAccent}, ${theme.colors.primary})`, borderRadius: 2, marginBottom: s(28) }} />
              <InlineLatex text={explanation} color={scene.bodyTextColor} fontSize={explainFontSize} fontFamily={theme.fonts.body} lineHeight={1.7} textAlign={isPortrait ? "center" : "left"} />
            </div>
          )}
        </div>
      )}
    </DynamicBackground>
  );
};
