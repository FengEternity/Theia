import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

type SceneWrapperProps = {
  children: React.ReactNode;
  durationInFrames: number;
  exitFrames?: number;
};

/**
 * 为场景内容添加退出动画（最后 N 帧渐出+轻微上移）。
 */
export const SceneWrapper: React.FC<SceneWrapperProps> = ({
  children,
  durationInFrames,
  exitFrames = 15,
}) => {
  const frame = useCurrentFrame();

  const exitStart = durationInFrames - exitFrames;
  const exitOpacity = interpolate(frame, [exitStart, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitY = interpolate(frame, [exitStart, durationInFrames], [0, -12], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        opacity: exitOpacity,
        transform: `translateY(${exitY}px)`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
