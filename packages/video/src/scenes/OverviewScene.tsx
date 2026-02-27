import { Img, interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import type { OverviewData } from "../types/script";
import { HighlightText } from "../components/HighlightText";
import { DynamicBackground } from "../components/DynamicBackground";
import { useScale } from "../hooks/useScale";
import { useTheme, resolveSceneStyle } from "../themes";
import { getIcon } from "../utils/characterAssets";

export const OverviewScene: React.FC<{
  data: Record<string, unknown>;
  durationInFrames: number;
}> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s, pad, isPortrait } = useScale();
  const theme = useTheme();
  const scene = resolveSceneStyle(theme, "overview");
  const { problem, contributions } = data as unknown as OverviewData;

  const headerOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const hasContrib = (contributions || []).length > 0;
  const problemLen = (problem || "").length;
  const problemFontSize = s(problemLen > 200 ? 36 : problemLen > 120 ? 40 : 44);
  const contribCount = (contributions || []).length;
  const contribFontSize = s(contribCount > 4 ? 34 : contribCount > 2 ? 38 : 40);
  const flexDir = isPortrait ? "column" as const : "row" as const;

  const showDecorations = theme.character.showDecorationIcons;
  const primaryColor = scene.accentColor;
  const secondaryColor = scene.secondaryColor;

  return (
    <DynamicBackground
      colors={scene.gradientStops}
      accentColor={scene.accentRgb}
      particleCount={theme.decoration.showParticles ? undefined : 0}
      showOrb={theme.decoration.showOrb}
      mode={theme.decoration.backgroundStyle === "flat" ? "flat" : undefined}
    >
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", flexDirection: flexDir, justifyContent: isPortrait ? "center" : "flex-start", padding: pad, gap: s(isPortrait ? 30 : 40), fontFamily: theme.fonts.body }}>
        <div style={{ flex: isPortrait ? undefined : 1, display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", gap: s(14), marginBottom: s(24), opacity: headerOpacity }}>
            {showDecorations ? (
              <Img src={getIcon("brain")} style={{ width: s(30), height: s(30) }} />
            ) : (
              <div style={{ width: s(5), height: s(30), background: primaryColor, borderRadius: 3 }} />
            )}
            <span style={{ color: primaryColor, fontSize: s(24), fontWeight: 600, fontFamily: theme.fonts.title, textTransform: "uppercase" as const, letterSpacing: 3 }}>研究问题</span>
          </div>
          <HighlightText text={problem} highlights={["注意力", "Transformer", "attention", "并行", "self-attention", "自注意力", "循环", "recurrent", "卷积", "convolutional"]} fontSize={problemFontSize} color={theme.colors.text} maxWidth={isPortrait ? 960 : hasContrib ? 820 : 1700} delay={10} />
        </div>

        {hasContrib && (
          <>
            {!isPortrait && <div style={{ width: 2, height: interpolate(frame, [15, 45], [0, 700], { extrapolateRight: "clamp" }), background: `linear-gradient(180deg, ${primaryColor}80, ${secondaryColor}50, transparent)`, borderRadius: 1, alignSelf: "center" }} />}
            {isPortrait && <div style={{ height: 2, width: interpolate(frame, [15, 45], [0, 300], { extrapolateRight: "clamp" }), background: `linear-gradient(90deg, ${primaryColor}80, transparent)`, borderRadius: 1, alignSelf: "center" }} />}

            <div style={{ flex: isPortrait ? undefined : 1, display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", alignItems: "center", gap: s(14), marginBottom: s(24), opacity: interpolate(frame, [20, 40], [0, 1], { extrapolateRight: "clamp" }) }}>
                {showDecorations ? (
                  <Img src={getIcon("rocket")} style={{ width: s(30), height: s(30) }} />
                ) : (
                  <div style={{ width: s(5), height: s(30), background: secondaryColor, borderRadius: 3 }} />
                )}
                <span style={{ color: secondaryColor, fontSize: s(24), fontWeight: 600, fontFamily: theme.fonts.title, textTransform: "uppercase" as const, letterSpacing: 3 }}>核心贡献</span>
              </div>
              {contributions?.map((c, i) => {
                const delay = 35 + i * 22;
                const prog = spring({ frame: frame - delay, fps, config: { damping: 14 } });
                return (
                  <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: s(16), marginBottom: s(20), opacity: prog, transform: `translateX(${(1 - prog) * 50}px)` }}>
                    <div style={{ width: s(40), height: s(40), borderRadius: s(20), background: `linear-gradient(135deg, ${primaryColor}, ${secondaryColor})`, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: s(20), fontWeight: 700, flexShrink: 0, marginTop: s(4) }}>
                      {i + 1}
                    </div>
                    <p style={{ color: scene.bodyTextColor, fontSize: contribFontSize, fontFamily: theme.fonts.body, lineHeight: 1.5 }}>{c}</p>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </DynamicBackground>
  );
};
