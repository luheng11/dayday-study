"""用户系统 API 集成测试（TDD：mock 仓储与微信，验证路由契约）"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

TRANSPORT = ASGITransport(app=app)


@pytest.fixture
def client():
    async def _request(method, url, **kwargs):
        async with AsyncClient(transport=TRANSPORT, base_url="http://test") as c:
            return await c.request(method, url, **kwargs)

    return _request


class TestLoginAPI:
    async def test_login_success_new_user(self, client):
        mock_user = {
            "id": 1,
            "openid": "dev_openid_default",
            "nickname": "学习者",
            "avatar_url": "",
            "total_xp": 0,
        }
        with patch(
            "app.services.user_service.wx_code_to_openid",
            new_callable=AsyncMock,
            return_value="dev_openid_default",
        ), patch(
            "app.services.user_service.user_repository.find_user_by_openid",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.user_service.user_repository.create_user",
            new_callable=AsyncMock,
            return_value=mock_user,
        ):
            resp = await client("POST", "/api/v1/user/login", json={"code": "dev_x"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["token"]
        assert body["data"]["user"]["nickname"] == "学习者"
        assert body["data"]["user"]["id"] == 1

    async def test_login_existing_user(self, client):
        mock_user = {
            "id": 5,
            "openid": "o_existing",
            "nickname": "小闯同学",
            "avatar_url": "",
            "total_xp": 320,
        }
        with patch(
            "app.services.user_service.wx_code_to_openid",
            new_callable=AsyncMock,
            return_value="o_existing",
        ), patch(
            "app.services.user_service.user_repository.find_user_by_openid",
            new_callable=AsyncMock,
            return_value=mock_user,
        ):
            resp = await client("POST", "/api/v1/user/login", json={"code": "dev_x"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["user"]["id"] == 5
        assert body["data"]["user"]["total_xp"] == 320

    async def test_login_empty_code_rejected(self, client):
        resp = await client("POST", "/api/v1/user/login", json={"code": ""})
        assert resp.status_code == 422
        assert resp.json()["code"] == 4001

    async def test_login_wechat_failure_returns_401(self, client):
        from app.core.exceptions import AuthenticationError

        with patch(
            "app.services.user_service.wx_code_to_openid",
            new_callable=AsyncMock,
            side_effect=AuthenticationError("微信登录失败，请重试"),
        ):
            resp = await client("POST", "/api/v1/user/login", json={"code": "bad"})
        assert resp.status_code == 401
        assert resp.json()["code"] == 4010


class TestProfileAPI:
    async def test_get_profile_success(self, client, auth_header):
        user_row = {
            "id": 1,
            "openid": "test_openid_123",
            "nickname": "小闯同学",
            "avatar_url": "",
            "total_xp": 320,
        }
        with patch(
            "app.services.user_service.user_repository.get_user_by_id",
            new_callable=AsyncMock,
            return_value=user_row,
        ), patch(
            "app.services.user_service.quiz_repository.get_user_answer_stats",
            new_callable=AsyncMock,
            side_effect=[
                {"quiz_count": 12, "correct_count": 45, "average_accuracy": 78, "total_duration_ms": 0},
                {"quiz_count": 5, "correct_count": 20, "average_accuracy": 82, "total_duration_ms": 0},
            ],
        ), patch(
            "app.services.user_service.quiz_repository.get_user_answer_dates",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client("GET", "/api/v1/user/profile", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["quiz_count"] == 12
        assert data["correct_count"] == 45
        assert data["average_accuracy"] == 78
        assert data["week_quiz_count"] == 5
        assert data["level"]["level"] == 3  # 320 XP → Lv3 知识探险家

    async def test_get_profile_unauthorized(self, client):
        resp = await client("GET", "/api/v1/user/profile")
        assert resp.status_code == 401
        assert resp.json()["code"] == 4010

    async def test_update_profile_success(self, client, auth_header):
        with patch(
            "app.services.user_service.user_repository.update_user_profile",
            new_callable=AsyncMock,
        ) as mock_update:
            resp = await client(
                "PUT",
                "/api/v1/user/profile",
                json={"nickname": " 新昵称 "},
                headers=auth_header,
            )
        assert resp.status_code == 200
        mock_update.assert_called_once_with(1, "新昵称", None)

    async def test_update_profile_empty_nickname_rejected(self, client, auth_header):
        resp = await client(
            "PUT",
            "/api/v1/user/profile",
            json={"nickname": "   "},
            headers=auth_header,
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 4001


class TestQuizHistoryAPI:
    async def test_get_quiz_list(self, client, auth_header):
        rows = [
            {
                "quiz_id": "quiz_1",
                "title": "光合作用",
                "user_input": "光合作用",
                "accuracy": 80.0,
                "question_count": 5,
                "duration_ms": 192000,
                "created_at": "2026-08-20 09:48:00",
                "has_report": True,
                "report_snippet": "snippet",
            }
        ]
        with patch(
            "app.services.history_service.quiz_repository.get_user_quiz_list",
            new_callable=AsyncMock,
            return_value=(rows, 1),
        ) as mock_list:
            resp = await client(
                "GET", "/api/v1/user/quizzes?page=1&page_size=10&range=week&only_completed=true",
                headers=auth_header,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["total"] == 1
        assert body["data"]["items"][0]["quiz_id"] == "quiz_1"
        kwargs = mock_list.call_args.kwargs
        assert kwargs["page"] == 1
        assert kwargs["page_size"] == 10
        assert kwargs["only_completed"] is True
        assert kwargs["start_time"] is not None

    async def test_get_quiz_list_unauthorized(self, client):
        resp = await client("GET", "/api/v1/user/quizzes")
        assert resp.status_code == 401

    async def test_get_quiz_detail_success(self, client, auth_header):
        row = {
            "quiz_id": "quiz_1",
            "title": "光合作用",
            "summary": "摘要",
            "user_input": "输入",
            "questions": [{"id": "q1"}],
            "answer_records": [{"question_id": "q1", "is_correct": True}],
            "report": {"accuracy": 80},
            "created_at": "2026-08-20 09:48:00",
        }
        with patch(
            "app.services.history_service.quiz_repository.get_quiz_detail",
            new_callable=AsyncMock,
            return_value=row,
        ):
            resp = await client(
                "GET", "/api/v1/user/quizzes/quiz_1", headers=auth_header
            )
        assert resp.status_code == 200
        assert resp.json()["data"]["quiz_id"] == "quiz_1"

    async def test_get_quiz_detail_not_found(self, client, auth_header):
        with patch(
            "app.services.history_service.quiz_repository.get_quiz_detail",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client(
                "GET", "/api/v1/user/quizzes/quiz_nonexist", headers=auth_header
            )
        assert resp.status_code == 200
        assert resp.json()["code"] == 4004


class TestUserStatsAPI:
    async def test_get_stats_success(self, client, auth_header):
        with patch(
            "app.services.history_service.quiz_repository.get_user_daily_stats",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.history_service.quiz_repository.get_user_knowledge_data",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.history_service.quiz_repository.get_user_answer_dates",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client("GET", "/api/v1/user/stats", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["days"]) == 7
        assert data["streak_days"] == 0
        assert data["mastery"] == []
        assert data["weak_points"] == []

    async def test_get_stats_unauthorized(self, client):
        resp = await client("GET", "/api/v1/user/stats")
        assert resp.status_code == 401
