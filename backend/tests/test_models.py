"""领域模型测试（TDD）"""

import pytest
from pydantic import ValidationError

from app.models.quiz import (
    AnswerRecord,
    Question,
    QuestionOption,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizOutput,
    QuizTaskCreateResponse,
    QuizTaskStatusResponse,
)
from app.models.report import ReportGenerateRequest, ReportGenerateResponse, ReportOutput


def make_question(**overrides) -> Question:
    base = {
        "id": "q1",
        "type": "single",
        "stem": "光合作用主要发生在植物细胞的哪个部位？",
        "options": [
            {"key": "A", "text": "叶绿体"},
            {"key": "B", "text": "线粒体"},
            {"key": "C", "text": "细胞核"},
            {"key": "D", "text": "液泡"},
        ],
        "answer": ["A"],
        "explanation": "叶绿体是光合作用的场所。",
        "knowledge_point": "光合作用场所",
        "difficulty": "easy",
    }
    base.update(overrides)
    return Question(**base)


class TestQuizGenerateRequest:
    def test_defaults(self):
        req = QuizGenerateRequest(user_input="光合作用")
        assert req.question_count == 5
        assert req.difficulty == "mixed"

    def test_valid_count_range(self):
        for n in (3, 5, 10):
            req = QuizGenerateRequest(user_input="x" * 10, question_count=n)
            assert req.question_count == n

    @pytest.mark.parametrize("bad_count", [0, 1, 2, 11, 100])
    def test_rejects_invalid_count(self, bad_count):
        with pytest.raises(ValidationError):
            QuizGenerateRequest(user_input="x", question_count=bad_count)

    def test_rejects_empty_input(self):
        with pytest.raises(ValidationError):
            QuizGenerateRequest(user_input="")

    def test_accepts_2000_chars(self):
        req = QuizGenerateRequest(user_input="学" * 2000)
        assert len(req.user_input) == 2000

    def test_rejects_over_2000_chars(self):
        with pytest.raises(ValidationError):
            QuizGenerateRequest(user_input="学" * 2001)

    def test_rejects_unknown_difficulty(self):
        with pytest.raises(ValidationError):
            QuizGenerateRequest(user_input="x", difficulty="hardcore")

    @pytest.mark.parametrize("d", ["easy", "medium", "hard", "mixed"])
    def test_accepts_difficulties(self, d):
        req = QuizGenerateRequest(user_input="x", difficulty=d)
        assert req.difficulty == d


class TestQuestionModel:
    def test_valid_single_question(self):
        q = make_question()
        assert q.type == "single"
        assert q.answer == ["A"]

    @pytest.mark.parametrize("bad_type", ["essay", "fill", "SINGLE"])
    def test_rejects_bad_type(self, bad_type):
        with pytest.raises(ValidationError):
            make_question(type=bad_type)

    @pytest.mark.parametrize("bad_diff", ["simple", "hardcore"])
    def test_rejects_bad_difficulty(self, bad_diff):
        with pytest.raises(ValidationError):
            make_question(difficulty=bad_diff)

    def test_image_url_defaults_none(self):
        q = make_question()
        assert q.image_url is None

    def test_answer_must_be_list(self):
        with pytest.raises(ValidationError):
            make_question(answer="A")

    def test_multiple_answer_allowed(self):
        q = make_question(type="multiple", answer=["A", "B", "D"])
        assert q.answer == ["A", "B", "D"]


class TestQuizOutput:
    def test_valid_quiz_output(self):
        quiz = QuizOutput(
            title="光合作用",
            summary="植物的能量工厂",
            questions=[make_question(), make_question(id="q2")],
        )
        assert len(quiz.questions) == 2

    def test_missing_title_rejected(self):
        with pytest.raises(ValidationError):
            QuizOutput(summary="s", questions=[make_question()])


class TestAnswerRecord:
    def test_valid_record(self):
        r = AnswerRecord(
            question_id="q1", selected_answers=["A"], is_correct=True, duration_ms=3200
        )
        assert r.duration_ms == 3200

    def test_negative_duration_rejected(self):
        with pytest.raises(ValidationError):
            AnswerRecord(question_id="q1", selected_answers=["A"], is_correct=True, duration_ms=-1)


class TestQuizGenerateResponse:
    def test_response_fields(self):
        q = make_question()
        resp = QuizGenerateResponse(
            quiz_id="quiz_abc123",
            title="光合作用",
            summary="植物的能量工厂",
            questions=[q],
        )
        dumped = resp.model_dump()
        assert dumped["quiz_id"] == "quiz_abc123"
        assert dumped["questions"][0]["id"] == "q1"


class TestQuizTaskModels:
    def test_create_response(self):
        r = QuizTaskCreateResponse(task_id="task_abc123")
        assert r.task_id == "task_abc123"

    def test_status_response_completed(self):
        r = QuizTaskStatusResponse(
            task_id="task_abc123",
            status="completed",
            result={
                "quiz_id": "quiz_x",
                "title": "t",
                "summary": "s",
                "questions": [make_question().model_dump()],
                "image_notice": None,
            },
        )
        assert r.status == "completed"
        assert r.result is not None

    def test_status_response_failed(self):
        r = QuizTaskStatusResponse(
            task_id="task_abc123", status="failed", error_message="题库生成失败"
        )
        assert r.result is None
        assert r.error_message == "题库生成失败"


class TestReportModels:
    def make_request(self):
        return {
            "quiz_id": "quiz_abc123",
            "topic": "光合作用",
            "questions": [make_question().model_dump()],
            "answer_records": [
                {
                    "question_id": "q1",
                    "selected_answers": ["A"],
                    "is_correct": True,
                    "duration_ms": 3000,
                }
            ],
        }

    def test_report_generate_request_valid(self):
        req = ReportGenerateRequest(**self.make_request())
        assert req.topic == "光合作用"
        assert len(req.answer_records) == 1

    def test_report_output_valid(self):
        r = ReportOutput(
            accuracy=80,
            mastered_points=["光合作用的场所"],
            weak_points=["产物与原料的区分"],
            three_line_summary=["1", "2", "3"],
            advice=["明天再来一次"],
            share_quote="把不会的，变成会的。",
        )
        assert r.accuracy == 80

    def test_report_generate_response(self):
        r = ReportGenerateResponse(
            accuracy=80,
            mastered_points=[],
            weak_points=[],
            three_line_summary=["1", "2", "3"],
            advice=["a"],
            share_quote="q",
        )
        assert r.model_dump()["accuracy"] == 80
