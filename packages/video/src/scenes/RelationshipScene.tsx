import { Img, spring, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { useTheme } from "../themes";
import { useScale } from "../hooks/useScale";
import { getIcon } from "../utils/characterAssets";

type NodeData = { id: string; label: string; color?: string; description?: string };
type EdgeData = { from: string; to: string; label?: string };

type RelationshipSceneProps = {
  data: Record<string, unknown>;
  durationInFrames: number;
};

export const RelationshipScene: React.FC<RelationshipSceneProps> = ({ data, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();
  const { s, isPortrait, width, height } = useScale();

  const nodes = (data.nodes as NodeData[]) ?? [];
  const edges = (data.edges as EdgeData[]) ?? [];

  const centerX = width / 2;
  const centerY = height / 2;
  const radius = isPortrait ? Math.min(width, height) * 0.28 : Math.min(width, height) * 0.3;

  const nodePositions = nodes.map((_, i) => {
    const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
    return {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    };
  });

  const NODE_SIZE = s(isPortrait ? 90 : 100);
  const showDecorations = theme.character.showDecorationIcons;
  const NODE_ICONS = ["gear", "code", "brain", "rocket", "lightbulb"] as const;

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      {/* SVG edges */}
      <svg
        style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }}
        viewBox={`0 0 ${width} ${height}`}
      >
        {edges.map((edge, i) => {
          const fromIdx = nodes.findIndex((n) => n.id === edge.from);
          const toIdx = nodes.findIndex((n) => n.id === edge.to);
          if (fromIdx < 0 || toIdx < 0) return null;

          const from = nodePositions[fromIdx];
          const to = nodePositions[toIdx];

          const edgeDelay = 15 + Math.max(fromIdx, toIdx) * 15;
          const drawProgress = interpolate(frame - edgeDelay, [0, 20], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          const dx = to.x - from.x;
          const dy = to.y - from.y;
          const len = Math.sqrt(dx * dx + dy * dy);
          const offsetFrom = NODE_SIZE / 2 + s(4);
          const offsetTo = NODE_SIZE / 2 + s(4);
          const nx = dx / len;
          const ny = dy / len;

          const x1 = from.x + nx * offsetFrom;
          const y1 = from.y + ny * offsetFrom;
          const x2 = from.x + (dx - nx * offsetTo) * drawProgress + nx * offsetFrom * (1 - drawProgress);
          const y2 = from.y + (dy - ny * offsetTo) * drawProgress + ny * offsetFrom * (1 - drawProgress);

          const midX = (from.x + to.x) / 2;
          const midY = (from.y + to.y) / 2 - s(16);

          return (
            <g key={`edge-${i}`}>
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={theme.colors.textSecondary}
                strokeWidth={s(3)}
                strokeDasharray="none"
                opacity={drawProgress * 0.6}
              />
              {drawProgress > 0.9 && (
                <polygon
                  points={`${to.x - nx * offsetTo},${to.y - ny * offsetTo} ${to.x - nx * (offsetTo + s(12)) + ny * s(7)},${to.y - ny * (offsetTo + s(12)) - nx * s(7)} ${to.x - nx * (offsetTo + s(12)) - ny * s(7)},${to.y - ny * (offsetTo + s(12)) + nx * s(7)}`}
                  fill={theme.colors.textSecondary}
                  opacity={0.6}
                />
              )}
              {edge.label && drawProgress > 0.5 && (
                <text
                  x={midX}
                  y={midY}
                  textAnchor="middle"
                  fontSize={s(20)}
                  fill={theme.colors.textSecondary}
                  fontFamily={theme.fonts.body}
                  opacity={interpolate(drawProgress, [0.5, 1], [0, 1])}
                >
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Nodes */}
      {nodes.map((node, i) => {
        const pos = nodePositions[i];
        const nodeProgress = spring({
          frame: frame - i * 12 - 5,
          fps,
          config: { mass: 0.4, stiffness: 160, damping: 11 },
        });

        const nodeColor = node.color || theme.colors.primary;

        return (
          <div
            key={node.id}
            style={{
              position: "absolute",
              left: pos.x - NODE_SIZE / 2,
              top: pos.y - NODE_SIZE / 2,
              width: NODE_SIZE,
              height: NODE_SIZE,
              borderRadius: "50%",
              background: nodeColor,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              transform: `scale(${nodeProgress})`,
              opacity: nodeProgress,
              boxShadow: `0 ${s(4)}px ${s(16)}px ${nodeColor}44`,
            }}
          >
            {showDecorations && (
              <Img
                src={getIcon(NODE_ICONS[i % NODE_ICONS.length])}
                style={{
                  width: s(28),
                  height: s(28),
                  marginBottom: s(2),
                  filter: "brightness(0) invert(1)",
                  opacity: 0.7,
                }}
              />
            )}
            <span
              style={{
                fontSize: s(isPortrait ? 18 : showDecorations ? 18 : 22),
                fontWeight: 700,
                fontFamily: theme.fonts.title,
                color: "#FFFFFF",
                textAlign: "center",
                lineHeight: 1.2,
                padding: `0 ${s(8)}px`,
              }}
            >
              {node.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};
