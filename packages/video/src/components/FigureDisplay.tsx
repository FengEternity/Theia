import { Img, interpolate, staticFile, useCurrentFrame } from "remotion";

type FigureDisplayProps = {
  src: string;
  caption?: string;
  delay?: number;
  maxHeight?: number;
};

export const FigureDisplay: React.FC<FigureDisplayProps> = ({
  src,
  caption,
  delay = 0,
  maxHeight = 500,
}) => {
  const frame = useCurrentFrame();
  const localFrame = frame - delay;

  const opacity = interpolate(localFrame, [0, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(localFrame, [0, 25], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 12,
        opacity,
        transform: `translateY(${y}px)`,
      }}
    >
      <Img
        src={staticFile(src)}
        style={{
          maxHeight,
          maxWidth: "100%",
          objectFit: "contain",
          borderRadius: 8,
          border: "1px solid rgba(148, 163, 184, 0.2)",
        }}
      />
      {caption && (
        <span
          style={{
            color: "#94a3b8",
            fontSize: 18,
            fontFamily: "system-ui, sans-serif",
            textAlign: "center",
            maxWidth: 800,
          }}
        >
          {caption}
        </span>
      )}
    </div>
  );
};
