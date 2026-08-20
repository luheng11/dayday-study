"""报告接口测试（TDD：路由、统一响应、错误码、服务端权威判分）"""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.fake_llm import VALID_QUIZ_JSON, VALID_REPORT_JSON, CapturingFakeModel


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def report_payload():
    quiz = json.loads(VALID_QUIZ_JSON)
    return {
        "quiz_id": "quiz_abc123",
        "topic": "光合作用",
        "questions": quiz["questions"],
        "answer_records": [
            {
                "question_id": "q1",
                "selected_answers": ["A"],
                "is_correct": True,
                "duration_ms": 3000,
            },
            {
                "question_id": "q2",
                "selected_answers": ["B"],
                "is_correct": True,
                "duration_ms": 4000,
            },
            {
                "question_id": "q3",
                "selected_answers": ["B"],
                "is_correct": False,
                "duration_ms": 5000,
            },
            {
                "question_id": "q4",
                "selected_answers": ["A", "B", "C"],
                "is_correct": True,
                "duration_ms": 8000,
            },
            {
                "question_id": "q5",
                "selected_answers": ["A"],
                "is_correct": False,
                "duration_ms": 2000,
            },
        ],
    }


class TestReportApi:
    @pytest.mark.asyncio
    async def test_report_ok_and_local_accuracy_wins(self, client, report_payload):
        from app.services import report_service

        report_service.llm_model = CapturingFakeModel([VALID_REPORT_JSON])

        resp = await client.post("/api/v1/report/generate", json=report_payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        # AI 输出 80，本地判分 3/5 = 60 → 以本地为准
        assert data["accuracy"] == 60
        assert len(data["three_line_summary"]) == 3
        assert data["share_quote"]

    @pytest.mark.asyncio
    async def test_report_mismatch_4001(self, client, report_payload):
        report_payload["answer_records"] = report_payload["answer_records"][:4]
        resp = await client.post("/api/v1/report/generate", json=report_payload)
        assert resp.status_code == 400
        assert resp.json()["code"] == 4001

    @pytest.mark.asyncio
    async def test_report_generation_failure_5002(self, client, report_payload):
        from app.services import report_service

        report_service.llm_model = CapturingFakeModel(["坏数据"] * 10)
        resp = await client.post("/api/v1/report/generate", json=report_payload)
        assert resp.status_code == 500
        body = resp.json()
        assert body["code"] == 5002
        assert "报告生成失败" in body["message"]

    @pytest.mark.asyncio
    async def test_report_invalid_schema_4001(self, client):
        resp = await client.post("/api/v1/report/generate", json={"quiz_id": "x"})
        assert resp.status_code == 422
        assert resp.json()["code"] == 4001
