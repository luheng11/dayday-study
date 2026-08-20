"""报告服务测试（TDD：服务端权威判分、准确率覆盖、参数校验）"""

import pytest

from app.core.exceptions import BusinessError, ReportGenerationError
from app.models.report import ReportGenerateRequest
from app.services import report_service
from tests.fake_llm import VALID_REPORT_JSON, CapturingFakeModel


def make_req(sample_questions, sample_answer_records) -> ReportGenerateRequest:
    return ReportGenerateRequest(
        quiz_id="quiz_abc123",
        topic="光合作用",
        questions=sample_questions,
        answer_records=sample_answer_records,
    )


class TestReportGenerate:
    @pytest.mark.asyncio
    async def test_success(self, sample_questions, sample_answer_records):
        report_service.llm_model = CapturingFakeModel([VALID_REPORT_JSON])
        resp = await report_service.handle_report_generate(
            make_req(sample_questions, sample_answer_records)
        )
        # 3/5 对 → 60，覆盖 AI 输出的 80
        assert resp.accuracy == 60
        assert len(resp.three_line_summary) == 3
        assert resp.share_quote

    @pytest.mark.asyncio
    async def test_accuracy_always_local_authoritative(
        self, sample_questions, sample_answer_records
    ):
        # AI 报告声称 100，但本地判分只有 60 → 以本地为准
        lying = VALID_REPORT_JSON.replace('"accuracy": 80', '"accuracy": 100')
        report_service.llm_model = CapturingFakeModel([lying])
        resp = await report_service.handle_report_generate(
            make_req(sample_questions, sample_answer_records)
        )
        assert resp.accuracy == 60

    @pytest.mark.asyncio
    async def test_client_cannot_fake_correctness(
        self, sample_questions, sample_answer_records
    ):
        """客户端把全部记录谎报为正确 → 服务端按 selected_answers 重判，仍是 3/5=60"""
        lied = [r.model_copy(update={"is_correct": True}) for r in sample_answer_records]
        report_service.llm_model = CapturingFakeModel([VALID_REPORT_JSON])
        resp = await report_service.handle_report_generate(
            make_req(sample_questions, lied)
        )
        assert resp.accuracy == 60

    @pytest.mark.asyncio
    async def test_mismatched_records_rejected(
        self, sample_questions, sample_answer_records
    ):
        # 少一条记录
        req = make_req(sample_questions, sample_answer_records[:4])
        with pytest.raises(BusinessError):
            await report_service.handle_report_generate(req)

    @pytest.mark.asyncio
    async def test_duplicate_records_rejected(
        self, sample_questions, sample_answer_records
    ):
        dup = [sample_answer_records[0], *sample_answer_records]
        req = make_req(sample_questions, dup)
        with pytest.raises(BusinessError):
            await report_service.handle_report_generate(req)

    @pytest.mark.asyncio
    async def test_unknown_question_id_rejected(
        self, sample_questions, sample_answer_records
    ):
        records = [r.model_copy(update={"question_id": "qX"}) for r in sample_answer_records]
        req = make_req(sample_questions, records)
        with pytest.raises(BusinessError):
            await report_service.handle_report_generate(req)

    @pytest.mark.asyncio
    async def test_generation_failure_propagates(
        self, sample_questions, sample_answer_records
    ):
        report_service.llm_model = CapturingFakeModel(["坏数据"] * 10)
        with pytest.raises(ReportGenerationError, match="报告生成失败"):
            await report_service.handle_report_generate(
                make_req(sample_questions, sample_answer_records)
            )
