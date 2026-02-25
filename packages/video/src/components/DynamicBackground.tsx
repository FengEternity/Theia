import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import React, { useMemo } from "react";
import { useTheme } from "../themes";

type Particle = {
  x: number;
  y: number;
  size: number;
  speed: number;
  opacity: number;
  phase: number;
};

type DynamicBackgroundProps = {
  /** CSS gradient colors, e.g. ["#0c1222", "#1a1f3a", "#0f172a"] */
  colors?: [string, string, string];
  /** Number of floating particles */
  particleCount?: number;
  /** Accent color for the radial glow */
  accentColor?: string;
  /** Whether to show the radial glow orb */
  showOrb?: boolean;
  /** Background rendering mode */
  mode?: "gradient" | "flat";
  children?: React.ReactNode;
};

function seededRandom(seed: number): number {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

export const DynamicBackground: React.FC<DynamicBackgroundProps> = ({
  colors,
  particleCount,
  accentColor,
  showOrb,
  mode,
  children,
}) => {
  const frame = useCurrentFrame();
  const theme = useTheme();

  const resolvedColors = colors ?? theme.colors.gradientStops;
  const resolvedParticleCount = particleCount ?? (theme.decoration.showParticles ? 12 : 0);
  const resolvedAccentColor = accentColor ?? theme.colors.accentRgb;
  const resolvedShowOrb = showOrb ?? theme.decoration.showOrb;
  const resolvedMode = mode ?? theme.decoration.backgroundStyle;

  const particles = useMemo<Particle[]>(() => {
    return Array.from({ length: resolvedParticleCount }, (_, i) => ({
      x: seededRandom(i * 3 + 1) * 100,
      y: seededRandom(i * 3 + 2) * 100,
      size: 2 + seededRandom(i * 3 + 3) * 4,
      speed: 0.3 + seededRandom(i * 3 + 4) * 0.7,
      opacity: 0.08 + seededRandom(i * 3 + 5) * 0.15,
      phase: seededRandom(i * 3 + 6) * Math.PI * 2,
    }));
  }, [resolvedParticleCount]);

  const isFlatMode = resolvedMode === "flat" || resolvedMode === "pattern";

  const gradientShift = Math.sin(frame * 0.015) * 5;
  const bg = isFlatMode
    ? resolvedColors[0]
    : `linear-gradient(160deg, ${resolvedColors[0]} 0%, ${resolvedColors[1]} ${40 + gradientShift}%, ${resolvedColors[2]} 100%)`;

  const orbOpacity = resolvedShowOrb
    ? interpolate(frame, [10, 50], [0, 0.25], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
      * (0.85 + Math.sin(frame * 0.025) * 0.15)
    : 0;

  const orbScale = 1 + Math.sin(frame * 0.012) * 0.04;

  return (
    <AbsoluteFill style={{ background: bg, overflow: "hidden" }}>
      {resolvedShowOrb && (
        <div
          style={{
            position: "absolute",
            top: "30%",
            left: "50%",
            width: 800,
            height: 800,
            borderRadius: "50%",
            background: `radial-gradient(circle, rgba(${resolvedAccentColor},0.15) 0%, transparent 70%)`,
            transform: `translate(-50%, -50%) scale(${orbScale})`,
            opacity: orbOpacity,
          }}
        />
      )}

      {particles.map((p, i) => {
        const t = frame * p.speed * 0.01;
        const px = p.x + Math.sin(t + p.phase) * 3;
        const py = p.y + Math.cos(t * 0.7 + p.phase) * 2;
        const pOpacity = p.opacity * (0.6 + Math.sin(frame * 0.03 + p.phase) * 0.4);

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${px}%`,
              top: `${py}%`,
              width: p.size,
              height: p.size,
              borderRadius: "50%",
              background: `rgba(${resolvedAccentColor},${pOpacity})`,
              filter: `blur(${p.size > 4 ? 1 : 0}px)`,
            }}
          />
        );
      })}

      {children}
    </AbsoluteFill>
  );
};
