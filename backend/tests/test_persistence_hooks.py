"""落库钩子测试（TDD：有登录态时 quiz/report 持久化、失败不影响主流程、XP 规则）"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.quiz import QuizGenerateRequest
from app.models.report import ReportGenerateRequest
from app.services import quiz_service, report_service
from tests.fake_llm import VALID_QUIZ_JSON, CapturingFakeModel


@pytest.fixture
def req() -> QuizGenerateRequest:
    return QuizGenerateRequest(
        user_input="光合作用是怎么进行的？", question_count=5, difficulty="medium"
    )


class TestQuizGeneratePersistence:
    @pytest.mark.asyncio
    async def test_with_user_saves_quiz_session(self, req):
        quiz_service.llm_model = CapturingFakeModel([VALID_QUIZ_JSON])
        with patch(
            "app.services.quiz_service.quiz_repository.save_quiz_session",
            new_callable=AsyncMock,
        ) as mock_save:
            resp = await quiz_service.handle_quiz_generate(req, user_id=1)
        assert resp.quiz_id.startswith("quiz_")
        kwargs = mock_save.call_args.kwargs
        assert kwargs["user_id"] == 1
        assert kwargs["quiz_id"] == resp.quiz_id
        assert kwargs["title"] == "光合作用"
        assert kwargs["user_input"] == req.user_input
        assert len(kwargs["questions_json"]) == 5

    @pytest.mark.asyncio
    async def test_anonymous_does_not_save(self, req):
        quiz_service.llm_model = CapturingFakeModel([VALID_QUIZ_JSON])
        with patch(
            "app.services.quiz_service.quiz_repository.save_quiz_session",
            new_callable=AsyncMock,
        ) as mock_save:
            await quiz_service.handle_quiz_generate(req, user_id=None)
        mock_save.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_failure_does_not_break_response(self, req):
        quiz_service.llm_model = CapturingFakeModel([VALID_QUIZ_JSON])
        with patch(
            "app.services.quiz_service.quiz_repository.save_quiz_session",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db down"),
        ):
            resp = await quiz_service.handle_quiz_generate(req, user_id=1)
        assert len(resp.questions) == 5

    @pytest.mark.asyncio
    async def test_async_task_persists_on_completion(self, req):
        """异步出题任务完成后（有登录态）也应落库。"""
        from app.services.task_store import task_store

        quiz_service.llm_model = CapturingFakeModel([VALID_QUIZ_JSON])
        task_id = "task_persist_1"
        await task_store.create(task_id)
        with patch(
            "app.services.quiz_service.quiz_repository.save_quiz_session",
            new_callable=AsyncMock,
        ) as mock_save:
            await quiz_service._run_quiz_task(task_id, req, user_id=1)
        status = await quiz_service.get_quiz_task_status(task_id)
        assert status.status == "completed"
        mock_save.assert_called_once()
        assert mock_save.call_args.kwargs["user_id"] == 1


class TestReportPersistence:
    @pytest.fixture
    def report_req(self, sample_questions, sample_answer_records) -> ReportGenerateRequest:
        return ReportGenerateRequest(
            quiz_id="quiz_test123",
            topic="光合作用",
            questions=sample_questions,
            answer_records=sample_answer_records,
        )

    @pytest.mark.asyncio
    async def test_with_user_persists_and_adds_xp(self, report_req):
        report_service.llm_model = CapturingFakeModel(["{}"] * 1)
        # 用 mock 报告生成器绕过 LLM，聚焦落库断言
        from app.models.report import ReportOutput

        fake_report = ReportOutput(
            accuracy=60,
            mastered_points=["p1"],
            weak_points=["p2"],
            three_line_summary=["s1", "s2", "s3"],
            advice=["a1"],
            share_quote="q",
        )
        with patch(
            "app.services.report_service.generate_report",
            new_callable=AsyncMock,
            return_value=fake_report,
        ), patch(
            "app.services.report_service.quiz_repository.save_answer_record",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_save_ar, patch(
            "app.services.report_service.quiz_repository.save_report",
            new_callable=AsyncMock,
        ) as mock_save_rp, patch(
            "app.services.report_service.user_repository.add_user_xp",
            new_callable=AsyncMock,
        ) as mock_add_xp:
            result = await report_service.handle_report_generate(report_req, user_id=1)
        assert result.accuracy == 60  # 本地统计覆盖
        mock_save_ar.assert_called_once()
        ar_kwargs = mock_save_ar.call_args.kwargs
        assert ar_kwargs["quiz_id"] == "quiz_test123"
        assert ar_kwargs["user_id"] == 1
        assert ar_kwargs["total_questions"] == 5
        assert ar_kwargs["correct_count"] == 3
        assert ar_kwargs["accuracy"] == 60
        assert ar_kwargs["total_duration_ms"] == 22000  # 3000+4000+5000+8000+2000
        mock_save_rp.assert_called_once()
        # XP 规则（沿用 M1）：q1✓单选10 + q2✓单选10 + q3✗ + q4✓多选15 + q5✗判断
        mock_add_xp.assert_called_once_with(1, 35)

    @pytest.mark.asyncio
    async def test_duplicate_answer_record_skips_xp(self, report_req):
        """同一 quiz 重复生成报告（重试）时更新记录但不重复加 XP。"""
        from app.models.report import ReportOutput

        fake_report = ReportOutput(
            accuracy=60,
            mastered_points=["p1"],
            weak_points=[],
            three_line_summary=["s1", "s2", "s3"],
            advice=["a1"],
            share_quote="q",
        )
        with patch(
            "app.services.report_service.generate_report",
            new_callable=AsyncMock,
            return_value=fake_report,
        ), patch(
            "app.services.report_service.quiz_repository.save_answer_record",
            new_callable=AsyncMock,
            return_value=False,  # 已存在 → 更新
        ), patch(
            "app.services.report_service.quiz_repository.save_report",
            new_callable=AsyncMock,
        ), patch(
            "app.services.report_service.user_repository.add_user_xp",
            new_callable=AsyncMock,
        ) as mock_add_xp:
            await report_service.handle_report_generate(report_req, user_id=1)
        mock_add_xp.assert_not_called()

    @pytest.mark.asyncio
    async def test_anonymous_does_not_persist(self, report_req):
        from app.models.report import ReportOutput

        fake_report = ReportOutput(
            accuracy=60,
            mastered_points=["p1"],
            weak_points=[],
            three_line_summary=["s1", "s2", "s3"],
            advice=["a1"],
            share_quote="q",
        )
        with patch(
            "app.services.report_service.generate_report",
            new_callable=AsyncMock,
            return_value=fake_report,
        ), patch(
            "app.services.report_service.quiz_repository.save_answer_record",
            new_callable=AsyncMock,
        ) as mock_save:
            await report_service.handle_report_generate(report_req, user_id=None)
        mock_save.assert_not_called()

    @pytest.mark.asyncio
    async def test_persist_failure_does_not_break_response(self, report_req):
        from app.models.report import ReportOutput

        fake_report = ReportOutput(
            accuracy=60,
            mastered_points=["p1"],
            weak_points=[],
            three_line_summary=["s1", "s2", "s3"],
            advice=["a1"],
            share_quote="q",
        )
        with patch(
            "app.services.report_service.generate_report",
            new_callable=AsyncMock,
            return_value=fake_report,
        ), patch(
            "app.services.report_service.quiz_repository.save_answer_record",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db down"),
        ):
            result = await report_service.handle_report_generate(report_req, user_id=1)
        assert result.accuracy == 60
