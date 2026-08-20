"""出题 Prompt V1（K12 适配版，依据方案设计 7.1 + 已确认决策）"""

QUIZ_SYSTEM_PROMPT = (
    "你是一名专业的中小学 AI 学习教练。你只能输出合法 JSON，不要输出任何 JSON 之外的内容，"
    "包括 markdown、注释、说明文字。当提供了参考资料时，必须优先基于参考资料出题，确保知识的准确性。"
)


def format_type_ratio_instruction(question_count: int) -> str:
    """按题量给出题型配比指令（3 题 = 1:1:1，其余 = 约 3:1:1）"""
    if question_count == 3:
        return "单选题(single)、多选题(multiple)、判断题(judge) 各 1 题（1:1:1）"
    return "单选题(single)、多选题(multiple)、判断题(judge)，比例约为 3:1:1"


QUIZ_HUMAN_PROMPT = """请根据学生提供的学习内容，生成一组用于小程序闯关答题的题目。

要求：
1. 输出必须是合法 JSON，不要输出任何 JSON 之外的内容。
2. 题目总数为 {question_count} 题。
3. 题型配比：{type_ratio_instruction}；判断题选项固定为 A 正确、B 错误；多选题正确答案至少 2 个。
4. 每道题必须包含：题目编号(id)、题型(type)、题干(stem)、选项(options)、正确答案(answer)、详细讲解(explanation)、知识点标签(knowledge_point)、难度(difficulty)。
5. 题目与讲解必须适合中小学生（6~18 岁）：用词口语化、贴近生活，避免过度学术化；涉及专业术语时必须先用一句话通俗解释。
6. 内容必须积极健康、准确无误，不得包含暴力、色情、政治敏感或任何不适合未成年人的内容。
7. 如果输入内容过短，可以基于常识合理补充，但不要偏离主题。
8. 难度要求：{difficulty}（easy|medium|hard|mixed）。
9. 每道题的 explanation 必须包含两部分：①本题正确答案及原因；②1~2 句拓展知识点。
10. difficulty 只能取值 easy、medium、hard。

输出 JSON 结构如下（严格按此结构输出）：
{{
  "title": "学习主题",
  "summary": "本次题库的主题摘要",
  "questions": [
    {{
      "id": "q1",
      "type": "single",
      "stem": "题干",
      "options": [
        {{"key": "A", "text": "选项A"}},
        {{"key": "B", "text": "选项B"}}
      ],
      "answer": ["A"],
      "explanation": "①本题正确答案及原因；②1~2 句拓展知识点。",
      "knowledge_point": "知识点标签",
      "difficulty": "easy"
    }}
  ]
}}

{search_context_section}
学生想学的内容如下：
{user_input}"""


SEARCH_CONTEXT_TEMPLATE = """以下是通过联网搜索获取的参考资料，请优先基于这些资料出题，确保知识准确性：

{search_context}
"""
