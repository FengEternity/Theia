"""Pass 2 深度提取 prompt 模板。"""

PASS2_PROMPT = """\
你是一位论文分析专家。你已经对论文进行了快速扫描，现在需要对重点章节进行深度阅读。

你之前的快速扫描结论是：
{overview_json}

请带着以下问题深度阅读提供的论文章节：
{reading_focus}

请深入分析每个问题，仔细推理后，输出一个**纯 JSON 对象**（不加 Markdown 围栏、不加额外文字）：

{{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "year": 2024,
  "problem": "2-3 句的研究问题陈述，比快速扫描更具体",
  "method": {{
    "summary": "一段话的方法概述，需要涵盖核心创新点",
    "key_steps": ["详细步骤1", "详细步骤2", "详细步骤3", "详细步骤4"],
    "formulas": ["LaTeX 公式1", "LaTeX 公式2"],
    "component_relations": [
      {{"source": "组件A", "target": "组件B", "relation": "A的输出传入B"}}
    ]
  }},
  "results": {{
    "datasets": ["数据集1"],
    "metrics": ["包含实际数字的指标描述"],
    "baselines": [
      {{"name": "对比方法名", "metric": "指标名", "value": 数字或null, "dataset": "数据集名"}},
      {{"name": "本文方法", "metric": "指标名", "value": 数字或null, "highlight": true, "dataset": "数据集名"}}
    ],
    "findings": "总结关键实验发现，包括消融实验中的重要结论"
  }},
  "conclusion": "一段话的结论",
  "contributions": ["贡献1", "贡献2"],
  "key_insights": [
    "阅读后获得的关键洞察1（方法为什么有效）",
    "关键洞察2（与先前工作相比的根本区别）",
    "关键洞察3（实验中值得注意的发现）"
  ],
  "key_concepts": [
    {{
      "term": "核心术语（如 Multi-Head Attention）",
      "definition": "一句话通俗定义（面向非专业观众）",
      "related_terms": ["关联术语1", "关联术语2"]
    }}
  ],
  "analogies": [
    {{
      "concept": "论文中的技术概念",
      "analogy": "日常生活类比（如'注意力机制就像聚光灯'）",
      "mapping": "为什么这个类比成立"
    }}
  ],
  "code_snippets": ["算法伪代码或关键代码片段"],
  "audience_takeaways": [
    "面向普通观众的一句话要点（不使用术语）"
  ],
  "figures": []
}}

指南：
- 所有文本均使用中文输出。
- 带着上面的问题去阅读，确保每个问题都能在提取结果中找到答案。
- method.key_steps 至少 3-5 步，每步应自包含且信息丰富。
- method.key_steps 的每步写成"动作+效果"格式，便于视频中逐步展示（如"将输入序列分成多个头 → 每个头独立计算注意力"）。
- method.component_relations：提取方法中组件间的数据流或依赖关系。只在方法有清晰的模块化结构时填写（如 Encoder → Decoder → Output Layer）。线性流程不需要填写（用 key_steps 表达即可）。
- 包含论文中最重要的 1-3 个公式（LaTeX 格式）。无关键公式则留空。
- 指标只提取论文中明确出现的数值，不要编造。
- baselines 包含论文中的对比方法及性能数据，仅在论文中有对比时填写。value 必须是数字或 null（无明确数值时用 null，不要用字符串）。多数据集时用 dataset 字段区分。
- results.baselines：从文字中提取所有可找到的对比数据。如果文字中提到"详见 Table X"但没有给出具体数字，在 findings 中注明"关键数据在 Table X 图表中"。
- key_insights 是深度阅读的精华：方法为什么有效、与先前工作的根本区别、实验中的意外发现等。
- key_concepts：提取 3-5 个论文中的核心术语并给出通俗定义。定义面向没有专业背景的观众，要直觉化而非学术化。如果论文本身就是定义新概念，务必提取。
- analogies：尝试提取 1-3 个技术概念的日常类比。优先使用论文自己提出的类比；如果论文没有，则基于方法本质创造恰当的类比。只在类比确实恰当时填写，不要强行类比。
- code_snippets：如果论文包含算法伪代码或关键代码片段，原样提取。不要编造代码。
- audience_takeaways：用 3-5 句"没有专业背景的人也能听懂"的话总结这篇论文。不使用术语，用直觉和类比表达。
- figures 字段：提取论文中最关键的 2-5 张图片引用。path 填 Markdown 图片路径，caption 填图片标题。

### 字段优先级（token 不足时按此顺序省略）：

**必填**（缺失视为提取失败）：
title, authors, problem, method.summary, method.key_steps, results.findings, conclusion

**重要**（尽量填写）：
results.baselines, results.metrics, results.datasets, contributions, key_insights, method.formulas

**增强**（有则提取，无则留空数组）：
key_concepts, analogies, audience_takeaways, method.component_relations, code_snippets

请对以下论文章节进行深度阅读和信息提取：

{focused_text}
"""
