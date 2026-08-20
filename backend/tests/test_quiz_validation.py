"""题库完整性校验测试（TDD，五级保障第 4 级）"""

import pytest

from app.core.exceptions import QuizIntegrityError
from app.models.quiz import QuizOutput
from app.services.quiz_validation import validate_quiz_output


def q(**overrides):
    base = {
        "id": "q1",
        "type": "single",
        "stem": "题干",
        "options": [
            {"key": "A", "text": "A选项"},
            {"key": "B", "text": "B选项"},
            {"key": "C", "text": "C选项"},
            {"key": "D", "text": "D选项"},
        ],
        "answer": ["A"],
        "explanation": "讲解",
        "knowledge_point": "知识点",
        "difficulty": "easy",
    }
    base.update(overrides)
    return base


def quiz(questions, title="主题", summary="摘要"):
    return QuizOutput(title=title, summary=summary, questions=questions)


class TestCount:
    def test_exact_count_passes(self):
        validate_quiz_output(quiz([q(id="q1"), q(id="q2")]), expected_count=2)

    def test_count_mismatch_raises(self):
        with pytest.raises(QuizIntegrityError, match="题目数量"):
            validate_quiz_output(quiz([q(id="q1")]), expected_count=2)


class TestSingleChoice:
    def test_single_answer_ok(self):
        validate_quiz_output(quiz([q(id="q1", answer=["A"])]), expected_count=1)

    def test_single_multi_answer_raises(self):
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(quiz([q(id="q1", answer=["A", "B"])]), expected_count=1)


class TestMultipleChoice:
    def test_multiple_at_least_two_answers(self):
        validate_quiz_output(
            quiz([q(id="q1", type="multiple", answer=["A", "B"])]), expected_count=1
        )

    def test_multiple_single_answer_raises(self):
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(
                quiz([q(id="q1", type="multiple", answer=["A"])]), expected_count=1
            )


class TestJudge:
    def test_judge_standard_options_pass(self):
        qq = q(
            id="q1",
            type="judge",
            options=[{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
            answer=["B"],
        )
        validate_quiz_output(quiz([qq]), expected_count=1)

    def test_judge_requires_exactly_two_options(self):
        qq = q(id="q1", type="judge", answer=["B"])
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(quiz([qq]), expected_count=1)

    def test_judge_option_texts_must_be_correct_wrong(self):
        qq = q(
            id="q1",
            type="judge",
            options=[{"key": "A", "text": "对"}, {"key": "B", "text": "错"}],
            answer=["B"],
        )
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(quiz([qq]), expected_count=1)

    def test_judge_answer_must_be_single(self):
        qq = q(
            id="q1",
            type="judge",
            options=[{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
            answer=["A", "B"],
        )
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(quiz([qq]), expected_count=1)


class TestGenericIntegrity:
    def test_answer_key_not_in_options_raises(self):
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(quiz([q(id="q1", answer=["Z"])]), expected_count=1)

    def test_duplicate_option_keys_raises(self):
        qq = q(
            id="q1",
            options=[
                {"key": "A", "text": "x"},
                {"key": "A", "text": "y"},
                {"key": "B", "text": "z"},
            ],
        )
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(quiz([qq]), expected_count=1)

    def test_duplicate_question_ids_raises(self):
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(quiz([q(id="q1"), q(id="q1")]), expected_count=2)

    def test_empty_stem_raises(self):
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(quiz([q(id="q1", stem="")]), expected_count=1)

    def test_empty_explanation_raises(self):
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(quiz([q(id="q1", explanation="")]), expected_count=1)

    def test_empty_knowledge_point_raises(self):
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(quiz([q(id="q1", knowledge_point="")]), expected_count=1)

    def test_fewer_than_two_options_raises(self):
        qq = q(id="q1", options=[{"key": "A", "text": "x"}])
        with pytest.raises(QuizIntegrityError):
            validate_quiz_output(quiz([qq]), expected_count=1)

    def test_all_valid_passes(self):
        questions = [
            q(id="q1"),
            q(
                id="q2",
                type="multiple",
                answer=["A", "B"],
                difficulty="medium",
            ),
            q(
                id="q3",
                type="judge",
                options=[{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
                answer=["A"],
                difficulty="hard",
            ),
        ]
        validate_quiz_output(quiz(questions), expected_count=3)
