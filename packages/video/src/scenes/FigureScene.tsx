import { Img, interpolate, useCurrentFrame, staticFile } from "remotion";
import { DynamicBackground } from "../components/DynamicBackground";
import { useChoreography } from "../hooks/useChoreography";
import { useScale } from "../hooks/useScale";
import { useTheme, resolveSceneStyle } from "../themes";
import type { AnimationPhase } from "../types/script";

export const FigureScene: React.FC<{
  data: Record<string, unknown>;
  durationInFrames: number;
  choreography?: AnimationPhase[];
}> = ({ data, durationInFrames, choreography }) => {
  const frame = useCurrentFrame();
  const { s, pad, isPortrait } = useScale();
  const theme = useTheme();
  const scene = resolveSceneStyle(theme, "figure");
  const choreo = useChoreography(choreography);
  const { figurePath, caption, description } = data as { figurePath: string; caption: string; description: string };

  const imgScale = choreo.hasChoreography
    ? (choreo.isElementVisible("image") ? interpolate(frame, [0, 30], [0.95, 1], { extrapolateRight: "clamp" }) : 0.95)
    : interpolate(frame, [0, 30], [0.95, 1], { extrapolateRight: "clamp" });
  const imgOpacity = choreo.hasChoreography
    ? (choreo.isElementVisible("image") ? interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" }) : 0)
    : interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const textOpacity = choreo.hasChoreography
    ? (choreo.isElementVisible("caption") || choreo.isElementVisible("description")
      ? interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" })
      : 0)
    : interpolate(frame, [20, 50], [0, 1], { extrapolateRight: "clamp" });

  const imgSrc = figurePath ? staticFile(figurePath.startsWith("figures/") ? figurePath : `figures/${figurePath}`) : "";
  const hasText = (caption || "").length > 0 || (description || "").length > 0;
  const captionFontSize = s((caption || "").length > 60 ? 38 : 44);
  const descFontSize = s((description || "").length > 120 ? 34 : 38);
  const flexDir = isPortrait ? "column" as const : "row" as const;

  const accentGradient = scene.accentGradient;

  return (
    <DynamicBackground
      colors={scene.gradientStops}
      accentColor={theme.colors.accentRgb}
      particleCount={theme.decoration.showParticles ? 8 : 0}
      showOrb={theme.decoration.showOrb}
      mode={theme.decoration.backgroundStyle === "flat" ? "flat" : undefined}
    >
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", flexDirection: flexDir, alignItems: "center", justifyContent: "center", padding: pad, gap: s(isPortrait ? 24 : 50) }}>
        {imgSrc ? (
          <>
            <div style={{ maxWidth: isPortrait ? "95%" : "58%", maxHeight: isPortrait ? "50%" : "90%", display: "flex", alignItems: "center", justifyContent: "center", opacity: imgOpacity, transform: `scale(${imgScale})`, flexShrink: 0 }}>
              <Img src={imgSrc} style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" as const, borderRadius: s(14), boxShadow: scene.imageShadow, border: scene.imageBorder }} />
            </div>
            {hasText && (
              <div style={{ maxWidth: isPortrait ? "95%" : undefined, flex: isPortrait ? undefined : 2, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: isPortrait ? "center" : "flex-start", gap: s(20), opacity: textOpacity, transform: isPortrait ? `translateY(${interpolate(frame, [20, 50], [20, 0], { extrapolateRight: "clamp" })}px)` : `translateX(${interpolate(frame, [20, 50], [40, 0], { extrapolateRight: "clamp" })}px)` }}>
                <div style={{ width: s(50), height: s(4), background: accentGradient, borderRadius: 2 }} />
                {caption && <h2 style={{ color: theme.colors.text, fontSize: captionFontSize, fontWeight: 700, fontFamily: theme.fonts.title, lineHeight: 1.4, textAlign: isPortrait ? "center" as const : "left" as const }}>{caption}</h2>}
                {description && <p style={{ color: theme.colors.textSecondary, fontSize: descFontSize, fontFamily: theme.fonts.body, lineHeight: 1.65, textAlign: isPortrait ? "center" as const : "left" as const }}>{description}</p>}
              </div>
            )}
          </>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: s(24), opacity: textOpacity }}>
            {caption && <h2 style={{ color: theme.colors.text, fontSize: s(44), fontWeight: 700, fontFamily: theme.fonts.title, textAlign: "center" as const }}>{caption}</h2>}
            {description && <p style={{ color: theme.colors.textSecondary, fontSize: s(36), fontFamily: theme.fonts.body, lineHeight: 1.65, textAlign: "center" as const, maxWidth: "90%" }}>{description}</p>}
          </div>
        )}
      </div>
    </DynamicBackground>
  );
};
