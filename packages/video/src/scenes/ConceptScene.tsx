import { Img, spring, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { useTheme } from "../themes";
import { useScale } from "../hooks/useScale";
import { BrowserFrame } from "../components/BrowserFrame";
import { getSceneIcon, getSticker } from "../utils/characterAssets";

type ConceptSceneProps = {
  data: Record<string, unknown>;
  durationInFrames: number;
};

export const ConceptScene: React.FC<ConceptSceneProps> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();
  const { s, isPortrait, padH } = useScale();

  const title = (data.title as string) ?? "";
  const definition = (data.definition as string) ?? "";
  const keywords = (data.keywords as string[]) ?? [];

  const titleScale = spring({
    frame: frame - 10,
    fps,
    config: { mass: 0.5, stiffness: 150, damping: 10 },
  });

  const defOpacity = interpolate(frame, [20, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const defY = interpolate(frame, [20, 40], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const iconProgress = spring({
    frame: frame - 5,
    fps,
    config: { mass: 0.3, stiffness: 200, damping: 14 },
  });

  const showDecorations = theme.character.showDecorationIcons;
  const iconSrc = getSceneIcon("concept");

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: `0 ${padH}px`,
        position: "relative",
      }}
    >
      {/* Decorative icon top-right */}
      {showDecorations && iconSrc && (
        <Img
          src={iconSrc}
          style={{
            position: "absolute",
            top: s(40),
            right: s(isPortrait ? 20 : 60),
            width: s(72),
            height: s(72),
            opacity: iconProgress * 0.35,
            transform: `scale(${iconProgress}) rotate(${-15 + frame * 0.3}deg)`,
          }}
        />
      )}

      {/* Decorative star bottom-left */}
      {showDecorations && (
        <Img
          src={getSticker("star")}
          style={{
            position: "absolute",
            bottom: s(50),
            left: s(isPortrait ? 20 : 60),
            width: s(56),
            height: s(56),
            opacity: iconProgress * 0.25,
            transform: `scale(${iconProgress}) rotate(${10 + Math.sin(frame * 0.04) * 8}deg)`,
          }}
        />
      )}

      <BrowserFrame title={title} variant="chrome" width={isPortrait ? "95%" : "75%"} delay={0}>
        <div style={{ textAlign: "center", padding: `${s(40)}px ${s(20)}px` }}>
          {/* Big title */}
          <div
            style={{
              fontSize: s(isPortrait ? 52 : 64),
              fontWeight: 700,
              fontFamily: theme.fonts.title,
              color: theme.colors.text,
              transform: `scale(${titleScale})`,
              marginBottom: s(24),
              lineHeight: 1.3,
            }}
          >
            {title}
          </div>

          {/* Definition */}
          <div
            style={{
              fontSize: s(isPortrait ? 30 : 36),
              fontFamily: theme.fonts.body,
              color: theme.colors.textSecondary,
              opacity: defOpacity,
              transform: `translateY(${defY}px)`,
              lineHeight: 1.6,
              maxWidth: s(800),
              margin: "0 auto",
            }}
          >
            {definition}
          </div>

          {/* Keywords */}
          {keywords.length > 0 && (
            <div
              style={{
                display: "flex",
                gap: s(12),
                justifyContent: "center",
                flexWrap: "wrap",
                marginTop: s(32),
              }}
            >
              {keywords.map((kw, i) => {
                const kwProgress = spring({
                  frame: frame - 40 - i * 8,
                  fps,
                  config: { mass: 0.4, stiffness: 180, damping: 12 },
                });

                return (
                  <div
                    key={i}
                    style={{
                      background: theme.colors.secondary,
                      color: theme.colors.text,
                      padding: `${s(8)}px ${s(20)}px`,
                      borderRadius: s(20),
                      fontSize: s(22),
                      fontFamily: theme.fonts.body,
                      fontWeight: 600,
                      transform: `scale(${kwProgress})`,
                      opacity: kwProgress,
                    }}
                  >
                    {kw}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </BrowserFrame>
    </div>
  );
};
