"""真实 DeepSeek 出题/报告验证（LLM_MOCK=false 且已填 Key 时使用）

用法：
    .venv\\Scripts\\python scripts/verify_deepseek.py [主题]
    .venv\\Scripts\\python scripts/verify_deepseek.py [主题] --report
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# 保证从任意目录执行都能导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.llm.quiz_chain import generate_quiz  # noqa: E402
from app.llm.report_chain import generate_report  # noqa: E402
from app.models.quiz import AnswerRecord, Question, QuizOutput  # noqa: E402
from app.services.scoring_service import compute_score_summary  # noqa: E402
from tests.fake_llm import VALID_QUIZ_JSON  # noqa: E402


def sample_report_input() -> tuple[list[Question], list[AnswerRecord], dict]:
    quiz = QuizOutput.model_validate(json.loads(VALID_QUIZ_JSON))
    questions = quiz.questions
    records = [
        AnswerRecord(question_id="q1", selected_answers=["A"], is_correct=True, duration_ms=3000),
        AnswerRecord(question_id="q2", selected_answers=["B"], is_correct=True, duration_ms=4000),
        AnswerRecord(question_id="q3", selected_answers=["A"], is_correct=False, duration_ms=5000),
        AnswerRecord(question_id="q4", selected_answers=["A", "B", "C"], is_correct=True, duration_ms=8000),
        AnswerRecord(question_id="q5", selected_answers=["A"], is_correct=False, duration_ms=2000),
    ]
    return questions, records, compute_score_summary(records)


async def verify_report() -> int:
    print("报告链验证（真实 DeepSeek）…")
    questions, records, summary = sample_report_input()
    start = time.time()
    try:
        report = await generate_report(
            topic="光合作用", questions=questions, answer_records=records, score_summary=summary
        )
    except Exception as exc:
        print(f"报告生成失败：{type(exc).__name__}: {exc}")
        return 1
    elapsed = time.time() - start
    print(f"耗时 {elapsed:.1f}s · 正确率(本地) {summary['accuracy']}%")
    print(f"三句总结：{report.three_line_summary[0]}")
    print(f"分享金句：{report.share_quote}")
    print("\n验证通过：真实 AI 报告正常")
    return 0


async def verify_quiz(topic: str) -> int:
    print(f"主题：{topic}（真实 DeepSeek 出题，3 题 / easy）")
    try:
        quiz = await generate_quiz(user_input=topic, question_count=3, difficulty="easy")
    except Exception as exc:
        print(f"出题失败：{type(exc).__name__}: {exc}")
        return 1

    print(f"标题：{quiz.title}")
    print(f"摘要：{quiz.summary}")
    for q in quiz.questions:
        print(f"  [{q.type}/{q.difficulty}] {q.stem}")
        print(f"    答案: {q.answer}  知识点: {q.knowledge_point}")
    print("\n验证通过：真实 AI 出题正常")
    return 0


async def main() -> int:
    args = [a for a in sys.argv[1:]]
    if "--report" in args:
        return await verify_report()
    topic = args[0] if args else "20以内的加减法"
    return await verify_quiz(topic)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
