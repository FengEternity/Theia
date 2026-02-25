import { Img, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { useTheme } from "../themes";
import { useScale } from "../hooks/useScale";
import { BrowserFrame } from "../components/BrowserFrame";
import { getIcon } from "../utils/characterAssets";

type Step = { action: string; content: string; delay?: number };

type DemoSceneProps = {
  data: Record<string, unknown>;
  durationInFrames: number;
};

export const DemoScene: React.FC<DemoSceneProps> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();
  const { s, isPortrait, padH } = useScale();

  const interfaceType = (data.interface as string) ?? "chat";
  const steps = (data.steps as Step[]) ?? [];

  const CHARS_PER_FRAME = 1.2;
  const STEP_GAP = 30;

  let accumulatedDelay = 15;
  const stepsWithTiming = steps.map((step) => {
    const startFrame = accumulatedDelay + (step.delay ?? 0);
    const typingFrames = Math.ceil(step.content.length / CHARS_PER_FRAME);
    accumulatedDelay = startFrame + typingFrames + STEP_GAP;
    return { ...step, startFrame, typingFrames };
  });

  const variant = interfaceType === "code-editor" ? "code-editor" as const : "chrome" as const;
  const frameTitle = interfaceType === "chat" ? "AI Assistant" : interfaceType === "terminal" ? "Terminal" : "";
  const showDecorations = theme.character.showDecorationIcons;

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
            right: s(isPortrait ? 16 : 50),
            width: s(56),
            height: s(56),
            opacity: 0.2,
          }}
        />
      )}
      <BrowserFrame title={frameTitle} variant={variant} width={isPortrait ? "95%" : "75%"} delay={0}>
        <div style={{ display: "flex", flexDirection: "column", gap: s(16) }}>
          {stepsWithTiming.map((step, i) => {
            const localFrame = frame - step.startFrame;
            if (localFrame < 0) return null;

            const charsToShow = Math.min(
              step.content.length,
              Math.floor(localFrame * CHARS_PER_FRAME),
            );
            const displayText = step.content.slice(0, charsToShow);
            const showCursor = charsToShow < step.content.length;

            if (interfaceType === "chat") {
              const isUser = step.action === "type";
              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    justifyContent: isUser ? "flex-end" : "flex-start",
                  }}
                >
                  <div
                    style={{
                      background: isUser ? theme.colors.primary : "#F1F1F1",
                      color: isUser ? "#FFFFFF" : theme.colors.text,
                      padding: `${s(12)}px ${s(20)}px`,
                      borderRadius: s(16),
                      fontSize: s(24),
                      fontFamily: theme.fonts.body,
                      maxWidth: "80%",
                      lineHeight: 1.5,
                    }}
                  >
                    {displayText}
                    {showCursor && (
                      <span style={{ opacity: Math.sin(frame * 0.15) > 0 ? 1 : 0 }}>|</span>
                    )}
                  </div>
                </div>
              );
            }

            if (interfaceType === "terminal") {
              const isInput = step.action === "type";
              return (
                <div
                  key={i}
                  style={{
                    fontFamily: theme.fonts.code,
                    fontSize: s(22),
                    color: isInput ? "#50FA7B" : "#F8F8F2",
                    lineHeight: 1.6,
                  }}
                >
                  {isInput && <span style={{ color: "#BD93F9" }}>$ </span>}
                  {displayText}
                  {showCursor && (
                    <span
                      style={{
                        display: "inline-block",
                        width: s(10),
                        height: s(22),
                        background: "#50FA7B",
                        marginLeft: s(2),
                        opacity: Math.sin(frame * 0.15) > 0 ? 1 : 0.2,
                      }}
                    />
                  )}
                </div>
              );
            }

            // code-editor / browser
            const isHighlight = step.action === "highlight";
            return (
              <div
                key={i}
                style={{
                  fontFamily: theme.fonts.code,
                  fontSize: s(22),
                  color: isHighlight ? "#F5D76E" : "#CDD6F4",
                  background: isHighlight ? "rgba(245,215,110,0.08)" : "transparent",
                  padding: `${s(4)}px ${s(8)}px`,
                  borderRadius: s(4),
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                }}
              >
                {displayText}
                {showCursor && (
                  <span style={{ opacity: Math.sin(frame * 0.15) > 0 ? 1 : 0 }}>|</span>
                )}
              </div>
            );
          })}
        </div>
      </BrowserFrame>
    </div>
  );
};
