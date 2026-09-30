"""头像上传接口测试（TDD：微信 chooseAvatar 临时文件 → 后端持久化）"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

TRANSPORT = ASGITransport(app=app)


@pytest.fixture
async def client():
    async def _request(method, url, **kwargs):
        async with AsyncClient(transport=TRANSPORT, base_url="http://test") as c:
            return await c.request(method, url, **kwargs)

    return _request


class TestAvatarUpload:
    async def test_upload_success(self, client, auth_header, tmp_path, monkeypatch):
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "data_dir", str(tmp_path))

        with patch(
            "app.services.user_service.user_repository.update_user_profile",
            new_callable=AsyncMock,
        ) as mock_update:
            resp = await client(
                "POST",
                "/api/v1/user/avatar",
                headers=auth_header,
                files={"file": ("avatar.png", b"\x89PNG fake image bytes", "image/png")},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        avatar_url = body["data"]["avatar_url"]
        assert "/static/avatars/" in avatar_url
        mock_update.assert_called_once()
        args = mock_update.call_args.args
        assert args[0] == 1
        assert args[1] is None  # 不改昵称
        assert args[2] == avatar_url

    async def test_upload_unauthorized(self, client):
        resp = await client(
            "POST",
            "/api/v1/user/avatar",
            files={"file": ("a.png", b"x", "image/png")},
        )
        assert resp.status_code == 401

    async def test_upload_rejects_non_image(self, client, auth_header, tmp_path, monkeypatch):
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "data_dir", str(tmp_path))

        resp = await client(
            "POST",
            "/api/v1/user/avatar",
            headers=auth_header,
            files={"file": ("a.txt", b"plain text", "text/plain")},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 4001

    async def test_upload_rejects_oversize(self, client, auth_header, tmp_path, monkeypatch):
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "data_dir", str(tmp_path))

        big = b"x" * (2 * 1024 * 1024 + 1)
        resp = await client(
            "POST",
            "/api/v1/user/avatar",
            headers=auth_header,
            files={"file": ("big.png", big, "image/png")},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 4001
