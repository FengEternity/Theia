import { Img, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme } from "../themes";
import { useScale } from "../hooks/useScale";
import { getMascot, getSticker, getIcon } from "../utils/characterAssets";
import type { MascotSeries } from "../utils/characterAssets";

type SummaryCardSceneProps = {
  data: Record<string, unknown>;
  durationInFrames: number;
};

export const SummaryCardScene: React.FC<SummaryCardSceneProps> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();
  const { s, isPortrait, padH } = useScale();

  const title = (data.title as string) ?? "总结";
  const points = (data.points as string[]) ?? [];

  const titleProgress = spring({
    frame: frame - 5,
    fps,
    config: { mass: 0.5, stiffness: 140, damping: 12 },
  });

  const mascotProgress = spring({
    frame: frame - 10,
    fps,
    config: { mass: 0.4, stiffness: 120, damping: 10 },
  });

  const BADGE_COLORS = [theme.colors.primary, theme.colors.accent, theme.colors.secondary, "#A29BFE", "#00CEC9"];
  const showMascot = theme.character.showMascot;
  const series = theme.character.mascotSeries as MascotSeries;
  const mascotSrc = getMascot(series, "happy");
  const bobOffset = Math.sin(frame * 0.06) * s(3);

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
      {/* Decorative rocket icon */}
      {theme.character.showDecorationIcons && (
        <Img
          src={getIcon("rocket")}
          style={{
            position: "absolute",
            top: s(30),
            right: s(isPortrait ? 20 : 50),
            width: s(64),
            height: s(64),
            opacity: titleProgress * 0.3,
            transform: `scale(${titleProgress}) translateY(${-frame * 0.3}px) rotate(-20deg)`,
          }}
        />
      )}

      {/* Mascot on the left side (landscape) or top (portrait) */}
      {showMascot && mascotSrc && !isPortrait && (
        <div
          style={{
            width: s(180),
            flexShrink: 0,
            opacity: mascotProgress,
            transform: `scale(${mascotProgress}) translateY(${bobOffset}px)`,
            marginRight: s(24),
          }}
        >
          <Img
            src={mascotSrc}
            style={{ width: "100%", height: "auto", objectFit: "contain" }}
          />
        </div>
      )}

      <div style={{ width: isPortrait ? "95%" : "65%", maxWidth: s(1000) }}>
        {/* Title */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: s(16),
            marginBottom: s(36),
          }}
        >
          {theme.character.showStickers && (
            <Img
              src={getSticker("star")}
              style={{
                width: s(40),
                height: s(40),
                opacity: titleProgress,
                transform: `scale(${titleProgress}) rotate(${Math.sin(frame * 0.03) * 10}deg)`,
              }}
            />
          )}
          <div
            style={{
              fontSize: s(isPortrait ? 40 : 48),
              fontWeight: 700,
              fontFamily: theme.fonts.title,
              color: theme.colors.text,
              textAlign: "center",
              transform: `scale(${titleProgress})`,
              opacity: titleProgress,
            }}
          >
            {title}
          </div>
          {theme.character.showStickers && (
            <Img
              src={getSticker("star")}
              style={{
                width: s(40),
                height: s(40),
                opacity: titleProgress,
                transform: `scale(${titleProgress}) rotate(${-Math.sin(frame * 0.03) * 10}deg)`,
              }}
            />
          )}
        </div>

        {/* Cards */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: s(16),
          }}
        >
          {points.map((point, i) => {
            const cardProgress = spring({
              frame: frame - 15 - i * 12,
              fps,
              config: { mass: 0.4, stiffness: 160, damping: 11 },
            });

            const badgeColor = BADGE_COLORS[i % BADGE_COLORS.length];

            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: s(20),
                  background: theme.colors.surface,
                  borderRadius: s(theme.decoration.borderRadius),
                  padding: `${s(20)}px ${s(28)}px`,
                  border: `2px solid ${badgeColor}20`,
                  boxShadow: `0 ${s(2)}px ${s(12)}px rgba(0,0,0,0.04)`,
                  transform: `translateX(${(1 - cardProgress) * 50}px)`,
                  opacity: cardProgress,
                }}
              >
                {/* Number badge with checkmark for popsci */}
                <div
                  style={{
                    width: s(44),
                    height: s(44),
                    borderRadius: "50%",
                    background: badgeColor,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <span
                    style={{
                      fontSize: s(22),
                      fontWeight: 700,
                      fontFamily: theme.fonts.title,
                      color: "#FFFFFF",
                    }}
                  >
                    {i + 1}
                  </span>
                </div>

                {/* Text */}
                <div
                  style={{
                    fontSize: s(26),
                    fontFamily: theme.fonts.body,
                    color: theme.colors.text,
                    lineHeight: 1.5,
                  }}
                >
                  {point}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
