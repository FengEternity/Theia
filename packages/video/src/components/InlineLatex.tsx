import katex from "katex";

type Segment = { type: "text" | "latex"; content: string };

function consumeBraces(text: string, pos: number): number {
  let i = pos;
  let depth = 0;
  while (i < text.length) {
    if (text[i] === "{") depth++;
    else if (text[i] === "}") {
      depth--;
      if (depth === 0) return i + 1;
    }
    i++;
  }
  return i;
}

function consumeLatexExpr(text: string, pos: number): number {
  let i = pos;
  while (i < text.length) {
    if (text[i] === "\\" && i + 1 < text.length && /[a-zA-Z]/.test(text[i + 1])) {
      i++;
      while (i < text.length && /[a-zA-Z]/.test(text[i])) i++;
      while (i < text.length && text[i] === "{") i = consumeBraces(text, i);
    } else if (text[i] === "_" || text[i] === "^") {
      i++;
      if (i < text.length && text[i] === "{") {
        i = consumeBraces(text, i);
      } else if (i < text.length && /[a-zA-Z0-9]/.test(text[i])) {
        i++;
      }
    } else if (text[i] === " " && i + 1 < text.length && text[i + 1] === "\\") {
      i++;
    } else {
      break;
    }
  }
  return i;
}

/**
 * Parse mixed text containing raw LaTeX commands into segments.
 * Supports both `$...$` delimiters and bare `\command` detection.
 */
export function parseLatexSegments(text: string): Segment[] {
  if (text.includes("\\(") || text.includes("\\[")) {
    return splitByDelimiters(text);
  }
  if (text.includes("$")) {
    return splitByDollarSign(text);
  }
  return splitByRawCommands(text);
}

function splitByDelimiters(text: string): Segment[] {
  const segments: Segment[] = [];
  const re = /\\\((.+?)\\\)|\\\[(.+?)\\\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      segments.push({ type: "text", content: text.slice(last, m.index) });
    }
    segments.push({ type: "latex", content: m[1] ?? m[2] });
    last = m.index + m[0].length;
  }
  if (last < text.length) {
    segments.push({ type: "text", content: text.slice(last) });
  }
  return segments;
}

function splitByDollarSign(text: string): Segment[] {
  const segments: Segment[] = [];
  const parts = text.split(/(\$[^$]+\$)/g);
  for (const part of parts) {
    if (part.startsWith("$") && part.endsWith("$") && part.length > 2) {
      segments.push({ type: "latex", content: part.slice(1, -1) });
    } else if (part) {
      segments.push({ type: "text", content: part });
    }
  }
  return segments;
}

function splitByRawCommands(text: string): Segment[] {
  const segments: Segment[] = [];
  let i = 0;
  let buf = "";

  while (i < text.length) {
    if (text[i] === "\\" && i + 1 < text.length && /[a-zA-Z]/.test(text[i + 1])) {
      if (buf) {
        segments.push({ type: "text", content: buf });
        buf = "";
      }
      const end = consumeLatexExpr(text, i);
      segments.push({ type: "latex", content: text.slice(i, end) });
      i = end;
    } else {
      buf += text[i];
      i++;
    }
  }

  if (buf) segments.push({ type: "text", content: buf });
  return segments;
}

function renderInlineKatex(latex: string): string | null {
  try {
    return katex.renderToString(latex, { displayMode: false, throwOnError: false, output: "html" });
  } catch {
    return null;
  }
}

type InlineLatexProps = {
  text: string;
  fontSize?: number;
  color?: string;
  lineHeight?: number;
  fontFamily?: string;
  textAlign?: "left" | "center" | "right";
};

/**
 * Renders text with inline LaTeX expressions.
 * Detects `$...$` delimiters or bare `\command` sequences and renders them via KaTeX.
 */
export const InlineLatex: React.FC<InlineLatexProps> = ({
  text,
  fontSize = 28,
  color = "#cbd5e1",
  lineHeight = 1.7,
  fontFamily = "system-ui, sans-serif",
  textAlign = "left",
}) => {
  if (!text) return null;
  const segments = parseLatexSegments(text);

  return (
    <p style={{ color, fontSize, lineHeight, fontFamily, textAlign }}>
      {segments.map((seg, i) => {
        if (seg.type === "latex") {
          const html = renderInlineKatex(seg.content);
          if (html) {
            return (
              <span
                key={i}
                style={{ display: "inline-block", verticalAlign: "middle" }}
                dangerouslySetInnerHTML={{ __html: html }}
              />
            );
          }
          return <span key={i} style={{ fontStyle: "italic", fontFamily: "'Times New Roman', serif" }}>{seg.content}</span>;
        }
        return <span key={i}>{seg.content}</span>;
      })}
    </p>
  );
};
