import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme } from "../themes";

type EmphasisStyle = "scale" | "color" | "glow" | "underline";

type EmphasisTextProps = {
  text: string;
  emphasize: string[];
  emphasisStyle?: EmphasisStyle;
  fontSize?: number;
  color?: string;
  emphasisColor?: string;
  delay?: number;
  style?: React.CSSProperties;
};

export const EmphasisText: React.FC<EmphasisTextProps> = ({
  text,
  emphasize,
  emphasisStyle = "scale",
  fontSize = 28,
  color,
  emphasisColor,
  delay = 0,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();

  const resolvedColor = color ?? theme.colors.text;
  const resolvedEmphasisColor = emphasisColor ?? theme.colors.accent;

  const segments = splitByKeywords(text, emphasize);

  return (
    <span
      style={{
        fontSize,
        color: resolvedColor,
        fontFamily: theme.fonts.body,
        lineHeight: 1.6,
        ...style,
      }}
    >
      {segments.map((seg, i) => {
        if (!seg.isKeyword) {
          return <span key={i}>{seg.text}</span>;
        }

        const keywordIdx = emphasize.indexOf(seg.text);
        const emphasisDelay = delay + 10 + keywordIdx * 15;

        const progress = spring({
          frame: frame - emphasisDelay,
          fps,
          config: { mass: 0.4, stiffness: 180, damping: 10 },
        });

        const emphasisStyles: Record<EmphasisStyle, React.CSSProperties> = {
          scale: {
            color: resolvedEmphasisColor,
            fontWeight: 700,
            display: "inline-block",
            transform: `scale(${1 + progress * 0.15})`,
          },
          color: {
            color: resolvedEmphasisColor,
            fontWeight: 700,
          },
          glow: {
            color: resolvedEmphasisColor,
            fontWeight: 700,
            textShadow: `0 0 ${8 * progress}px ${resolvedEmphasisColor}60`,
          },
          underline: {
            color: resolvedEmphasisColor,
            fontWeight: 700,
            borderBottom: `3px solid ${resolvedEmphasisColor}`,
            paddingBottom: 2,
          },
        };

        return (
          <span key={i} style={emphasisStyles[emphasisStyle]}>
            {seg.text}
          </span>
        );
      })}
    </span>
  );
};

function splitByKeywords(
  text: string,
  keywords: string[],
): Array<{ text: string; isKeyword: boolean }> {
  if (keywords.length === 0) return [{ text, isKeyword: false }];

  const escaped = keywords.map((kw) => kw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escaped.join("|")})`, "g");
  const parts = text.split(pattern);

  return parts
    .filter((p) => p.length > 0)
    .map((p) => ({
      text: p,
      isKeyword: keywords.includes(p),
    }));
}
