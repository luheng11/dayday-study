"""Mock 模式测试（TDD）：主题匹配题库、无 Key 演示、报告 Mock、隔离恢复"""

import pytest

from app.core.config import get_settings
from app.llm.mock_data import _match_quiz_key, build_mock_quiz
from app.models.quiz import QuizGenerateRequest
from app.models.report import ReportGenerateRequest
from app.services import quiz_service, report_service


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """每个用例后恢复全局注入状态"""
    monkeypatch.setattr(get_settings(), "llm_mock", False)
    monkeypatch.setattr(quiz_service, "llm_model", None)
    monkeypatch.setattr(report_service, "llm_model", None)


@pytest.fixture
def mock_on(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_mock", True)


class TestQuizKeyMatching:
    @pytest.mark.parametrize(
        "topic, expected",
        [
            ("20以内的加减法", "math"),
            ("小学数学口算", "math"),
            ("乘法口诀", "math"),
            ("光合作用是怎么进行的", "photosynthesis"),
            ("植物是怎么吃饭的", "photosynthesis"),
            ("火山为什么会喷发", "volcano"),
            ("地震是怎么发生的", "volcano"),
            ("磁铁的秘密", "magnet"),
            ("磁铁为什么能吸铁", "magnet"),
            ("我不知道想学什么", "general"),
        ],
    )
    def test_keyword_matching(self, topic, expected):
        assert _match_quiz_key(topic) == expected


class TestMockQuizTopicAware:
    @pytest.mark.asyncio
    async def test_math_topic_gets_math_questions(self, mock_on):
        resp = await quiz_service.handle_quiz_generate(
            QuizGenerateRequest(user_input="20以内的加减法", question_count=5, difficulty="easy")
        )
        assert resp.title == "20以内的加减法"
        stems = "".join(q.stem for q in resp.questions)
        assert any(ch.isdigit() for ch in stems)
        assert "光合" not in stems and "叶绿体" not in stems

    @pytest.mark.asyncio
    async def test_science_topic_gets_science_questions(self, mock_on):
        resp = await quiz_service.handle_quiz_generate(
            QuizGenerateRequest(user_input="光合作用", question_count=5, difficulty="medium")
        )
        stems = "".join(q.stem for q in resp.questions)
        assert "光合" in stems

    @pytest.mark.asyncio
    async def test_volcano_topic_gets_volcano_questions(self, mock_on):
        resp = await quiz_service.handle_quiz_generate(
            QuizGenerateRequest(user_input="火山为什么会喷发", question_count=5)
        )
        stems = "".join(q.stem for q in resp.questions)
        assert "火山" in stems or "岩浆" in stems

    @pytest.mark.asyncio
    async def test_magnet_topic_gets_magnet_questions(self, mock_on):
        resp = await quiz_service.handle_quiz_generate(
            QuizGenerateRequest(user_input="磁铁的秘密", question_count=5)
        )
        stems = "".join(q.stem for q in resp.questions)
        assert "磁铁" in stems or "磁" in stems

    @pytest.mark.asyncio
    async def test_general_fallback(self, mock_on):
        resp = await quiz_service.handle_quiz_generate(
            QuizGenerateRequest(user_input="随便学点什么", question_count=5)
        )
        assert len(resp.questions) == 5
        stems = "".join(q.stem for q in resp.questions)
        assert "光合" not in stems

    @pytest.mark.asyncio
    async def test_three_question_ratio_one_to_one(self, mock_on):
        resp = await quiz_service.handle_quiz_generate(
            QuizGenerateRequest(user_input="20以内的加减法", question_count=3)
        )
        types = {q.type for q in resp.questions}
        assert types == {"single", "multiple", "judge"}

    def test_summary_mentions_mock(self):
        quiz = build_mock_quiz("20以内的加减法", 5, "easy")
        assert "Mock" in quiz.summary or "演示" in quiz.summary


class TestMockModeSwitches:
    @pytest.mark.asyncio
    async def test_mock_off_uses_real_llm_path(self):
        """mock 关闭时走真实链路：注入的假模型失败 → 出题失败（若误走 mock 会成功返回内置题库）"""
        from tests.fake_llm import CapturingFakeModel

        from app.core.exceptions import QuizGenerationError

        quiz_service.llm_model = CapturingFakeModel(["坏数据"] * 10)
        with pytest.raises(QuizGenerationError):
            await quiz_service.handle_quiz_generate(
                QuizGenerateRequest(user_input="光合作用", question_count=3)
            )

    @pytest.mark.asyncio
    async def test_mock_report_returns_valid_report(self, mock_on):
        from app.models.quiz import AnswerRecord, Question, QuestionOption

        question = Question(
            id="q1",
            type="single",
            stem="光合作用发生在哪里？",
            options=[QuestionOption(key="A", text="叶绿体"), QuestionOption(key="B", text="线粒体")],
            answer=["A"],
            explanation="叶绿体是光合作用的场所。",
            knowledge_point="光合作用场所",
            difficulty="easy",
        )
        resp = await report_service.handle_report_generate(
            ReportGenerateRequest(
                quiz_id="quiz_mock123",
                topic="光合作用",
                questions=[question],
                answer_records=[
                    AnswerRecord(
                        question_id="q1",
                        selected_answers=["A"],
                        is_correct=True,
                        duration_ms=3000,
                    )
                ],
            )
        )
        assert resp.accuracy == 100
        assert len(resp.three_line_summary) == 3
        assert resp.share_quote
