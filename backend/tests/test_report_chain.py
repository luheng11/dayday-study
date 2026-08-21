"""报告链测试（TDD，mock 大模型）"""

import pytest

from app.core.exceptions import ReportGenerationError
from app.llm.report_chain import generate_report
from app.models.quiz import AnswerRecord
from tests.fake_llm import VALID_REPORT_JSON, CapturingFakeModel


def make_records() -> list[AnswerRecord]:
    return [
        AnswerRecord(
            question_id="q1", selected_answers=["A"], is_correct=True, duration_ms=3200
        ),
        AnswerRecord(
            question_id="q2", selected_answers=["B"], is_correct=False, duration_ms=5000
        ),
    ]


@pytest.fixture
def score_summary() -> dict:
    return {
        "total": 2,
        "correct": 1,
        "wrong": 1,
        "accuracy": 50,
        "avg_duration_ms": 4100,
    }


class TestGenerateReportSuccess:
    @pytest.mark.asyncio
    async def test_plain_json(self, score_summary):
        model = CapturingFakeModel([VALID_REPORT_JSON])
        report = await generate_report(
            topic="光合作用",
            questions=[],
            answer_records=make_records(),
            score_summary=score_summary,
            model=model,
        )
        assert len(report.three_line_summary) == 3
        assert report.share_quote
        assert len(report.advice) >= 1

    @pytest.mark.asyncio
    async def test_fenced_json(self, score_summary):
        model = CapturingFakeModel(["```json\n" + VALID_REPORT_JSON + "\n```"])
        report = await generate_report(
            topic="光合作用",
            questions=[],
            answer_records=make_records(),
            score_summary=score_summary,
            model=model,
        )
        assert report.accuracy == 80

    @pytest.mark.asyncio
    async def test_prompt_contains_topic_and_stats(self, score_summary):
        model = CapturingFakeModel([VALID_REPORT_JSON])
        await generate_report(
            topic="光合作用",
            questions=[],
            answer_records=make_records(),
            score_summary=score_summary,
            model=model,
        )
        text = model.joined_text()
        assert "光合作用" in text
        assert '"accuracy": 50' in text or "'accuracy': 50" in text


class TestGenerateReportRetry:
    @pytest.mark.asyncio
    async def test_retry_after_invalid_json(self, score_summary):
        model = CapturingFakeModel(["坏数据", VALID_REPORT_JSON])
        report = await generate_report(
            topic="光合作用",
            questions=[],
            answer_records=make_records(),
            score_summary=score_summary,
            model=model,
        )
        assert model.call_count == 2
        assert report.accuracy == 80

    @pytest.mark.asyncio
    async def test_retry_when_summary_not_three_items(self, score_summary):
        bad = VALID_REPORT_JSON.replace(
            '"three_line_summary": [', '"three_line_summary": ["只有一句"],"x_ignore": ['
        )
        # 上面替换后 JSON 仍合法但 three_line_summary 只有 1 项
        model = CapturingFakeModel([bad, VALID_REPORT_JSON])
        report = await generate_report(
            topic="光合作用",
            questions=[],
            answer_records=make_records(),
            score_summary=score_summary,
            model=model,
        )
        assert model.call_count == 2
        assert len(report.three_line_summary) == 3

    @pytest.mark.asyncio
    async def test_retry_when_share_quote_empty(self, score_summary):
        bad = VALID_REPORT_JSON.replace(
            '"share_quote": "把不会的，变成会的。"', '"share_quote": ""'
        )
        model = CapturingFakeModel([bad, VALID_REPORT_JSON])
        report = await generate_report(
            topic="光合作用",
            questions=[],
            answer_records=make_records(),
            score_summary=score_summary,
            model=model,
        )
        assert model.call_count == 2
        assert report.share_quote

    @pytest.mark.asyncio
    async def test_retry_when_advice_empty(self, score_summary):
        bad = VALID_REPORT_JSON.replace('"advice": [', '"advice": [];"x_ignore": [')
        model = CapturingFakeModel([bad, VALID_REPORT_JSON])
        report = await generate_report(
            topic="光合作用",
            questions=[],
            answer_records=make_records(),
            score_summary=score_summary,
            model=model,
        )
        assert model.call_count == 2
        assert len(report.advice) >= 1


class TestGenerateReportExhausted:
    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self, score_summary):
        model = CapturingFakeModel(["坏数据"] * 10)
        with pytest.raises(ReportGenerationError, match="报告生成失败"):
            await generate_report(
                topic="光合作用",
                questions=[],
                answer_records=make_records(),
                score_summary=score_summary,
                model=model,
            )
        # 报告同步接口受前端 60s 超时约束：最多 2 次尝试（20s × 2 最坏 40s）
        assert model.call_count == 2
