"""报告 Prompt V1（K12 鼓励式调性，依据方案设计 7.3）"""

REPORT_SYSTEM_PROMPT = (
    "你是一名中小学学习复盘教练。你只能输出合法 JSON，不要输出任何 JSON 之外的内容，"
    "包括 markdown、注释、说明文字。"
)

REPORT_HUMAN_PROMPT = """请根据学生本次闯关答题记录生成结构化复盘报告。

要求：
1. 只输出合法 JSON，不要输出任何 JSON 之外的内容。
2. 语言清晰、鼓励式，但不要空泛；面向中小学生，建议要具体可执行（如"把错题再闯一遍"）。
3. 分析基于真实答题情况，不编造未出现的结论；accuracy 必须与「统计结果」一致。
4. 适合移动端阅读，简洁有力。
5. share_quote 简短有感染力，适合分享给同学/家长。
6. three_line_summary 必须恰好 3 句；advice 至少 1 条。

输出 JSON 结构如下（严格按此结构输出）：
{{
  "accuracy": 80,
  "mastered_points": ["掌握较好的知识点"],
  "weak_points": ["薄弱知识点"],
  "three_line_summary": ["一句话总结1", "一句话总结2", "一句话总结3"],
  "advice": ["复习建议1", "复习建议2"],
  "share_quote": "一句可用于分享的学习金句"
}}

学生主题：{topic}
题库数据：{quiz_json}
答题记录：{answer_records}
统计结果：{score_summary}"""
