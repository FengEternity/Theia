import { Img, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme } from "../themes";
import { useScale } from "../hooks/useScale";
import { getMascot, expressionToPose, getSticker } from "../utils/characterAssets";
import type { MascotSeries } from "../utils/characterAssets";

type CharacterTalkSceneProps = {
  data: Record<string, unknown>;
  durationInFrames: number;
};

export const CharacterTalkScene: React.FC<CharacterTalkSceneProps> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();
  const { s, isPortrait, padH } = useScale();

  const text = (data.text as string) ?? "";
  const expression = (data.expression as string) ?? "explaining";

  const characterProgress = spring({
    frame: frame - 5,
    fps,
    config: { mass: 0.5, stiffness: 120, damping: 10 },
  });

  const bubbleProgress = spring({
    frame: frame - 15,
    fps,
    config: { mass: 0.4, stiffness: 140, damping: 12 },
  });

  const stickerProgress = spring({
    frame: frame - 30,
    fps,
    config: { mass: 0.3, stiffness: 200, damping: 14 },
  });

  const CHAR_SIZE = s(isPortrait ? 200 : 260);
  const bobOffset = Math.sin(frame * 0.05) * s(4);
  const useMascot = theme.character.showMascot;
  const series = theme.character.mascotSeries as MascotSeries;
  const pose = expressionToPose(expression);
  const mascotSrc = getMascot(series, pose);

  const expressionSticker = expression === "happy" ? "heart" as const
    : expression === "surprised" ? "warning" as const
    : expression === "thinking" ? "question" as const
    : null;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: isPortrait ? "center" : "center",
        justifyContent: "center",
        padding: `0 ${padH}px`,
        gap: s(isPortrait ? 24 : 48),
        flexDirection: isPortrait ? "column" : "row",
      }}
    >
      {/* Character */}
      <div
        style={{
          width: CHAR_SIZE,
          height: CHAR_SIZE,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          transform: `scale(${characterProgress}) translateY(${bobOffset}px)`,
          opacity: characterProgress,
          position: "relative",
        }}
      >
        {useMascot && mascotSrc ? (
          <Img
            src={mascotSrc}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
            }}
          />
        ) : (
          <div
            style={{
              width: "100%",
              height: "100%",
              borderRadius: "50%",
              background: `linear-gradient(135deg, ${theme.colors.primary}30, ${theme.colors.secondary}30)`,
              border: `4px solid ${theme.colors.primary}40`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <span style={{ fontSize: s(80), lineHeight: 1 }}>
              {expression === "thinking" ? "\u{1F914}" : expression === "surprised" ? "\u{1F62E}" : expression === "happy" ? "\u{1F604}" : "\u{1F9D1}\u200D\u{1F3EB}"}
            </span>
          </div>
        )}

        {/* Expression sticker */}
        {useMascot && expressionSticker && theme.character.showStickers && (
          <Img
            src={getSticker(expressionSticker)}
            style={{
              position: "absolute",
              top: s(-10),
              right: s(-10),
              width: s(52),
              height: s(52),
              transform: `scale(${stickerProgress}) rotate(${15 * stickerProgress}deg)`,
              opacity: stickerProgress,
            }}
          />
        )}
      </div>

      {/* Speech bubble */}
      <div
        style={{
          position: "relative",
          maxWidth: isPortrait ? "90%" : "55%",
          transform: `scale(${bubbleProgress})`,
          opacity: bubbleProgress,
        }}
      >
        {!isPortrait && (
          <div
            style={{
              position: "absolute",
              left: s(-16),
              top: "50%",
              transform: "translateY(-50%)",
              width: 0,
              height: 0,
              borderTop: `${s(14)}px solid transparent`,
              borderBottom: `${s(14)}px solid transparent`,
              borderRight: `${s(18)}px solid ${theme.colors.surface}`,
            }}
          />
        )}

        <div
          style={{
            background: theme.colors.surface,
            borderRadius: s(theme.decoration.borderRadius + 4),
            padding: `${s(28)}px ${s(36)}px`,
            boxShadow: `0 ${s(4)}px ${s(24)}px rgba(0,0,0,0.08)`,
            border: `2px solid ${theme.colors.primary}15`,
          }}
        >
          <div
            style={{
              fontSize: s(isPortrait ? 30 : 34),
              fontFamily: theme.fonts.body,
              color: theme.colors.text,
              lineHeight: 1.7,
              fontWeight: 500,
            }}
          >
            {text}
          </div>
        </div>
      </div>
    </div>
  );
};
