import { interpolate, useCurrentFrame } from "remotion";
import { useTheme } from "../themes";

type CircleHighlightProps = {
  cx: number;
  cy: number;
  radius: number;
  color?: string;
  strokeWidth?: number;
  drawDuration?: number;
  delay?: number;
};

export const CircleHighlight: React.FC<CircleHighlightProps> = ({
  cx,
  cy,
  radius,
  color,
  strokeWidth = 3,
  drawDuration = 20,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const theme = useTheme();
  const resolvedColor = color ?? theme.colors.accent;

  const progress = interpolate(frame - delay, [0, drawDuration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (progress <= 0) return null;

  const circumference = 2 * Math.PI * radius;

  return (
    <svg
      style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}
    >
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        fill="none"
        stroke={resolvedColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={circumference * (1 - progress)}
        opacity={0.8}
      />
    </svg>
  );
};
