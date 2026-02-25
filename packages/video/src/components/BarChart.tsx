import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type Bar = {
  label: string;
  value: number;
  highlight?: boolean;
};

type BarChartProps = {
  bars: Bar[];
  unit?: string;
  delay?: number;
  accentColor?: string;
  highlightColor?: string;
  maxValue?: number;
};

function formatAnimatedNumber(target: number, progress: number): string {
  const current = target * progress;
  const decimals = target % 1 !== 0 ? 1 : 0;
  return current.toFixed(decimals);
}

/**
 * 带动画效果的水平柱状图组件。
 * 柱子从 0 增长到目标值，数字同步滚动。
 */
export const BarChart: React.FC<BarChartProps> = ({
  bars,
  unit = "",
  delay = 0,
  accentColor = "#3b82f6",
  highlightColor = "#10b981",
  maxValue,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const max = maxValue ?? Math.max(...bars.map((b) => b.value)) * 1.1;
  const highlightIdx = bars.findIndex((b) => b.highlight);
  const bestIdx = highlightIdx >= 0 ? highlightIdx : bars.length - 1;
  const secondBestValue = bars.reduce(
    (best, b, i) => (i !== bestIdx && b.value > best ? b.value : best),
    0,
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {bars.map((bar, i) => {
        const barDelay = delay + i * 15;
        const prog = spring({
          frame: frame - barDelay,
          fps,
          config: { damping: 15, stiffness: 80 },
        });
        const width = (bar.value / max) * 100 * prog;
        const color = bar.highlight ? highlightColor : accentColor;

        const highlightPulse = bar.highlight
          ? 1 + Math.sin((frame - barDelay) * 0.08) * 0.015
          : 1;

        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <div
              style={{
                width: 220,
                textAlign: "right" as const,
                color: bar.highlight ? "#e2e8f0" : "#94a3b8",
                fontSize: 26,
                fontWeight: bar.highlight ? 700 : 400,
                fontFamily: "system-ui, sans-serif",
                flexShrink: 0,
              }}
            >
              {bar.label}
            </div>
            <div
              style={{
                flex: 1,
                height: 42,
                background: "rgba(255,255,255,0.04)",
                borderRadius: 8,
                overflow: "hidden",
                position: "relative",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${width}%`,
                  background: bar.highlight
                    ? `linear-gradient(90deg, ${color}aa, ${color}, ${color}ee)`
                    : `linear-gradient(90deg, ${color}cc, ${color})`,
                  borderRadius: 8,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "flex-end",
                  paddingRight: 16,
                  transform: `scaleY(${highlightPulse})`,
                  boxShadow: bar.highlight ? `0 0 20px ${color}44` : "none",
                }}
              >
                {prog > 0.3 && (
                  <span
                    style={{
                      color: "#fff",
                      fontSize: bar.highlight ? 26 : 24,
                      fontWeight: 700,
                      fontFamily: "system-ui, sans-serif",
                      opacity: interpolate(prog, [0.3, 0.7], [0, 1], { extrapolateRight: "clamp" }),
                    }}
                  >
                    {formatAnimatedNumber(bar.value, prog)}
                    {unit}
                  </span>
                )}
              </div>
            </div>
            {bar.highlight && i === bestIdx && secondBestValue > 0 && prog > 0.9 && (
              <div
                style={{
                  color: highlightColor,
                  fontSize: 22,
                  fontWeight: 700,
                  fontFamily: "system-ui, sans-serif",
                  opacity: interpolate(prog, [0.9, 1], [0, 1], { extrapolateRight: "clamp" }),
                  whiteSpace: "nowrap",
                  flexShrink: 0,
                }}
              >
                +{(bar.value - secondBestValue).toFixed(1)}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
