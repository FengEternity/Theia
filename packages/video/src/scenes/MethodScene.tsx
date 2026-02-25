import { Img, interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import type { MethodData } from "../types/script";
import { DynamicBackground } from "../components/DynamicBackground";
import { useScale } from "../hooks/useScale";
import { useTheme, resolveSceneStyle } from "../themes";
import { getIcon } from "../utils/characterAssets";

export const MethodScene: React.FC<{
  data: Record<string, unknown>;
  durationInFrames: number;
}> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s, pad, isPortrait } = useScale();
  const theme = useTheme();
  const scene = resolveSceneStyle(theme, "method");
  const { summary, steps } = data as unknown as MethodData;

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
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", flexDirection: "column", justifyContent: isPortrait ? "center" : "flex-start", padding: pad, fontFamily: theme.fonts.body }}>
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
            const delay = 35 + i * 18;
            const prog = spring({ frame: frame - delay, fps, config: { damping: 14 } });
            const highlightStart = delay + 10;
            const highlightEnd = highlightStart + Math.max(durationInFrames / stepCount - 18, 30);
            const isActive = frame >= highlightStart && frame < highlightEnd;
            const bgAlpha = isActive ? 0.12 : 0.04;
            const borderAlpha = isActive ? 0.4 : 0.1;

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
                <p style={{ color: isActive ? theme.colors.text : theme.colors.textSecondary, fontSize: stepFontSize, fontFamily: theme.fonts.body, lineHeight: 1.5, marginTop: s(4) }}>{step}</p>
              </div>
            );
          })}
        </div>
      </div>
    </DynamicBackground>
  );
};
