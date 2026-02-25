import { Img, spring, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { useTheme } from "../themes";
import { useScale } from "../hooks/useScale";
import { getIcon, getArrow } from "../utils/characterAssets";

type AnalogySceneProps = {
  data: Record<string, unknown>;
  durationInFrames: number;
};

type SideData = { label?: string; description?: string };

export const AnalogyScene: React.FC<AnalogySceneProps> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();
  const { s, isPortrait, padH } = useScale();

  const concept = (data.concept as SideData) ?? { label: "", description: "" };
  const analogy = (data.analogy as SideData) ?? { label: "", description: "" };
  const mapping = (data.mapping as string) ?? "";

  const leftProgress = spring({
    frame: frame - 5,
    fps,
    config: { mass: 0.5, stiffness: 120, damping: 12 },
  });

  const rightProgress = spring({
    frame: frame - 20,
    fps,
    config: { mass: 0.5, stiffness: 120, damping: 12 },
  });

  const arrowProgress = spring({
    frame: frame - 35,
    fps,
    config: { mass: 0.4, stiffness: 100, damping: 14 },
  });

  const mappingOpacity = interpolate(frame, [50, 65], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const showDecorations = theme.character.showDecorationIcons;

  const cardStyle = (progress: number, color: string): React.CSSProperties => ({
    flex: 1,
    background: theme.colors.surface,
    borderRadius: s(theme.decoration.borderRadius),
    padding: s(32),
    border: `3px solid ${color}`,
    transform: `scale(${progress})`,
    opacity: progress,
    textAlign: "center",
    boxShadow: `0 ${s(4)}px ${s(16)}px rgba(0,0,0,0.06)`,
    position: "relative",
  });

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: `0 ${padH}px`,
        gap: s(24),
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: isPortrait ? "column" : "row",
          gap: s(isPortrait ? 24 : 40),
          alignItems: "center",
          width: isPortrait ? "95%" : "85%",
        }}
      >
        {/* Concept side */}
        <div style={cardStyle(leftProgress, theme.colors.primary)}>
          {showDecorations && (
            <Img
              src={getIcon("gear")}
              style={{
                position: "absolute",
                top: s(-18),
                right: s(-18),
                width: s(44),
                height: s(44),
                opacity: leftProgress * 0.5,
                transform: `rotate(${frame * 0.8}deg)`,
              }}
            />
          )}
          <div
            style={{
              fontSize: s(18),
              color: theme.colors.primary,
              fontFamily: theme.fonts.body,
              fontWeight: 600,
              marginBottom: s(12),
              textTransform: "uppercase",
              letterSpacing: s(2),
            }}
          >
            概念
          </div>
          <div
            style={{
              fontSize: s(isPortrait ? 36 : 42),
              fontWeight: 700,
              fontFamily: theme.fonts.title,
              color: theme.colors.text,
              marginBottom: s(16),
            }}
          >
            {concept.label}
          </div>
          <div
            style={{
              fontSize: s(24),
              fontFamily: theme.fonts.body,
              color: theme.colors.textSecondary,
              lineHeight: 1.5,
            }}
          >
            {concept.description}
          </div>
        </div>

        {/* Arrow / equals sign */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            opacity: arrowProgress,
            transform: isPortrait
              ? `rotate(90deg) scale(${arrowProgress})`
              : `scale(${arrowProgress})`,
          }}
        >
          {showDecorations ? (
            <Img
              src={getArrow("curved-right")}
              style={{
                width: s(100),
                height: s(50),
              }}
            />
          ) : (
            <span
              style={{
                fontSize: s(48),
                color: theme.colors.accent,
                fontWeight: 700,
              }}
            >
              ≈
            </span>
          )}
        </div>

        {/* Analogy side */}
        <div style={cardStyle(rightProgress, theme.colors.secondary)}>
          {showDecorations && (
            <Img
              src={getIcon("lightbulb")}
              style={{
                position: "absolute",
                top: s(-18),
                right: s(-18),
                width: s(44),
                height: s(44),
                opacity: rightProgress * 0.5,
              }}
            />
          )}
          <div
            style={{
              fontSize: s(18),
              color: theme.colors.secondary === "#F5D76E" ? "#B7950B" : theme.colors.secondary,
              fontFamily: theme.fonts.body,
              fontWeight: 600,
              marginBottom: s(12),
              textTransform: "uppercase",
              letterSpacing: s(2),
            }}
          >
            类比
          </div>
          <div
            style={{
              fontSize: s(isPortrait ? 36 : 42),
              fontWeight: 700,
              fontFamily: theme.fonts.title,
              color: theme.colors.text,
              marginBottom: s(16),
            }}
          >
            {analogy.label}
          </div>
          <div
            style={{
              fontSize: s(24),
              fontFamily: theme.fonts.body,
              color: theme.colors.textSecondary,
              lineHeight: 1.5,
            }}
          >
            {analogy.description}
          </div>
        </div>
      </div>

      {/* Mapping text */}
      {mapping && (
        <div
          style={{
            fontSize: s(28),
            fontFamily: theme.fonts.body,
            color: theme.colors.text,
            fontWeight: 600,
            opacity: mappingOpacity,
            background: theme.colors.surface,
            padding: `${s(16)}px ${s(32)}px`,
            borderRadius: s(theme.decoration.borderRadius),
            border: `2px dashed ${theme.colors.primary}`,
          }}
        >
          {mapping}
        </div>
      )}
    </div>
  );
};
