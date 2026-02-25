import { Img, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme } from "../themes";
import { useScale } from "../hooks/useScale";
import { getIcon, getMascot } from "../utils/characterAssets";
import type { MascotSeries } from "../utils/characterAssets";

type ComparisonItem = { name: string; features: Record<string, string> };

type ComparisonSceneProps = {
  data: Record<string, unknown>;
  durationInFrames: number;
};

export const ComparisonScene: React.FC<ComparisonSceneProps> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();
  const { s, isPortrait, padH } = useScale();

  const items = (data.items as ComparisonItem[]) ?? [];
  const featureLabels = (data.featureLabels as string[]) ?? [];

  const labels = featureLabels.length > 0
    ? featureLabels
    : items.length > 0
      ? Object.keys(items[0].features)
      : [];

  const COLORS = [theme.colors.primary, theme.colors.secondary, theme.colors.accent, "#A29BFE", "#00CEC9"];
  const showDecorations = theme.character.showDecorationIcons;
  const showMascot = theme.character.showMascot;

  const mascotProgress = spring({
    frame: frame - 5,
    fps,
    config: { mass: 0.4, stiffness: 120, damping: 10 },
  });

  const series = theme.character.mascotSeries as MascotSeries;
  const mascotSrc = getMascot(series, "thinking");
  const bobOffset = Math.sin(frame * 0.05) * s(3);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: `0 ${padH}px`,
        gap: s(24),
        position: "relative",
      }}
    >
      {/* Decorative gear icon */}
      {showDecorations && (
        <Img
          src={getIcon("gear")}
          style={{
            position: "absolute",
            top: s(30),
            left: s(isPortrait ? 20 : 50),
            width: s(56),
            height: s(56),
            opacity: 0.2,
            transform: `rotate(${frame * 0.5}deg)`,
          }}
        />
      )}

      {/* Mascot on the left (landscape only) */}
      {showMascot && mascotSrc && !isPortrait && (
        <div
          style={{
            width: s(140),
            flexShrink: 0,
            opacity: mascotProgress,
            transform: `scale(${mascotProgress}) translateY(${bobOffset}px)`,
          }}
        >
          <Img
            src={mascotSrc}
            style={{ width: "100%", height: "auto", objectFit: "contain" }}
          />
        </div>
      )}

      <div
        style={{
          background: theme.colors.surface,
          borderRadius: s(theme.decoration.borderRadius),
          overflow: "hidden",
          boxShadow: `0 ${s(4)}px ${s(24)}px rgba(0,0,0,0.08)`,
          width: isPortrait ? "95%" : showMascot ? "70%" : "85%",
        }}
      >
        {/* Header row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `${s(140)}px ${items.map(() => "1fr").join(" ")}`,
            borderBottom: `2px solid ${theme.colors.primary}20`,
          }}
        >
          <div
            style={{
              padding: s(16),
              fontFamily: theme.fonts.body,
              fontSize: s(20),
              color: theme.colors.textSecondary,
              fontWeight: 600,
            }}
          />
          {items.map((item, i) => {
            const headerProgress = spring({
              frame: frame - i * 10 - 5,
              fps,
              config: { mass: 0.4, stiffness: 180, damping: 12 },
            });

            return (
              <div
                key={i}
                style={{
                  padding: `${s(16)}px ${s(12)}px`,
                  textAlign: "center",
                  fontFamily: theme.fonts.title,
                  fontSize: s(26),
                  fontWeight: 700,
                  color: COLORS[i % COLORS.length],
                  transform: `scale(${headerProgress})`,
                  opacity: headerProgress,
                }}
              >
                {item.name}
              </div>
            );
          })}
        </div>

        {/* Feature rows */}
        {labels.map((label, rowIdx) => {
          const rowDelay = 15 + rowIdx * 12;
          const rowProgress = spring({
            frame: frame - rowDelay,
            fps,
            config: { mass: 0.5, stiffness: 140, damping: 14 },
          });

          return (
            <div
              key={rowIdx}
              style={{
                display: "grid",
                gridTemplateColumns: `${s(140)}px ${items.map(() => "1fr").join(" ")}`,
                borderBottom: `1px solid ${theme.colors.primary}10`,
                opacity: rowProgress,
                transform: `translateX(${(1 - rowProgress) * 30}px)`,
                background: rowIdx % 2 === 0 ? "transparent" : `${theme.colors.primary}05`,
              }}
            >
              <div
                style={{
                  padding: `${s(14)}px ${s(16)}px`,
                  fontFamily: theme.fonts.body,
                  fontSize: s(20),
                  color: theme.colors.textSecondary,
                  fontWeight: 500,
                  display: "flex",
                  alignItems: "center",
                }}
              >
                {label}
              </div>
              {items.map((item, colIdx) => (
                <div
                  key={colIdx}
                  style={{
                    padding: `${s(14)}px ${s(12)}px`,
                    textAlign: "center",
                    fontFamily: theme.fonts.body,
                    fontSize: s(22),
                    color: theme.colors.text,
                    fontWeight: 500,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {item.features[label] ?? "-"}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
};
