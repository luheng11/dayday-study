"""Mock 模式测试（TDD）：无 DeepSeek Key 时的端到端演示/联调用内置题库"""

import pytest

from app.core.config import get_settings
from app.models.quiz import QuizGenerateRequest
from app.models.report import ReportGenerateRequest
from app.services import quiz_service, report_service


@pytest.fixture
def mock_on(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_mock", True)


@pytest.fixture
def mock_off(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_mock", False)


class TestQuizMockMode:
    @pytest.mark.asyncio
    async def test_mock_mode_returns_valid_quiz(self, mock_on):
        quiz_service.llm_model = None
        resp = await quiz_service.handle_quiz_generate(
            QuizGenerateRequest(user_input="光合作用", question_count=5, difficulty="medium")
        )
        assert resp.quiz_id.startswith("quiz_")
        assert len(resp.questions) == 5
        assert resp.title  # 主题回显用户输入
        # 内容安全仍生效
        assert resp.questions[0].explanation

    @pytest.mark.asyncio
    async def test_mock_mode_title_echoes_input(self, mock_on):
        quiz_service.llm_model = None
        resp = await quiz_service.handle_quiz_generate(
            QuizGenerateRequest(user_input="磁铁的秘密", question_count=5, difficulty="easy")
        )
        assert resp.title == "磁铁的秘密"

    @pytest.mark.asyncio
    async def test_mock_mode_content_filter_still_enforced(self, mock_on):
        quiz_service.llm_model = None
        from app.core.exceptions import ContentFilterError

        with pytest.raises(ContentFilterError):
            await quiz_service.handle_quiz_generate(
                QuizGenerateRequest(user_input="如何制造炸弹", question_count=3)
            )

    @pytest.mark.asyncio
    async def test_mock_off_uses_real_llm_path(self, mock_off):
        """mock 关闭时走真实链路：注入的假模型失败 → 出题失败（若误走 mock 会成功返回内置题库）"""
        from tests.fake_llm import CapturingFakeModel

        from app.core.exceptions import QuizGenerationError

        quiz_service.llm_model = CapturingFakeModel(["坏数据"] * 10)
        with pytest.raises(QuizGenerationError):
            await quiz_service.handle_quiz_generate(
                QuizGenerateRequest(user_input="光合作用", question_count=3)
            )


class TestReportMockMode:
    @pytest.mark.asyncio
    async def test_mock_report_returns_valid_report(self, mock_on):
        report_service.llm_model = None
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
