import { useCurrentFrame, useVideoConfig } from "remotion";

type ProgressBarProps = {
  color?: string;
  height?: number;
};

export const ProgressBar: React.FC<ProgressBarProps> = ({
  color = "#3b82f6",
  height = 4,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const progress = (frame / durationInFrames) * 100;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        height,
        background: "rgba(255, 255, 255, 0.05)",
      }}
    >
      <div
        style={{
          height: "100%",
          width: `${progress}%`,
          background: `linear-gradient(90deg, ${color}, ${color}dd)`,
          borderRadius: `0 ${height / 2}px ${height / 2}px 0`,
        }}
      />
    </div>
  );
};
