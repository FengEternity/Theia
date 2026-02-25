import { useCurrentFrame, useVideoConfig } from "remotion";
import { useScale } from "../hooks/useScale";
import { useTheme } from "../themes";
import type { WordTiming } from "../types/script";

type SubtitleProps = {
  wordTimings: WordTiming[];
  audioStartFrame: number;
  color?: string;
  highlightColor?: string;
};

/**
 * 基于 word-level timing 的实时字幕组件。
 * 将 wordTimings 分组为行，当前正在播报的文字高亮显示。
 */
export const Subtitle: React.FC<SubtitleProps> = ({
  wordTimings,
  audioStartFrame,
  color,
  highlightColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s, isPortrait } = useScale();
  const theme = useTheme();

  const resolvedColor = color ?? theme.colors.subtitle.text;
  const resolvedHighlight = highlightColor ?? theme.colors.subtitle.highlight;

  if (!wordTimings.length) return null;

  const elapsedMs = Math.max(0, ((frame - audioStartFrame) / fps) * 1000);

  const CHARS_PER_LINE = isPortrait ? 18 : 28;
  const lines: { words: WordTiming[]; text: string }[] = [];
  let currentLine = { words: [] as WordTiming[], text: "" };

  const isLatin = (s: string) => /^[a-zA-Z0-9]/.test(s);
  const endsLatin = (s: string) => /[a-zA-Z0-9]$/.test(s);

  for (const wt of wordTimings) {
    const needsSpace = currentLine.text.length > 0 && endsLatin(currentLine.text) && isLatin(wt.text);
    const display = (needsSpace ? " " : "") + wt.text;
    if (currentLine.text.length + display.length > CHARS_PER_LINE && currentLine.text.length > 0) {
      lines.push(currentLine);
      currentLine = { words: [], text: "" };
    }
    currentLine.words.push(wt);
    currentLine.text += display;
  }
  if (currentLine.text.length > 0) lines.push(currentLine);

  const activeLine = lines.findIndex((line) => {
    const firstWord = line.words[0];
    const lastWord = line.words[line.words.length - 1];
    const lineStart = firstWord.offsetMs;
    const lineEnd = lastWord.offsetMs + lastWord.durationMs;
    return elapsedMs >= lineStart && elapsedMs < lineEnd + 500;
  });

  const lineIdx = activeLine >= 0 ? activeLine : lines.length - 1;
  const displayLine = lines[lineIdx];
  if (!displayLine) return null;

  return (
    <div
      style={{
        position: "absolute",
        bottom: s(isPortrait ? 100 : 50),
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        zIndex: 20,
      }}
    >
      <div
        style={{
          background: theme.colors.subtitle.background,
          borderRadius: s(theme.decoration.borderRadius),
          padding: `${s(10)}px ${s(24)}px`,
          maxWidth: "90%",
        }}
      >
        <span style={{ fontSize: s(isPortrait ? 32 : 28), fontFamily: theme.fonts.body, lineHeight: 1.5 }}>
          {displayLine.words.map((wt, i) => {
            const wordStart = wt.offsetMs;
            const wordEnd = wordStart + wt.durationMs;
            const isActive = elapsedMs >= wordStart && elapsedMs < wordEnd + 200;
            const prev = displayLine.words[i - 1];
            const needsSpace = prev && /[a-zA-Z0-9]$/.test(prev.text) && /^[a-zA-Z0-9]/.test(wt.text);
            return (
              <span
                key={i}
                style={{
                  color: isActive ? resolvedHighlight : resolvedColor,
                  fontWeight: isActive ? 700 : 400,
                  transition: "color 0.1s",
                }}
              >
                {needsSpace ? " " : ""}{wt.text}
              </span>
            );
          })}
        </span>
      </div>
    </div>
  );
};
