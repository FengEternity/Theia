import { OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import type { ManimClip as ManimClipType } from "../types/script";
import { useScale } from "../hooks/useScale";

function getPositionStyle(
  position: string,
  s: (px: number) => number,
): React.CSSProperties {
  const base: React.CSSProperties = {
    position: "absolute",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  };

  switch (position) {
    case "left":
      return { ...base, top: "10%", left: s(40), width: "45%", height: "80%" };
    case "right":
      return { ...base, top: "10%", right: s(40), width: "45%", height: "80%" };
    case "full":
      return { ...base, top: 0, left: 0, width: "100%", height: "100%" };
    case "center":
    default:
      return { ...base, top: "10%", left: "15%", width: "70%", height: "80%" };
  }
}

export const ManimClipPlayer: React.FC<{
  clip: ManimClipType;
  durationInFrames: number;
}> = ({ clip, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useScale();

  const clipStartFrame = Math.round((clip.startMs / 1000) * fps);
  const clipDurationFrames = Math.round((clip.durationMs / 1000) * fps);
  const clipEndFrame = clipStartFrame + clipDurationFrames;
  const sceneEndFrame = durationInFrames;

  const isBeforeStart = frame < clipStartFrame;
  if (isBeforeStart) return null;

  const fadeIn = interpolate(
    frame,
    [clipStartFrame, clipStartFrame + 15],
    [0, 1],
    { extrapolateRight: "clamp" },
  );

  const sceneEndFade = interpolate(
    frame,
    [sceneEndFrame - 20, sceneEndFrame],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const opacity = Math.min(fadeIn, sceneEndFade) * clip.opacity;
  const positionStyle = getPositionStyle(clip.position, s);
  const isTransparent = clip.clipPath.endsWith(".webm");

  const videoFrame = Math.min(frame - clipStartFrame, clipDurationFrames - 1);

  return (
    <div style={{ ...positionStyle, opacity }}>
      <OffthreadVideo
        src={staticFile(clip.clipPath)}
        startFrom={videoFrame}
        endAt={clipDurationFrames}
        style={{ width: "100%", height: "100%", objectFit: "contain" }}
        transparent={isTransparent}
      />
    </div>
  );
};
