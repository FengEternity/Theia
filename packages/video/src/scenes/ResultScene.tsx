import { Img, interpolate, useCurrentFrame } from "remotion";
import type { ResultData } from "../types/script";
import { DataTable } from "../components/DataTable";
import { BarChart } from "../components/BarChart";
import { ComparisonBadge } from "../components/ComparisonBadge";
import { DynamicBackground } from "../components/DynamicBackground";
import { useScale } from "../hooks/useScale";
import { useTheme, resolveSceneStyle } from "../themes";
import { getIcon } from "../utils/characterAssets";

export const ResultScene: React.FC<{
  data: Record<string, unknown>;
  durationInFrames: number;
}> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { s, pad, isPortrait } = useScale();
  const theme = useTheme();
  const scene = resolveSceneStyle(theme, "result");
  const { datasets, metrics, findings, baselines } = data as unknown as ResultData & {
    baselines?: Array<{ name: string; metric: string; value: number | null; highlight?: boolean; dataset?: string }>;
  };

  const headerOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const metricsRows = (metrics ?? []).filter((m): m is string => typeof m === "string" && m.length > 0).map((m) => {
    const colonParts = m.split(/[:：]/);
    if (colonParts.length >= 2) return [colonParts[0].trim(), colonParts.slice(1).join(":").trim()];
    const eqParts = m.split(/\s*=\s*/);
    if (eqParts.length >= 2) return [eqParts[0].trim(), eqParts.slice(1).join("=").trim()];
    const numMatch = m.match(/^(.+?)\s+([\d.]+%?\s*)$/);
    if (numMatch) return [numMatch[1].trim(), numMatch[2].trim()];
    return [m, ""];
  });

  const hasChart = (baselines && baselines.length > 0) || metricsRows.length > 0;
  const hasFindings = findings && findings.length > 0;
  const findingsLen = (findings || "").length;
  const findingsFontSize = s(findingsLen > 200 ? 34 : findingsLen > 100 ? 38 : 42);
  const bodyDir = isPortrait ? "column" as const : "row" as const;

  const showDecorations = theme.character.showDecorationIcons;
  const accentColor = scene.accentColor;
  const accentGradient = scene.accentGradient;

  return (
    <DynamicBackground
      colors={scene.gradientStops}
      accentColor={scene.accentRgb}
      particleCount={theme.decoration.showParticles ? 10 : 0}
      showOrb={theme.decoration.showOrb}
      mode={theme.decoration.backgroundStyle === "flat" ? "flat" : undefined}
    >
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", flexDirection: "column", justifyContent: isPortrait ? "center" : "flex-start", padding: pad, fontFamily: theme.fonts.body }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: s(20), marginBottom: s(20), opacity: headerOpacity, flexWrap: "wrap" as const, flexShrink: 0, justifyContent: isPortrait ? "center" : "flex-start" }}>
          <div style={{ display: "flex", alignItems: "center", gap: s(14) }}>
            {showDecorations ? (
              <Img src={getIcon("rocket")} style={{ width: s(32), height: s(32) }} />
            ) : (
              <div style={{ width: s(5), height: s(32), background: accentGradient, borderRadius: 3 }} />
            )}
            <span style={{ color: accentColor, fontSize: s(30), fontWeight: 600, fontFamily: theme.fonts.title, textTransform: "uppercase" as const, letterSpacing: 4 }}>实验结果</span>
          </div>
          {datasets && datasets.length > 0 && (
            <div style={{ display: "flex", gap: s(10), flexWrap: "wrap" as const, justifyContent: isPortrait ? "center" : "flex-start" }}>
              {datasets.map((d, i) => (
                <div key={i} style={{ background: `${accentColor}14`, border: `1px solid ${accentColor}33`, borderRadius: s(8), padding: `${s(5)}px ${s(16)}px`, color: accentColor, fontSize: s(18), fontFamily: theme.fonts.body, fontWeight: 600 }}>{d}</div>
              ))}
            </div>
          )}
        </div>

        {/* Body */}
        <div style={{ display: "flex", flexDirection: bodyDir, gap: s(isPortrait ? 30 : 50), flex: isPortrait ? undefined : 1, alignItems: "center" }}>
          {hasChart && (
            <div style={{ width: isPortrait ? "100%" : "58%", display: "flex", flexDirection: "column", justifyContent: "center", flexShrink: 0 }}>
              {baselines && baselines.filter((b) => b.value != null).length > 0 ? (
                <BarChart bars={baselines.filter((b) => b.value != null).map((b) => ({ label: b.dataset ? `${b.name} (${b.dataset})` : b.name, value: b.value!, highlight: b.highlight }))} unit={` ${baselines[0]?.metric ?? ""}`} delay={20} accentColor={theme.colors.primary} highlightColor={accentColor} />
              ) : metricsRows.length <= 4 && metricsRows.every(([, v]) => v) ? (
                <div style={{ display: "flex", gap: s(16), flexWrap: "wrap" as const, justifyContent: "center" }}>
                  {metricsRows.map(([metric, value], i) => (
                    <ComparisonBadge key={i} metric={metric} value={value} isHighlight={i === 0} delay={20 + i * 12} />
                  ))}
                </div>
              ) : (
                <DataTable headers={["指标", "结果"]} rows={metricsRows} delay={20} accentColor={accentColor} />
              )}
            </div>
          )}

          {hasFindings && (
            <div style={{ flex: isPortrait ? undefined : 2, width: isPortrait ? "100%" : undefined, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: isPortrait ? "center" : "flex-start", opacity: interpolate(frame, [40, 70], [0, 1], { extrapolateRight: "clamp" }), transform: isPortrait ? `translateY(${interpolate(frame, [40, 70], [20, 0], { extrapolateRight: "clamp" })}px)` : `translateX(${interpolate(frame, [40, 70], [30, 0], { extrapolateRight: "clamp" })}px)` }}>
              <div style={{ width: s(50), height: s(4), background: `linear-gradient(90deg, ${accentColor}, ${theme.colors.accent})`, borderRadius: 2, marginBottom: s(20) }} />
              <p style={{ color: theme.colors.text, fontSize: findingsFontSize, fontFamily: theme.fonts.body, lineHeight: 1.65, textAlign: isPortrait ? "center" as const : "left" as const }}>{findings}</p>
            </div>
          )}
        </div>
      </div>
    </DynamicBackground>
  );
};
