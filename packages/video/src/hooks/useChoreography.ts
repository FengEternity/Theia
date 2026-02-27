import { useCurrentFrame, useVideoConfig } from "remotion";
import type { AnimationPhase } from "../types/script";

export interface ChoreographyState {
  /** Whether choreography data is available */
  hasChoreography: boolean;
  /** Current animation phase (null if between phases or no choreography) */
  currentPhase: AnimationPhase | null;
  /** Current attention mode */
  attentionMode: "voice_primary" | "visual_primary" | "synced";
  /** Elements that should be visible in the current phase */
  visibleElements: string[];
  /** Element that should be highlighted (null if none) */
  highlightElement: string | null;
  /** Current transition type */
  transitionType: string;
  /** Whether a specific element should be visible */
  isElementVisible: (elementId: string) => boolean;
  /** Whether a specific element is the highlight target */
  isElementHighlighted: (elementId: string) => boolean;
  /** Progress within the current phase (0-1) */
  phaseProgress: number;
}

/**
 * Hook that reads AnimationPhase choreography data and returns
 * the current visual state based on the current frame.
 *
 * When choreography is empty, returns a default state that makes
 * all elements visible (backward compatible with hardcoded animations).
 */
export function useChoreography(
  choreography: AnimationPhase[] | undefined,
): ChoreographyState {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentMs = (frame / fps) * 1000;

  const phases = choreography ?? [];
  const hasChoreography = phases.length > 0;

  if (!hasChoreography) {
    return {
      hasChoreography: false,
      currentPhase: null,
      attentionMode: "synced",
      visibleElements: [],
      highlightElement: null,
      transitionType: "fade_in",
      isElementVisible: () => true,
      isElementHighlighted: () => false,
      phaseProgress: 0,
    };
  }

  const currentPhase = phases.find(
    (p) => p.startMs <= currentMs && currentMs < p.endMs,
  ) ?? null;

  const cumulativeElements = new Set<string>();
  for (const phase of phases) {
    if (phase.startMs <= currentMs) {
      for (const el of phase.elementsToShow) {
        cumulativeElements.add(el);
      }
    }
  }

  const visibleElements = Array.from(cumulativeElements);
  const highlightElement = currentPhase?.highlightElement ?? null;
  const attentionMode = (currentPhase?.attentionMode ?? "synced") as
    "voice_primary" | "visual_primary" | "synced";

  let phaseProgress = 0;
  if (currentPhase) {
    const phaseDuration = currentPhase.endMs - currentPhase.startMs;
    if (phaseDuration > 0) {
      phaseProgress = Math.min(1, Math.max(0,
        (currentMs - currentPhase.startMs) / phaseDuration,
      ));
    }
  }

  return {
    hasChoreography: true,
    currentPhase,
    attentionMode,
    visibleElements,
    highlightElement,
    transitionType: currentPhase?.transitionType ?? "fade_in",
    isElementVisible: (id: string) => cumulativeElements.has(id),
    isElementHighlighted: (id: string) => highlightElement === id,
    phaseProgress,
  };
}
