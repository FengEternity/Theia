import { Img, interpolate, useCurrentFrame } from "remotion";
import type { TitleData } from "../types/script";
import { useScale } from "../hooks/useScale";
import { useTheme } from "../themes";
import { DynamicBackground } from "../components/DynamicBackground";
import { getMascot, getSticker } from "../utils/characterAssets";
import type { MascotSeries } from "../utils/characterAssets";

export const TitleScene: React.FC<{
  data: Record<string, unknown>;
  durationInFrames: number;
}> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { s, pad } = useScale();
  const theme = useTheme();
  const { title, authors, year } = data as unknown as TitleData;

  const titleOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [0, 30], [40, 0], { extrapolateRight: "clamp" });
  const authorOpacity = interpolate(frame, [20, 50], [0, 1], { extrapolateRight: "clamp" });
  const yearOpacity = interpolate(frame, [40, 60], [0, 1], { extrapolateRight: "clamp" });
  const lineWidth = interpolate(frame, [0, 40], [0, s(200)], { extrapolateRight: "clamp" });

  const titleLen = (title || "").length;
  const titleFontSize = s(titleLen > 80 ? 56 : titleLen > 50 ? 64 : titleLen > 30 ? 74 : 82);
  const authorCount = (authors || []).length;
  const authorFontSize = s(authorCount > 6 ? 32 : authorCount > 4 ? 36 : 40);

  const showMascot = theme.character.showMascot;
  const series = theme.character.mascotSeries as MascotSeries;
  const mascotSrc = getMascot(series, "explaining");
  const mascotOpacity = interpolate(frame, [10, 35], [0, 1], { extrapolateRight: "clamp" });
  const bobOffset = Math.sin(frame * 0.05) * s(4);

  return (
    <DynamicBackground
      colors={theme.colors.gradientStops}
      accentColor={theme.colors.accentRgb}
      particleCount={theme.decoration.showParticles ? 15 : 0}
      showOrb={theme.decoration.showOrb}
      mode={theme.decoration.backgroundStyle === "flat" ? "flat" : undefined}
    >
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: pad, fontFamily: theme.fonts.body }}>
        {/* Mascot for popsci theme */}
        {showMascot && mascotSrc && (
          <Img
            src={mascotSrc}
            style={{
              width: s(140),
              height: s(140),
              objectFit: "contain",
              marginBottom: s(16),
              opacity: mascotOpacity,
              transform: `translateY(${bobOffset}px)`,
            }}
          />
        )}

        <div style={{ width: lineWidth, height: s(4), background: `linear-gradient(90deg, ${theme.colors.primary}, ${theme.colors.secondary === theme.colors.primary ? theme.colors.accent : theme.colors.secondary})`, borderRadius: 2, marginBottom: s(40), opacity: titleOpacity }} />

        <h1 style={{ color: theme.colors.text, fontSize: titleFontSize, fontWeight: 700, fontFamily: theme.fonts.title, textAlign: "center" as const, lineHeight: 1.3, maxWidth: "95%", opacity: titleOpacity, transform: `translateY(${titleY}px)` }}>
          {title}
        </h1>

        <p style={{ color: theme.colors.textSecondary, fontSize: authorFontSize, fontFamily: theme.fonts.body, marginTop: s(36), opacity: authorOpacity, letterSpacing: 1.5, textAlign: "center" as const }}>
          {authors?.join("  \u00B7  ")}
        </p>

        {year && (
          <div style={{ display: "flex", alignItems: "center", gap: s(14), marginTop: s(22), opacity: yearOpacity }}>
            <div style={{ width: s(40), height: 1, background: theme.colors.textSecondary + "60" }} />
            <span style={{ color: theme.colors.textSecondary, fontSize: s(34), fontWeight: 500 }}>{year}</span>
            <div style={{ width: s(40), height: 1, background: theme.colors.textSecondary + "60" }} />
          </div>
        )}

        {/* Stickers for popsci theme */}
        {theme.character.showStickers && (
          <>
            <Img
              src={getSticker("star")}
              style={{
                position: "absolute",
                top: s(40),
                right: s(50),
                width: s(48),
                height: s(48),
                opacity: titleOpacity * 0.3,
                transform: `rotate(${Math.sin(frame * 0.04) * 15}deg)`,
              }}
            />
            <Img
              src={getSticker("heart")}
              style={{
                position: "absolute",
                bottom: s(60),
                left: s(50),
                width: s(40),
                height: s(40),
                opacity: authorOpacity * 0.25,
                transform: `scale(${0.9 + Math.sin(frame * 0.06) * 0.1})`,
              }}
            />
          </>
        )}
      </div>
    </DynamicBackground>
  );
};
