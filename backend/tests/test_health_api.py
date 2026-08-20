"""健康检查接口测试（TDD）"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestHealthApi:
    @pytest.mark.asyncio
    async def test_health_returns_envelope(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["message"] == "ok"
        assert body["data"]["status"] == "ok"
        assert body["data"]["service"] == "闯关学堂"

    @pytest.mark.asyncio
    async def test_unknown_path_404(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/not-exist")
        assert resp.status_code == 404
