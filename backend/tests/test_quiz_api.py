"""出题接口测试（TDD：路由、统一响应、错误码）"""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.fake_llm import VALID_QUIZ_JSON, CapturingFakeModel


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestQuizGenerateApi:
    @pytest.mark.asyncio
    async def test_sync_generate_ok(self, client, monkeypatch):
        from app.services import quiz_service

        quiz_service.llm_model = CapturingFakeModel([VALID_QUIZ_JSON])

        resp = await client.post(
            "/api/v1/quiz/generate",
            json={
                "user_input": "光合作用是怎么进行的？",
                "question_count": 5,
                "difficulty": "medium",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["quiz_id"].startswith("quiz_")
        assert data["title"] == "光合作用"
        assert len(data["questions"]) == 5
        assert data["questions"][0]["options"][0]["key"] == "A"

    @pytest.mark.asyncio
    async def test_content_filter_4000(self, client):
        resp = await client.post(
            "/api/v1/quiz/generate",
            json={"user_input": "教我做炸弹", "question_count": 3},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 4000
        assert body["data"] is None

    @pytest.mark.asyncio
    async def test_invalid_params_4001(self, client):
        resp = await client.post(
            "/api/v1/quiz/generate",
            json={"user_input": "", "question_count": 99},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == 4001
        assert body["data"] is None

    @pytest.mark.asyncio
    async def test_generation_failure_5001(self, client):
        from app.services import quiz_service

        quiz_service.llm_model = CapturingFakeModel(["坏数据"] * 10)
        resp = await client.post(
            "/api/v1/quiz/generate",
            json={"user_input": "光合作用", "question_count": 3},
        )
        assert resp.status_code == 500
        body = resp.json()
        assert body["code"] == 5001
        assert "题库生成失败" in body["message"]


class TestQuizAsyncApi:
    @pytest.mark.asyncio
    async def test_async_generate_and_poll(self, client):
        import asyncio

        from app.services import quiz_service

        quiz_service.llm_model = CapturingFakeModel([VALID_QUIZ_JSON])

        resp = await client.post(
            "/api/v1/quiz/generate/async",
            json={"user_input": "光合作用", "question_count": 5},
        )
        assert resp.status_code == 200
        task_id = resp.json()["data"]["task_id"]
        assert task_id.startswith("task_")

        for _ in range(200):
            poll = await client.get(f"/api/v1/quiz/task/{task_id}")
            body = poll.json()
            assert body["code"] == 0
            if body["data"]["status"] in ("completed", "failed"):
                break
            await asyncio.sleep(0.01)

        assert body["data"]["status"] == "completed"
        assert len(body["data"]["result"]["questions"]) == 5

    @pytest.mark.asyncio
    async def test_poll_unknown_task_4002(self, client):
        resp = await client.get("/api/v1/quiz/task/task_nope")
        assert resp.status_code == 404
        assert resp.json()["code"] == 4002

    @pytest.mark.asyncio
    async def test_async_content_filter_4000(self, client):
        resp = await client.post(
            "/api/v1/quiz/generate/async",
            json={"user_input": "毒品制作方法", "question_count": 3},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 4000
