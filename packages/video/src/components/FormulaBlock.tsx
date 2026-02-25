import { interpolate, useCurrentFrame } from "remotion";
import katex from "katex";

type FormulaBlockProps = {
  formula: string;
  delay?: number;
  fontSize?: number;
};

/**
 * 使用 KaTeX 渲染 LaTeX 数学公式。
 * 渲染失败时回退为显示原始 LaTeX 文本。
 */
export const FormulaBlock: React.FC<FormulaBlockProps> = ({
  formula,
  delay = 0,
  fontSize = 26,
}) => {
  const frame = useCurrentFrame();
  const localFrame = frame - delay;

  const opacity = interpolate(localFrame, [0, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scale = interpolate(localFrame, [0, 25], [0.9, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  let html: string;
  let isRendered = false;
  try {
    html = katex.renderToString(formula, {
      displayMode: true,
      throwOnError: false,
      output: "html",
    });
    isRendered = true;
  } catch {
    html = formula;
  }

  return (
    <div
      style={{
        background: "rgba(59, 130, 246, 0.08)",
        border: "1px solid rgba(59, 130, 246, 0.2)",
        borderRadius: 12,
        padding: "20px 28px",
        opacity,
        transform: `scale(${scale})`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {isRendered ? (
        <span
          style={{ fontSize, color: "#e2e8f0" }}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      ) : (
        <span
          style={{
            color: "#e2e8f0",
            fontSize,
            fontFamily: "'Times New Roman', 'Latin Modern Math', serif",
            fontStyle: "italic",
            letterSpacing: 1,
          }}
        >
          {formula}
        </span>
      )}
    </div>
  );
};
