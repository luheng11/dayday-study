"""题库完整性校验（五级保障第 4 级：字段完整性校验）

校验规则（与方案设计 4.3 + Prompt 约束一致）：
- 题目数量必须等于请求数量；
- 题目 id 唯一、stem/explanation/knowledge_point 非空；
- 题型枚举由 Pydantic 保证（single/multiple/judge）；
- 选项 key 唯一、至少 2 个；answer 必须是选项 key 的子集；
- 单选/判断 answer 恰好 1 个；多选 answer 至少 2 个；
- 判断题选项固定 A 正确、B 错误，共 2 个；
- difficulty 枚举由 Pydantic 保证（easy/medium/hard）。
"""

from app.core.exceptions import QuizIntegrityError
from app.models.quiz import Question, QuizOutput

JUDGE_OPTION_TEXTS = ("正确", "错误")


def _validate_question(question: Question, index: int) -> None:
    label = f"第 {index + 1} 题（{question.id}）"

    if not question.stem.strip():
        raise QuizIntegrityError(f"{label}：题干为空")
    if not question.explanation.strip():
        raise QuizIntegrityError(f"{label}：讲解为空")
    if not question.knowledge_point.strip():
        raise QuizIntegrityError(f"{label}：知识点标签为空")

    if len(question.options) < 2:
        raise QuizIntegrityError(f"{label}：选项少于 2 个")

    keys = [opt.key for opt in question.options]
    if len(keys) != len(set(keys)):
        raise QuizIntegrityError(f"{label}：选项 key 重复")

    if not question.answer:
        raise QuizIntegrityError(f"{label}：答案为空")
    if any(a not in keys for a in question.answer):
        raise QuizIntegrityError(f"{label}：答案包含不存在的选项 key")

    if question.type == "single":
        if len(question.answer) != 1:
            raise QuizIntegrityError(f"{label}：单选题答案必须恰好 1 个")

    if question.type == "multiple":
        if len(question.answer) < 2:
            raise QuizIntegrityError(f"{label}：多选题答案至少 2 个")

    if question.type == "judge":
        if len(question.options) != 2:
            raise QuizIntegrityError(f"{label}：判断题必须恰好 2 个选项")
        if [opt.text for opt in question.options] != list(JUDGE_OPTION_TEXTS):
            raise QuizIntegrityError(f"{label}：判断题选项必须为「正确/错误」")
        if len(question.answer) != 1:
            raise QuizIntegrityError(f"{label}：判断题答案必须恰好 1 个")


def validate_quiz_output(quiz: QuizOutput, expected_count: int) -> None:
    """校验完整题库；不合法抛 QuizIntegrityError。"""
    if len(quiz.questions) != expected_count:
        raise QuizIntegrityError(
            f"题目数量不符：期望 {expected_count} 题，实际 {len(quiz.questions)} 题"
        )

    ids = [q.id for q in quiz.questions]
    if len(ids) != len(set(ids)):
        raise QuizIntegrityError("题目 id 重复")

    for i, question in enumerate(quiz.questions):
        _validate_question(question, i)
