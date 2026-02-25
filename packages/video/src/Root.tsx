import { Composition } from "remotion";
import { PaperVideo } from "./PaperVideo";
import { VideoScript } from "./types/script";

const academicScript: VideoScript = {
  meta: { fps: 30, width: 1920, height: 1080, theme: "academic" },
  scenes: [
    {
      type: "title",
      durationInFrames: 150,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        title: "Sample Paper Title",
        authors: ["Author A", "Author B"],
        year: 2024,
      },
    },
    {
      type: "overview",
      durationInFrames: 300,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        problem: "This paper addresses the challenge of...",
        contributions: [
          "Contribution one",
          "Contribution two",
          "Contribution three",
        ],
      },
    },
    {
      type: "method",
      durationInFrames: 450,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        summary: "We propose a novel approach...",
        steps: ["Step 1: Data collection", "Step 2: Model training", "Step 3: Evaluation"],
        formulas: ["E = mc^2"],
      },
    },
    {
      type: "result",
      durationInFrames: 300,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        datasets: ["ImageNet", "COCO"],
        metrics: ["Accuracy: 95.2%", "F1: 0.93"],
        findings: "Our method outperforms baselines by 3.2% on average.",
      },
    },
    {
      type: "conclusion",
      durationInFrames: 180,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        conclusion: "This work demonstrates that...",
        contributions: ["Key takeaway one", "Key takeaway two"],
      },
    },
  ],
};

const popsciScript: VideoScript = {
  meta: { fps: 30, width: 1920, height: 1080, theme: "popsci" },
  scenes: [
    {
      type: "title",
      durationInFrames: 150,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        title: "Transformer 注意力机制：让 AI 学会「看重点」",
        authors: ["AI 科普频道"],
        year: 2025,
      },
    },
    {
      type: "character_talk",
      durationInFrames: 240,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        text: "大家好！今天我们来聊一个超级重要的 AI 技术 —— Transformer 的注意力机制。听起来很高大上？别怕，我用最简单的方式给你讲明白！",
        expression: "explaining",
      },
    },
    {
      type: "concept",
      durationInFrames: 300,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        title: "什么是注意力机制？",
        definition: "注意力机制让模型能够自动关注输入中最重要的部分，就像你阅读时眼睛会自动聚焦到关键词一样。",
        keywords: ["Self-Attention", "Query", "Key", "Value"],
      },
    },
    {
      type: "analogy",
      durationInFrames: 300,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        concept: { label: "注意力机制", description: "模型通过计算 Query 和 Key 的相似度来决定关注哪些信息" },
        analogy: { label: "图书馆找书", description: "你带着问题(Query)去图书馆，对比书名标签(Key)，找到最相关的书获取内容(Value)" },
        mapping: "Query ≈ 你的问题, Key ≈ 书的标签, Value ≈ 书的内容",
      },
    },
    {
      type: "comparison",
      durationInFrames: 300,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        items: [
          { name: "RNN", features: { "并行计算": "❌ 不支持", "长距离依赖": "⚠️ 困难", "训练速度": "🐌 慢", "效果": "⭐⭐⭐" } },
          { name: "Transformer", features: { "并行计算": "✅ 完全支持", "长距离依赖": "✅ 轻松", "训练速度": "🚀 快", "效果": "⭐⭐⭐⭐⭐" } },
        ],
        featureLabels: ["并行计算", "长距离依赖", "训练速度", "效果"],
      },
    },
    {
      type: "summary_card",
      durationInFrames: 240,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        title: "今日要点回顾",
        points: [
          "注意力机制让模型学会了「看重点」",
          "Query-Key-Value 三兄弟各司其职",
          "Transformer 用并行计算大幅加速训练",
          "这是 GPT、BERT 等大模型的核心基础",
        ],
      },
    },
    {
      type: "character_talk",
      durationInFrames: 180,
      narration: "",
      audioFile: null,
      wordTimings: [],
      data: {
        text: "怎么样，是不是比你想象的简单？点赞收藏，下次我们继续聊更多 AI 干货！",
        expression: "happy",
      },
    },
  ],
};

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="PaperVideo"
        component={PaperVideo}
        durationInFrames={1380}
        fps={academicScript.meta.fps}
        width={academicScript.meta.width}
        height={academicScript.meta.height}
        defaultProps={{ script: academicScript }}
        calculateMetadata={({ props }) => {
          const totalFrames = props.script.scenes.reduce(
            (sum: number, s: { durationInFrames: number }) => sum + s.durationInFrames,
            0,
          );
          return {
            durationInFrames: totalFrames,
            fps: props.script.meta.fps,
            width: props.script.meta.width,
            height: props.script.meta.height,
          };
        }}
      />
      <Composition
        id="PopsciVideo"
        component={PaperVideo}
        durationInFrames={1710}
        fps={popsciScript.meta.fps}
        width={popsciScript.meta.width}
        height={popsciScript.meta.height}
        defaultProps={{ script: popsciScript }}
        calculateMetadata={({ props }) => {
          const totalFrames = props.script.scenes.reduce(
            (sum: number, s: { durationInFrames: number }) => sum + s.durationInFrames,
            0,
          );
          return {
            durationInFrames: totalFrames,
            fps: props.script.meta.fps,
            width: props.script.meta.width,
            height: props.script.meta.height,
          };
        }}
      />
    </>
  );
};
