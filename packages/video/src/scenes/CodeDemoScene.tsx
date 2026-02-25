import { Img, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { useTheme } from "../themes";
import { useScale } from "../hooks/useScale";
import { BrowserFrame } from "../components/BrowserFrame";
import { getIcon } from "../utils/characterAssets";

type CodeDemoSceneProps = {
  data: Record<string, unknown>;
  durationInFrames: number;
};

export const CodeDemoScene: React.FC<CodeDemoSceneProps> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();
  const { s, isPortrait, padH } = useScale();

  const language = (data.language as string) ?? "python";
  const code = (data.code as string) ?? "";
  const highlights = (data.highlights as number[]) ?? [];
  const filename = (data.filename as string) ?? `example.${language}`;

  const lines = code.split("\n");
  const CHARS_PER_FRAME = 1.5;
  const totalChars = code.length;
  const charsToShow = Math.min(totalChars, Math.floor(frame * CHARS_PER_FRAME));

  let charCount = 0;
  const visibleLines = lines.map((line) => {
    if (charCount >= charsToShow) return "";
    const remaining = charsToShow - charCount;
    charCount += line.length + 1;
    return remaining >= line.length ? line : line.slice(0, remaining);
  });

  const showCursor = charsToShow < totalChars;
  const showDecorations = theme.character.showDecorationIcons;

  const LINE_NUM_WIDTH = s(50);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: `0 ${padH}px`,
        position: "relative",
      }}
    >
      {showDecorations && (
        <Img
          src={getIcon("code")}
          style={{
            position: "absolute",
            top: s(30),
            left: s(isPortrait ? 16 : 50),
            width: s(56),
            height: s(56),
            opacity: 0.2,
          }}
        />
      )}
      <BrowserFrame
        title={filename}
        variant="code-editor"
        width={isPortrait ? "95%" : "78%"}
        delay={0}
      >
        <div style={{ fontFamily: theme.fonts.code, fontSize: s(22), lineHeight: 1.7 }}>
          {visibleLines.map((line, i) => {
            if (i > 0 && charCount <= 0 && line === "") return null;
            const isHighlighted = highlights.includes(i + 1);

            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  background: isHighlighted ? "rgba(245,215,110,0.08)" : "transparent",
                  borderLeft: isHighlighted ? `3px solid ${theme.colors.secondary}` : "3px solid transparent",
                  paddingRight: s(8),
                }}
              >
                <span
                  style={{
                    width: LINE_NUM_WIDTH,
                    color: "#6C7086",
                    textAlign: "right",
                    paddingRight: s(16),
                    flexShrink: 0,
                    userSelect: "none",
                  }}
                >
                  {i + 1}
                </span>
                <span style={{ color: "#CDD6F4", whiteSpace: "pre" }}>
                  {line}
                  {showCursor && i === visibleLines.filter((l) => l !== "").length - 1 && (
                    <span
                      style={{
                        display: "inline-block",
                        width: s(2),
                        height: "1.2em",
                        background: "#F5D76E",
                        marginLeft: s(1),
                        opacity: Math.sin(frame * 0.15) > 0 ? 1 : 0.2,
                        verticalAlign: "text-bottom",
                      }}
                    />
                  )}
                </span>
              </div>
            );
          })}
        </div>
      </BrowserFrame>
    </div>
  );
};
