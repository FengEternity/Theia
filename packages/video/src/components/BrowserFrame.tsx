import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme } from "../themes";
import { useScale } from "../hooks/useScale";

type BrowserFrameVariant = "chrome" | "minimal" | "code-editor";

type BrowserFrameProps = {
  title?: string;
  children: React.ReactNode;
  width?: string;
  height?: string;
  variant?: BrowserFrameVariant;
  delay?: number;
};

export const BrowserFrame: React.FC<BrowserFrameProps> = ({
  title = "",
  children,
  width = "85%",
  height = "auto",
  variant = "chrome",
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();
  const { s } = useScale();

  const localFrame = frame - delay;

  const scaleProgress = spring({
    frame: localFrame,
    fps,
    config: { mass: 0.6, stiffness: 120, damping: 12 },
  });

  const opacity = interpolate(localFrame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const dotColors =
    variant === "code-editor"
      ? ["#FF5F57", "#FFBD2E", "#28CA42"]
      : ["#FF5F57", "#FFBD2E", "#28CA42"];

  const bgColor =
    variant === "code-editor" ? "#1E1E2E" : theme.colors.surface;

  const titleBarBg =
    variant === "code-editor"
      ? "#2B2B3D"
      : variant === "minimal"
        ? theme.colors.primary
        : "#E8E8E8";

  const titleColor =
    variant === "code-editor"
      ? "#CDD6F4"
      : variant === "minimal"
        ? "#FFFFFF"
        : "#555555";

  const borderColor =
    variant === "code-editor" ? "#313244" : "rgba(0,0,0,0.08)";

  return (
    <div
      style={{
        width,
        height,
        opacity,
        transform: `scale(${0.85 + 0.15 * scaleProgress})`,
        borderRadius: s(theme.decoration.borderRadius),
        overflow: "hidden",
        boxShadow: `0 ${s(8)}px ${s(32)}px rgba(0,0,0,0.12), 0 ${s(2)}px ${s(8)}px rgba(0,0,0,0.06)`,
        border: `1px solid ${borderColor}`,
      }}
    >
      {/* Title bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: s(8),
          padding: `${s(12)}px ${s(16)}px`,
          background: titleBarBg,
          borderBottom: `1px solid ${borderColor}`,
        }}
      >
        {/* Window dots */}
        <div style={{ display: "flex", gap: s(7), flexShrink: 0 }}>
          {dotColors.map((c, i) => (
            <div
              key={i}
              style={{
                width: s(13),
                height: s(13),
                borderRadius: "50%",
                background: c,
              }}
            />
          ))}
        </div>

        {/* Address bar / title */}
        {variant === "chrome" && title ? (
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                background: "#F4F4F4",
                borderRadius: s(8),
                padding: `${s(6)}px ${s(20)}px`,
                fontSize: s(16),
                color: "#888",
                fontFamily: theme.fonts.body,
                maxWidth: "70%",
                textAlign: "center",
                overflow: "hidden",
                whiteSpace: "nowrap",
                textOverflow: "ellipsis",
              }}
            >
              {title}
            </div>
          </div>
        ) : title ? (
          <div
            style={{
              flex: 1,
              fontSize: s(16),
              color: titleColor,
              fontFamily: theme.fonts.body,
              textAlign: "center",
              fontWeight: 600,
              overflow: "hidden",
              whiteSpace: "nowrap",
              textOverflow: "ellipsis",
            }}
          >
            {title}
          </div>
        ) : null}
      </div>

      {/* Content area */}
      <div
        style={{
          background: bgColor,
          padding: s(24),
          minHeight: s(200),
        }}
      >
        {children}
      </div>
    </div>
  );
};
