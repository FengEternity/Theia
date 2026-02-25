import { spring, useCurrentFrame, useVideoConfig } from "remotion";

type BulletListProps = {
  items: string[];
  startDelay?: number;
  itemDelay?: number;
  accentColor?: string;
  fontSize?: number;
};

export const BulletList: React.FC<BulletListProps> = ({
  items,
  startDelay = 30,
  itemDelay = 18,
  accentColor = "#3b82f6",
  fontSize = 24,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {items.map((item, i) => {
        const delay = startDelay + i * itemDelay;
        const prog = spring({
          frame: frame - delay,
          fps,
          config: { damping: 15, stiffness: 120 },
        });

        return (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 16,
              opacity: prog,
              transform: `translateX(${(1 - prog) * 50}px)`,
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: 4,
                background: accentColor,
                marginTop: fontSize * 0.45,
                flexShrink: 0,
              }}
            />
            <span
              style={{
                color: "#cbd5e1",
                fontSize,
                lineHeight: 1.5,
                fontFamily: "system-ui, sans-serif",
              }}
            >
              {item}
            </span>
          </div>
        );
      })}
    </div>
  );
};
