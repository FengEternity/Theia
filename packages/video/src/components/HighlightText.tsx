import { interpolate, useCurrentFrame } from "remotion";

type HighlightTextProps = {
  text: string;
  highlights?: string[];
  highlightColor?: string;
  fontSize?: number;
  color?: string;
  delay?: number;
  maxWidth?: number;
};

/**
 * 文本组件，自动高亮指定关键词。
 */
export const HighlightText: React.FC<HighlightTextProps> = ({
  text,
  highlights = [],
  highlightColor = "#3b82f6",
  fontSize = 28,
  color = "#e2e8f0",
  delay = 0,
  maxWidth = 1200,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame - delay, [0, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (highlights.length === 0) {
    return (
      <p style={{ color, fontSize, lineHeight: 1.6, maxWidth, opacity, fontFamily: "system-ui, sans-serif" }}>
        {text}
      </p>
    );
  }

  const regex = new RegExp(`(${highlights.map(escapeRegex).join("|")})`, "gi");
  const parts = text.split(regex);

  return (
    <p style={{ color, fontSize, lineHeight: 1.6, maxWidth, opacity, fontFamily: "system-ui, sans-serif" }}>
      {parts.map((part, i) => {
        const isHighlight = highlights.some(
          (h) => h.toLowerCase() === part.toLowerCase(),
        );
        if (isHighlight) {
          return (
            <span
              key={i}
              style={{
                color: highlightColor,
                fontWeight: 700,
                textDecoration: "underline",
                textDecorationColor: `${highlightColor}55`,
                textUnderlineOffset: 4,
              }}
            >
              {part}
            </span>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </p>
  );
};

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
