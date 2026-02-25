import { interpolate, useCurrentFrame } from "remotion";
import { useTheme } from "../themes";

type ArrowStyle = "straight" | "curved" | "wavy";

type HandDrawnArrowProps = {
  from: { x: number; y: number };
  to: { x: number; y: number };
  color?: string;
  strokeWidth?: number;
  drawDuration?: number;
  delay?: number;
  arrowStyle?: ArrowStyle;
  headSize?: number;
};

export const HandDrawnArrow: React.FC<HandDrawnArrowProps> = ({
  from,
  to,
  color,
  strokeWidth = 3,
  drawDuration = 20,
  delay = 0,
  arrowStyle = "curved",
  headSize = 12,
}) => {
  const frame = useCurrentFrame();
  const theme = useTheme();
  const resolvedColor = color ?? theme.colors.textSecondary;

  const progress = interpolate(frame - delay, [0, drawDuration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (progress <= 0) return null;

  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const len = Math.sqrt(dx * dx + dy * dy);

  let pathD: string;
  if (arrowStyle === "straight") {
    pathD = `M ${from.x} ${from.y} L ${to.x} ${to.y}`;
  } else if (arrowStyle === "wavy") {
    const midX = (from.x + to.x) / 2;
    const midY = (from.y + to.y) / 2;
    const perpX = -dy / len * len * 0.15;
    const perpY = dx / len * len * 0.15;
    pathD = `M ${from.x} ${from.y} Q ${midX + perpX * 0.5} ${midY + perpY * 0.5} ${midX} ${midY} Q ${midX - perpX * 0.3} ${midY - perpY * 0.3} ${to.x} ${to.y}`;
  } else {
    const midX = (from.x + to.x) / 2;
    const midY = (from.y + to.y) / 2;
    const perpX = -dy / len * len * 0.2;
    const perpY = dx / len * len * 0.2;
    pathD = `M ${from.x} ${from.y} Q ${midX + perpX} ${midY + perpY} ${to.x} ${to.y}`;
  }

  const angle = Math.atan2(dy, dx);
  const headP1 = {
    x: to.x - headSize * Math.cos(angle - Math.PI / 6),
    y: to.y - headSize * Math.sin(angle - Math.PI / 6),
  };
  const headP2 = {
    x: to.x - headSize * Math.cos(angle + Math.PI / 6),
    y: to.y - headSize * Math.sin(angle + Math.PI / 6),
  };

  const estimatedPathLength = len * (arrowStyle === "straight" ? 1 : 1.3);

  return (
    <svg
      style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}
    >
      <path
        d={pathD}
        fill="none"
        stroke={resolvedColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={estimatedPathLength}
        strokeDashoffset={estimatedPathLength * (1 - progress)}
      />
      {progress > 0.85 && (
        <polygon
          points={`${to.x},${to.y} ${headP1.x},${headP1.y} ${headP2.x},${headP2.y}`}
          fill={resolvedColor}
          opacity={interpolate(progress, [0.85, 1], [0, 1])}
        />
      )}
    </svg>
  );
};
