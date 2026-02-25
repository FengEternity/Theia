import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type DataTableProps = {
  headers: string[];
  rows: string[][];
  delay?: number;
  accentColor?: string;
};

/**
 * 带动画效果的数据表格组件。
 * 逐行弹入，带渐变色头部。
 */
export const DataTable: React.FC<DataTableProps> = ({
  headers,
  rows,
  delay = 0,
  accentColor = "#3b82f6",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame - delay, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        borderRadius: 16,
        overflow: "hidden",
        border: `1px solid ${accentColor}33`,
        opacity: headerOpacity,
      }}
    >
      {/* 表头 */}
      <div
        style={{
          display: "flex",
          background: `linear-gradient(135deg, ${accentColor}25, ${accentColor}15)`,
          borderBottom: `1px solid ${accentColor}33`,
        }}
      >
        {headers.map((h, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              padding: "18px 28px",
              color: accentColor,
              fontSize: 26,
              fontWeight: 700,
              textTransform: "uppercase" as const,
              letterSpacing: 1,
              fontFamily: "system-ui, sans-serif",
            }}
          >
            {h}
          </div>
        ))}
      </div>

      {/* 数据行 */}
      {rows.map((row, ri) => {
        const rowDelay = delay + 15 + ri * 12;
        const prog = spring({
          frame: frame - rowDelay,
          fps,
          config: { damping: 15, stiffness: 120 },
        });

        return (
          <div
            key={ri}
            style={{
              display: "flex",
              borderBottom: ri < rows.length - 1 ? "1px solid rgba(148,163,184,0.1)" : "none",
              background: ri % 2 === 0 ? "rgba(15,23,42,0.5)" : "rgba(30,41,59,0.5)",
              opacity: prog,
              transform: `translateY(${(1 - prog) * 20}px)`,
            }}
          >
            {row.map((cell, ci) => (
              <div
                key={ci}
                style={{
                  flex: 1,
                  padding: "16px 28px",
                  color: ci === 0 ? "#e2e8f0" : "#94a3b8",
                  fontSize: 28,
                  fontWeight: ci === 0 ? 600 : 400,
                  fontFamily: "system-ui, sans-serif",
                  lineHeight: 1.4,
                }}
              >
                {cell}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
};
