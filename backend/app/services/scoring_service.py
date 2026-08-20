"""计分服务：正确率统计与星星（⭐/XP）结算

分值约定（与用户确认、与 UI 原型结算数字一致）：
- 单选题  +10⭐
- 多选题  +15⭐
- 判断题  +10⭐
- 答错    +0⭐
"""

from app.models.quiz import AnswerRecord


def compute_score_summary(answer_records: list[AnswerRecord]) -> dict:
    """本地统计：总数、答对数、答错数、正确率、平均用时"""
    total = len(answer_records)
    correct = sum(1 for r in answer_records if r.is_correct)
    accuracy = round(correct / total * 100) if total > 0 else 0
    avg_duration = (
        round(sum(r.duration_ms for r in answer_records) / total) if total > 0 else 0
    )
    return {
        "total": total,
        "correct": correct,
        "wrong": total - correct,
        "accuracy": accuracy,
        "avg_duration_ms": avg_duration,
    }


_XP_BY_TYPE = {"single": 10, "multiple": 15, "judge": 10}


def compute_xp(question_type: str, is_correct: bool) -> int:
    """单题得分"""
    if not is_correct:
        return 0
    return _XP_BY_TYPE.get(question_type, 0)


def total_xp(answer_records: list[AnswerRecord], question_types: dict[str, str]) -> int:
    """整局总得分：按记录逐题累加（question_types: {question_id: type}）"""
    return sum(
        compute_xp(question_types.get(r.question_id, ""), r.is_correct)
        for r in answer_records
    )
