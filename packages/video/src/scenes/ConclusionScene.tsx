import { Img, interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import type { ConclusionData } from "../types/script";
import { DynamicBackground } from "../components/DynamicBackground";
import { useScale } from "../hooks/useScale";
import { useTheme, resolveSceneStyle } from "../themes";
import { getMascot, getSticker, getIcon } from "../utils/characterAssets";
import type { MascotSeries } from "../utils/characterAssets";

export const ConclusionScene: React.FC<{
  data: Record<string, unknown>;
  durationInFrames: number;
}> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s, pad } = useScale();
  const theme = useTheme();
  const scene = resolveSceneStyle(theme, "conclusion");
  const { conclusion, contributions } = data as unknown as ConclusionData;

  const headerOpacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: "clamp" });
  const lineWidth = interpolate(frame, [0, 40], [0, s(240)], { extrapolateRight: "clamp" });
  const concLen = (conclusion || "").length;
  const concFontSize = s(concLen > 200 ? 38 : concLen > 100 ? 42 : 48);
  const contribCount = (contributions || []).length;
  const contribFontSize = s(contribCount > 4 ? 30 : contribCount > 2 ? 34 : 38);

  const showMascot = theme.character.showMascot;
  const series = theme.character.mascotSeries as MascotSeries;
  const mascotSrc = getMascot(series, "happy");
  const mascotOpacity = interpolate(frame, [5, 30], [0, 1], { extrapolateRight: "clamp" });
  const bobOffset = Math.sin(frame * 0.05) * s(3);

  const accentColor = scene.accentColor;
  const accentGradient = scene.accentGradient;

  return (
    <DynamicBackground
      colors={scene.gradientStops}
      accentColor={scene.accentRgb}
      particleCount={theme.decoration.showParticles ? 12 : 0}
      showOrb={theme.decoration.showOrb}
      mode={theme.decoration.backgroundStyle === "flat" ? "flat" : undefined}
    >
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: pad, fontFamily: theme.fonts.body }}>
        {showMascot && mascotSrc && (
          <Img
            src={mascotSrc}
            style={{
              width: s(120),
              height: s(120),
              objectFit: "contain",
              marginBottom: s(12),
              opacity: mascotOpacity,
              transform: `translateY(${bobOffset}px)`,
            }}
          />
        )}

        <div style={{ color: accentColor, fontSize: s(34), fontWeight: 600, fontFamily: theme.fonts.title, textTransform: "uppercase" as const, letterSpacing: 5, marginBottom: s(16), opacity: headerOpacity }}>
          总结
        </div>
        <div style={{ width: lineWidth, height: s(3), background: accentGradient, borderRadius: 2, marginBottom: s(40) }} />

        <p style={{ color: theme.colors.text, fontSize: concFontSize, fontFamily: theme.fonts.body, lineHeight: 1.7, textAlign: "center" as const, maxWidth: "92%", opacity: interpolate(frame, [20, 50], [0, 1], { extrapolateRight: "clamp" }), transform: `translateY(${interpolate(frame, [20, 50], [24, 0], { extrapolateRight: "clamp" })}px)` }}>
          {conclusion}
        </p>

        {contributions && contributions.length > 0 && (
          <div style={{ marginTop: s(40), display: "flex", gap: s(16), flexWrap: "wrap" as const, justifyContent: "center", maxWidth: "95%" }}>
            {contributions.map((c, i) => {
              const delay = 50 + i * 18;
              const prog = spring({ frame: frame - delay, fps, config: { damping: 12, stiffness: 120 } });
              return (
                <div key={i} style={{
                  display: "flex",
                  alignItems: "center",
                  gap: s(12),
                  background: `rgba(${scene.accentRgb}, ${0.06 + prog * 0.04})`,
                  border: `1px solid rgba(${scene.accentRgb}, ${0.15 + prog * 0.15})`,
                  borderRadius: s(14),
                  padding: `${s(12)}px ${s(22)}px`,
                  opacity: prog,
                  transform: `scale(${0.85 + prog * 0.15}) translateY(${(1 - prog) * 20}px)`,
                }}>
                  {theme.character.showStickers && i === 0 ? (
                    <Img
                      src={getSticker("checkmark")}
                      style={{ width: s(32), height: s(32), flexShrink: 0 }}
                    />
                  ) : (
                    <div style={{
                      width: s(32),
                      height: s(32),
                      borderRadius: "50%",
                      background: `linear-gradient(135deg, ${theme.colors.primary}, ${theme.colors.accent})`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#fff",
                      fontSize: s(16),
                      fontWeight: 700,
                      flexShrink: 0,
                    }}>
                      {i + 1}
                    </div>
                  )}
                  <span style={{ color: scene.bodyTextColor, fontSize: contribFontSize, fontFamily: theme.fonts.body, lineHeight: 1.4 }}>{c}</span>
                </div>
              );
            })}
          </div>
        )}

        {theme.character.showDecorationIcons && (
          <Img
            src={getIcon("rocket")}
            style={{
              position: "absolute",
              bottom: s(40),
              right: s(40),
              width: s(56),
              height: s(56),
              opacity: 0.25,
              transform: `rotate(-15deg) translateY(${-frame * 0.15}px)`,
            }}
          />
        )}
      </div>
    </DynamicBackground>
  );
};
