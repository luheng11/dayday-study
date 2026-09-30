"""服务层与路由层测试 fixtures（复用 fake LLM 与样例数据）"""

import json

import pytest

from app.models.quiz import AnswerRecord, Question, QuizOutput
from tests.fake_llm import VALID_QUIZ_JSON, VALID_REPORT_JSON


@pytest.fixture
def sample_quiz_output() -> QuizOutput:
    return QuizOutput.model_validate(json.loads(VALID_QUIZ_JSON))


@pytest.fixture
def sample_questions() -> list[Question]:
    return QuizOutput.model_validate(json.loads(VALID_QUIZ_JSON)).questions


@pytest.fixture
def sample_answer_records(sample_questions) -> list[AnswerRecord]:
    """5 题记录：q1/q2 对、q3 错、q4 对、q5 错 → 正确率 60"""
    return [
        AnswerRecord(
            question_id="q1", selected_answers=["A"], is_correct=True, duration_ms=3000
        ),
        AnswerRecord(
            question_id="q2", selected_answers=["B"], is_correct=True, duration_ms=4000
        ),
        AnswerRecord(
            question_id="q3", selected_answers=["B"], is_correct=False, duration_ms=5000
        ),
        AnswerRecord(
            question_id="q4",
            selected_answers=["A", "B", "C"],
            is_correct=True,
            duration_ms=8000,
        ),
        AnswerRecord(
            question_id="q5", selected_answers=["A"], is_correct=False, duration_ms=2000
        ),
    ]


@pytest.fixture
def sample_report_dict() -> dict:
    return json.loads(VALID_REPORT_JSON)


@pytest.fixture
def auth_header() -> dict:
    """生成一个有效的 JWT（user_id=1）用于鉴权相关测试。"""
    from app.core.auth import create_token

    token = create_token(user_id=1, openid="test_openid_123")
    return {"Authorization": f"Bearer {token}"}
