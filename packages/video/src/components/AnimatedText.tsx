import { interpolate, useCurrentFrame } from "remotion";

type AnimatedTextProps = {
  text: string;
  delay?: number;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
  style?: React.CSSProperties;
};

export const AnimatedText: React.FC<AnimatedTextProps> = ({
  text,
  delay = 0,
  fontSize = 28,
  color = "#e2e8f0",
  fontWeight = 400,
  style,
}) => {
  const frame = useCurrentFrame();
  const localFrame = frame - delay;

  const opacity = interpolate(localFrame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(localFrame, [0, 20], [25, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        fontSize,
        color,
        fontWeight,
        opacity,
        transform: `translateY(${y}px)`,
        lineHeight: 1.5,
        fontFamily: "system-ui, sans-serif",
        ...style,
      }}
    >
      {text}
    </div>
  );
};
