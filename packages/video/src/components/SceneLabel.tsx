import { interpolate, useCurrentFrame } from "remotion";
import { useScale } from "../hooks/useScale";

const SCENE_LABELS: Record<string, { label: string; color: string }> = {
  title: { label: "", color: "transparent" },
  overview: { label: "研究背景", color: "#3b82f6" },
  method: { label: "方法论", color: "#8b5cf6" },
  formula: { label: "核心公式", color: "#a855f7" },
  figure: { label: "关键图表", color: "#6366f1" },
  result: { label: "实验结果", color: "#10b981" },
  conclusion: { label: "总结", color: "#f59e0b" },
};

type SceneLabelProps = {
  sceneType: string;
  durationInFrames: number;
};

export const SceneLabel: React.FC<SceneLabelProps> = ({
  sceneType,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { s } = useScale();
  const config = SCENE_LABELS[sceneType];

  if (!config || !config.label) return null;

  const enterOpacity = interpolate(frame, [0, 20], [0, 0.85], {
    extrapolateRight: "clamp",
  });
  const exitOpacity = interpolate(
    frame,
    [durationInFrames - 20, durationInFrames],
    [0.85, 0],
    { extrapolateLeft: "clamp" },
  );
  const opacity = Math.min(enterOpacity, exitOpacity);

  return (
    <div
      style={{
        position: "absolute",
        top: s(20),
        left: s(28),
        display: "flex",
        alignItems: "center",
        gap: s(10),
        opacity,
        zIndex: 10,
      }}
    >
      <div
        style={{
          width: s(8),
          height: s(8),
          borderRadius: "50%",
          background: config.color,
          boxShadow: `0 0 8px ${config.color}88`,
        }}
      />
      <span
        style={{
          color: config.color,
          fontSize: s(18),
          fontWeight: 600,
          letterSpacing: 2,
          fontFamily: "system-ui, sans-serif",
          textTransform: "uppercase",
        }}
      >
        {config.label}
      </span>
    </div>
  );
};
