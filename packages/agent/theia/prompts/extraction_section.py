"""分段提取与融合 prompt 模板。"""

PASS2_SECTION_PROMPT = """\
你是一位论文分析专家。你正在分段阅读一篇论文的 [{section_label}] 部分。

论文概览（来自快速扫描）：
- 论文类型: {paper_type}
- 核心思想: {core_idea}
{context_block}
请从当前章节中提取关键信息，输出**纯 JSON 对象**（不加 Markdown 围栏）：

{{
  "section_summary": "本章节的核心内容（2-3句话）",
  "title": "论文标题（如果出现在本章节，否则为空字符串）",
  "authors": [],
  "year": null,
  "problem": "研究问题（如果本章节涉及，否则为空字符串）",
  "method_summary": "方法描述（如果本章节涉及）",
  "method_steps": ["方法步骤"],
  "formulas": ["LaTeX 公式"],
  "datasets": ["数据集名称"],
  "metrics": ["含数字的指标描述"],
  "baselines": [
    {{"name": "方法名", "metric": "指标名", "value": 0或null, "highlight": false, "dataset": "数据集名"}}
  ],
  "findings": "实验发现",
  "contributions": ["贡献"],
  "key_insights": ["关键洞察"],
  "conclusion": "结论（如果本章节涉及）"
}}

指南：
- 所有文本使用中文输出。
- 只填写本章节中明确出现的信息，没有的字段留空字符串或空列表。
- 数值指标只提取原文中出现的，不要编造。value 必须是数字或 null（无明确数值时用 null，不要用字符串）。
- section_summary 必须填写，简明扼要概括本章节核心内容。

当前章节 [{section_label}] 内容：

{section_text}
"""

PASS2_MERGE_PROMPT = """\
你是一位论文分析专家。以下是对同一篇论文各章节的分段提取结果，\
请将它们融合为一个完整的论文结构化摘要。

分段提取结果：
{section_results}

请输出一个**纯 JSON 对象**（不加 Markdown 围栏）：

{{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "year": 2024,
  "problem": "2-3 句的研究问题陈述",
  "method": {{
    "summary": "方法概述（一段话，涵盖核心创新点）",
    "key_steps": ["步骤1", "步骤2", "步骤3"],
    "formulas": ["LaTeX 公式"]
  }},
  "results": {{
    "datasets": ["数据集"],
    "metrics": ["含数字的指标描述"],
    "baselines": [
      {{"name": "对比方法名", "metric": "指标名", "value": 0或null, "dataset": "数据集名"}},
      {{"name": "本文方法", "metric": "指标名", "value": 0或null, "highlight": true, "dataset": "数据集名"}}
    ],
    "findings": "关键实验发现的总结"
  }},
  "conclusion": "一段话的结论",
  "contributions": ["贡献1", "贡献2"],
  "key_insights": [
    "关键洞察1（方法为什么有效）",
    "关键洞察2（与先前工作的根本区别）"
  ]
}}

指南：
- 所有文本使用中文输出。
- 从各章节提取结果中综合信息，去重并整合。
- 方法步骤至少 3 步，从方法章节的结果中整合。
- 指标只使用原文提取的数值，不要编造。
- 贡献要具体且互不相同。
"""
