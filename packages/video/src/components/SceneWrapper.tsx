import { Component } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

class SceneErrorBoundary extends Component<
  { children: React.ReactNode },
  { hasError: boolean; errorMsg: string }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, errorMsg: "" };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, errorMsg: error.message };
  }

  render() {
    if (this.state.hasError) {
      return (
        <AbsoluteFill
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: "#0f172a",
            gap: 16,
          }}
        >
          <div style={{ color: "#f87171", fontSize: 18, fontWeight: 600 }}>场景渲染失败</div>
          <div style={{ color: "#94a3b8", fontSize: 13, maxWidth: "70%", textAlign: "center" }}>
            {this.state.errorMsg}
          </div>
        </AbsoluteFill>
      );
    }
    return this.props.children;
  }
}

type SceneWrapperProps = {
  children: React.ReactNode;
  durationInFrames: number;
  exitFrames?: number;
};

/**
 * 为场景内容添加退出动画（最后 N 帧渐出+轻微上移）。
 * 包含错误边界，防止场景数据异常时整个视频崩溃。
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
    <SceneErrorBoundary>
      <AbsoluteFill
        style={{
          opacity: exitOpacity,
          transform: `translateY(${exitY}px)`,
        }}
      >
        {children}
      </AbsoluteFill>
    </SceneErrorBoundary>
  );
};
