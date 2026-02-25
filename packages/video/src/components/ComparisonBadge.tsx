import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type ComparisonBadgeProps = {
  metric: string;
  value: string;
  isHighlight?: boolean;
  delay?: number;
  accentColor?: string;
};

/**
 * 带动画的指标展示徽章，适合在 Result 场景中展示单个关键指标。
 */
export const ComparisonBadge: React.FC<ComparisonBadgeProps> = ({
  metric,
  value,
  isHighlight = false,
  delay = 0,
  accentColor = "#10b981",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const prog = spring({ frame: frame - delay, fps, config: { damping: 14, stiffness: 100 } });
  const glowPulse = isHighlight ? 0.15 + Math.sin(frame * 0.06) * 0.05 : 0;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "18px 28px",
        background: isHighlight
          ? `rgba(16,185,129,${0.08 + glowPulse})`
          : "rgba(255,255,255,0.04)",
        border: `1px solid ${isHighlight ? `${accentColor}44` : "rgba(255,255,255,0.08)"}`,
        borderRadius: 16,
        opacity: prog,
        transform: `scale(${0.8 + prog * 0.2})`,
        minWidth: 140,
      }}
    >
      <span
        style={{
          color: isHighlight ? accentColor : "#94a3b8",
          fontSize: 20,
          fontWeight: 600,
          fontFamily: "system-ui, sans-serif",
          letterSpacing: 1,
          marginBottom: 8,
        }}
      >
        {metric}
      </span>
      <span
        style={{
          color: isHighlight ? "#f1f5f9" : "#e2e8f0",
          fontSize: isHighlight ? 36 : 30,
          fontWeight: 700,
          fontFamily: "system-ui, sans-serif",
        }}
      >
        {value}
      </span>
    </div>
  );
};
