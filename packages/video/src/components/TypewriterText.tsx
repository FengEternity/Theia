import { useCurrentFrame } from "remotion";
import { useTheme } from "../themes";

type TypewriterTextProps = {
  text: string;
  charDelay?: number;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
  showCursor?: boolean;
  delay?: number;
  style?: React.CSSProperties;
};

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  charDelay = 2,
  fontSize = 28,
  color,
  fontWeight = 400,
  showCursor = true,
  delay = 0,
  style,
}) => {
  const frame = useCurrentFrame();
  const theme = useTheme();

  const localFrame = Math.max(0, frame - delay);
  const charsToShow = Math.min(text.length, Math.floor(localFrame / charDelay));
  const displayText = text.slice(0, charsToShow);
  const isTyping = charsToShow < text.length;

  return (
    <span
      style={{
        fontSize,
        color: color ?? theme.colors.text,
        fontWeight,
        fontFamily: theme.fonts.body,
        lineHeight: 1.5,
        ...style,
      }}
    >
      {displayText}
      {showCursor && isTyping && (
        <span
          style={{
            display: "inline-block",
            width: fontSize * 0.08,
            height: "1.1em",
            background: theme.colors.primary,
            marginLeft: 2,
            opacity: Math.sin(frame * 0.2) > 0 ? 1 : 0.15,
            verticalAlign: "text-bottom",
          }}
        />
      )}
    </span>
  );
};
