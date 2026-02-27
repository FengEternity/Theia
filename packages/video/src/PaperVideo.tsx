import "katex/dist/katex.min.css";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import { TitleScene } from "./scenes/TitleScene";
import { OverviewScene } from "./scenes/OverviewScene";
import { MethodScene } from "./scenes/MethodScene";
import { FormulaScene } from "./scenes/FormulaScene";
import { FigureScene } from "./scenes/FigureScene";
import { ResultScene } from "./scenes/ResultScene";
import { ConclusionScene } from "./scenes/ConclusionScene";
import { ConceptScene } from "./scenes/ConceptScene";
import { AnalogyScene } from "./scenes/AnalogyScene";
import { RelationshipScene } from "./scenes/RelationshipScene";
import { DemoScene } from "./scenes/DemoScene";
import { ComparisonScene } from "./scenes/ComparisonScene";
import { CharacterTalkScene } from "./scenes/CharacterTalkScene";
import { SummaryCardScene } from "./scenes/SummaryCardScene";
import { CodeDemoScene } from "./scenes/CodeDemoScene";
import { ProgressBar } from "./components/ProgressBar";
import { SceneLabel } from "./components/SceneLabel";
import { SceneWrapper } from "./components/SceneWrapper";
import { Subtitle } from "./components/Subtitle";
import { ThemeProvider, getTheme } from "./themes";
import { ensureFontsLoaded } from "./fonts";
import type { VideoScript, SceneType } from "./types/script";

const sceneComponentMap: Record<string, React.FC<{ data: Record<string, unknown>; durationInFrames: number }>> = {
  title: TitleScene,
  overview: OverviewScene,
  method: MethodScene,
  formula: FormulaScene,
  figure: FigureScene,
  result: ResultScene,
  conclusion: ConclusionScene,
  concept: ConceptScene,
  analogy: AnalogyScene,
  relationship: RelationshipScene,
  demo: DemoScene,
  comparison: ComparisonScene,
  character_talk: CharacterTalkScene,
  summary_card: SummaryCardScene,
  code_demo: CodeDemoScene,
};

const TRANSITION_CONFIG: Record<string, { frames: number; type: "fade" | "slide" | "wipe" }> = {
  "title->overview": { frames: 20, type: "fade" },
  "overview->method": { frames: 25, type: "slide" },
  "method->formula": { frames: 15, type: "fade" },
  "formula->figure": { frames: 15, type: "fade" },
  "figure->result": { frames: 20, type: "wipe" },
  "result->conclusion": { frames: 25, type: "fade" },
};
const DEFAULT_TRANSITION = { frames: 15, type: "fade" as const };

function getTransition(prevType: string, nextType: string) {
  const key = `${prevType}->${nextType}`;
  const config = TRANSITION_CONFIG[key] ?? DEFAULT_TRANSITION;

  const presentation = config.type === "slide"
    ? slide({ direction: "from-right" })
    : config.type === "wipe"
      ? wipe({ direction: "from-left" })
      : fade();

  return { presentation: presentation as any, frames: config.frames };
}

export const PaperVideo: React.FC<{ script: VideoScript }> = ({ script }) => {
  ensureFontsLoaded();
  const theme = getTheme(script.meta.theme ?? "academic");

  return (
    <ThemeProvider theme={theme}>
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <TransitionSeries>
        {script.scenes.map((scene, i) => {
          const SceneComponent = sceneComponentMap[scene.type];
          if (!SceneComponent) return null;

          const transition = i > 0
            ? getTransition(script.scenes[i - 1].type, scene.type)
            : null;

          return [
            transition && (
              <TransitionSeries.Transition
                key={`t-${i}`}
                presentation={transition.presentation}
                timing={linearTiming({ durationInFrames: transition.frames })}
              />
            ),
            <TransitionSeries.Sequence
              key={`s-${i}`}
              durationInFrames={scene.durationInFrames}
            >
              <SceneWrapper durationInFrames={scene.durationInFrames}>
                <SceneComponent
                  data={scene.data}
                  durationInFrames={scene.durationInFrames}
                  {...(scene.choreography && scene.choreography.length > 0
                    ? { choreography: scene.choreography }
                    : {})}
                />
                <SceneLabel
                  sceneType={scene.type}
                  durationInFrames={scene.durationInFrames}
                />
                {scene.wordTimings && scene.wordTimings.length > 0 && (
                  <Subtitle
                    wordTimings={scene.wordTimings}
                    audioStartFrame={Math.round(script.meta.fps * 0.5)}
                  />
                )}
                {scene.audioFile && (
                  <Audio src={staticFile(scene.audioFile)} />
                )}
              </SceneWrapper>
            </TransitionSeries.Sequence>,
          ];
        })}
      </TransitionSeries>
      <Audio
        src={staticFile("bgm.wav")}
        volume={(f) => {
          const { durationInFrames: total } = script.scenes.reduce(
            (acc, s) => ({ durationInFrames: acc.durationInFrames + s.durationInFrames }),
            { durationInFrames: 0 },
          );
          const fadeOutStart = total - 150;
          if (f >= fadeOutStart) {
            const prog = (f - fadeOutStart) / 150;
            return Math.max(0, 0.15 * (1 - prog));
          }
          if (f < 30) return 0.15 * (f / 30);
          return 0.15;
        }}
      />
      <ProgressBar color={theme.colors.primary} height={4} />
    </AbsoluteFill>
    </ThemeProvider>
  );
};
