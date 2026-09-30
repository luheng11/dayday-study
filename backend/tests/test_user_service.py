"""用户服务单元测试（TDD：先写测试再实现 app/services/user_service.py）"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AuthenticationError, BusinessError
from app.models.user import LoginRequest, UpdateProfileRequest
from app.services import user_service


class TestWxCodeToOpenid:
    @pytest.mark.asyncio
    async def test_mock_mode_default_openid(self, monkeypatch):
        """开发降级模式：无微信凭据时返回固定开发 openid（每次登录同一用户）。"""
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "wechat_app_id", "")
        monkeypatch.setattr(settings, "wechat_app_secret", "")
        monkeypatch.setattr(settings, "wechat_mock_login", True)

        openid = await user_service.wx_code_to_openid("任意code")
        assert openid == "dev_openid_default"

    @pytest.mark.asyncio
    async def test_mock_mode_dev_prefix_passthrough(self, monkeypatch):
        """dev_ 前缀 code 直接作为 openid（便于本地模拟多用户）。"""
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "wechat_mock_login", True)
        monkeypatch.setattr(settings, "wechat_app_id", "")
        monkeypatch.setattr(settings, "wechat_app_secret", "")

        assert await user_service.wx_code_to_openid("dev_openid_42") == "dev_openid_42"

    @pytest.mark.asyncio
    async def test_mock_disabled_without_credentials_raises(self, monkeypatch):
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "wechat_mock_login", False)
        monkeypatch.setattr(settings, "wechat_app_id", "")
        monkeypatch.setattr(settings, "wechat_app_secret", "")

        with pytest.raises(AuthenticationError, match="未配置"):
            await user_service.wx_code_to_openid("code")

    @pytest.mark.asyncio
    async def test_real_call_success(self, monkeypatch):
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "wechat_mock_login", False)
        monkeypatch.setattr(settings, "wechat_app_id", "wx123")
        monkeypatch.setattr(settings, "wechat_app_secret", "secret123")

        class FakeResp:
            def json(self):
                return {"openid": "real_openid_9", "session_key": "sk"}

        def assert_params(url, params=None):
            assert params["appid"] == "wx123"
            assert params["js_code"] == "wxcode"
            return FakeResp()

        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=assert_params,
        ):
            openid = await user_service.wx_code_to_openid("wxcode")
        assert openid == "real_openid_9"

    @pytest.mark.asyncio
    async def test_real_call_wechat_rejects(self, monkeypatch):
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "wechat_mock_login", False)
        monkeypatch.setattr(settings, "wechat_app_id", "wx123")
        monkeypatch.setattr(settings, "wechat_app_secret", "secret123")

        class FakeResp:
            def json(self):
                return {"errcode": 40029, "errmsg": "invalid code"}

        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            return_value=FakeResp(),
        ):
            with pytest.raises(AuthenticationError, match="微信登录失败"):
                await user_service.wx_code_to_openid("badcode")

    @pytest.mark.asyncio
    async def test_real_call_network_error(self, monkeypatch):
        import httpx

        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "wechat_mock_login", False)
        monkeypatch.setattr(settings, "wechat_app_id", "wx123")
        monkeypatch.setattr(settings, "wechat_app_secret", "secret123")

        async def raise_connect(url, params=None):
            raise httpx.ConnectError("boom")

        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=raise_connect,
        ):
            with pytest.raises(AuthenticationError, match="暂时不可用"):
                await user_service.wx_code_to_openid("code")


class TestHandleLogin:
    @pytest.mark.asyncio
    async def test_new_user_auto_register(self, monkeypatch):
        monkeypatch.setattr(
            user_service, "wx_code_to_openid", AsyncMock(return_value="openid_new")
        )
        created_user = {
            "id": 7,
            "openid": "openid_new",
            "nickname": "学习者",
            "avatar_url": "",
            "total_xp": 0,
        }
        with patch(
            "app.services.user_service.user_repository.find_user_by_openid",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.user_service.user_repository.create_user",
            new_callable=AsyncMock,
            return_value=created_user,
        ) as mock_create:
            resp = await user_service.handle_login("code")
        mock_create.assert_called_once_with("openid_new")
        assert resp.token
        assert resp.user.id == 7
        assert resp.user.nickname == "学习者"
        assert resp.user.total_xp == 0

    @pytest.mark.asyncio
    async def test_existing_user_returns_same_identity(self, monkeypatch):
        monkeypatch.setattr(
            user_service, "wx_code_to_openid", AsyncMock(return_value="openid_old")
        )
        existing = {
            "id": 5,
            "openid": "openid_old",
            "nickname": "小闯同学",
            "avatar_url": "https://example.com/a.png",
            "total_xp": 320,
        }
        with patch(
            "app.services.user_service.user_repository.find_user_by_openid",
            new_callable=AsyncMock,
            return_value=existing,
        ), patch(
            "app.services.user_service.user_repository.create_user",
            new_callable=AsyncMock,
        ) as mock_create:
            resp = await user_service.handle_login("code")
        mock_create.assert_not_called()
        assert resp.user.id == 5
        assert resp.user.total_xp == 320


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_profile_aggregates_stats_and_level(self):
        user_row = {
            "id": 1,
            "openid": "o1",
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
                # 全部历史
                {
                    "quiz_count": 12,
                    "correct_count": 45,
                    "average_accuracy": 78,
                    "total_duration_ms": 600000,
                },
                # 本周（since=周一）
                {"quiz_count": 5, "correct_count": 20, "average_accuracy": 82, "total_duration_ms": 200000},
            ],
        ), patch(
            "app.services.user_service.quiz_repository.get_user_answer_dates",
            new_callable=AsyncMock,
            return_value=[],
        ):
            profile = await user_service.get_profile(1)
        assert profile.id == 1
        assert profile.nickname == "小闯同学"
        assert profile.total_xp == 320
        assert profile.quiz_count == 12
        assert profile.correct_count == 45
        assert profile.average_accuracy == 78
        assert profile.week_quiz_count == 5
        assert profile.streak_days == 0
        assert profile.level.level == 3  # 320 XP → Lv3 知识探险家（门槛 300）
        assert profile.level.title == "知识探险家"

    @pytest.mark.asyncio
    async def test_profile_user_not_found_raises(self):
        with patch(
            "app.services.user_service.user_repository.get_user_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(AuthenticationError, match="用户不存在"):
                await user_service.get_profile(999)


class TestUpdateProfile:
    @pytest.mark.asyncio
    async def test_update_calls_repository_with_stripped_values(self):
        with patch(
            "app.services.user_service.user_repository.update_user_profile",
            new_callable=AsyncMock,
        ) as mock_update:
            await user_service.update_profile(1, "  小闯同学  ", None)
        mock_update.assert_called_once_with(1, "小闯同学", None)

    @pytest.mark.asyncio
    async def test_update_empty_nickname_rejected(self):
        with pytest.raises(BusinessError, match="昵称不能为空"):
            await user_service.update_profile(1, "   ", None)

    @pytest.mark.asyncio
    async def test_update_none_fields_noop(self):
        with patch(
            "app.services.user_service.user_repository.update_user_profile",
            new_callable=AsyncMock,
        ) as mock_update:
            await user_service.update_profile(1, None, None)
        mock_update.assert_not_called()
