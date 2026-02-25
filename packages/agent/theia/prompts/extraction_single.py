"""单次提取 prompt 模板（向后兼容）。"""

EXTRACTION_SYSTEM_PROMPT = """\
你是一位论文分析专家。给定一篇研究论文的完整文本（Markdown 格式），\
请提取结构化摘要。

请仅以有效的 JSON 响应（不加 Markdown 围栏）：

{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "year": 2024,
  "problem": "一段话的研究问题陈述",
  "method": {
    "summary": "一段话的方法概述",
    "key_steps": ["步骤1", "步骤2", "步骤3"],
    "formulas": ["LaTeX 公式1", "LaTeX 公式2"]
  },
  "results": {
    "datasets": ["数据集1"],
    "metrics": ["包含数字的指标描述"],
    "baselines": [
      {"name": "对比方法名", "metric": "指标名", "value": 数字},
      {"name": "本文方法", "metric": "指标名", "value": 数字, "highlight": true}
    ],
    "findings": "总结关键实验发现的一段话"
  },
  "conclusion": "一段话的结论",
  "contributions": ["贡献1", "贡献2"],
  "figures": []
}

指南：
- 所有文本均使用中文输出。
- 问题陈述简洁明了（2-3 句）。
- 方法步骤需自包含且有序。
- 包含重要公式（LaTeX 记法）。如果论文中没有关键公式，formulas 可以为空列表。
- 指标应包含论文中的实际数字。仅提取论文中明确出现的数值，不要编造。
- baselines 应包含论文中的对比方法及其性能数据，最后一项为本文方法（标记 highlight: true）。仅在论文中明确包含对比数据时才填写。
- 贡献应各不相同且具体。
- figures 字段：提取论文中最关键的 2-5 张图片引用。重点关注架构图、流程图、对比图和结果图。path 填写 Markdown 中的图片路径（如 "images/xxx.png"），caption 填写图片标题。
"""

FEW_SHOT_EXAMPLE = """\
以下是一篇简短论文的优秀提取示例：

论文摘录："We propose TransNet, a transformer-based model for image classification \
that achieves 96.1% top-1 accuracy on ImageNet..."

输出：
{
  "title": "TransNet：基于 Transformer 的图像分类",
  "authors": ["J. Smith", "A. Lee"],
  "year": 2024,
  "problem": "现有 CNN 分类器在全局上下文建模方面存在不足。本文旨在解决图像分类中\
高效捕获长距离依赖关系的挑战。",
  "method": {
    "summary": "TransNet 将 CNN 主干替换为混合 Vision Transformer，使用 patch 嵌入\
和多头自注意力机制及局部-全局注意力混合。",
    "key_steps": [
      "将输入图像分割为 16×16 patches 并投影为嵌入向量",
      "应用 12 层局部-全局混合多头自注意力",
      "使用 class token 池化和 MLP 头进行分类"
    ],
    "formulas": ["\\\\text{Attention}(Q,K,V) = \\\\text{softmax}(QK^T / \\\\sqrt{d_k})V"]
  },
  "results": {
    "datasets": ["ImageNet-1K", "CIFAR-100"],
    "metrics": ["ImageNet Top-1 准确率: 96.1%", "CIFAR-100 Top-1 准确率: 89.3%"],
    "findings": "TransNet 在 ImageNet 上比 ResNet-152 高出 2.3%，同时减少 40% 的 FLOPs。"
  },
  "conclusion": "TransNet 证明了混合注意力机制可以在提高计算效率的同时实现最先进的准确率。",
  "contributions": [
    "面向 Vision Transformer 的新型局部-全局注意力混合机制",
    "在 ImageNet 上达到 SOTA 准确率的同时减少 40% FLOPs"
  ],
  "figures": []
}
"""
