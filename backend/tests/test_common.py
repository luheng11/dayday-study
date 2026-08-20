"""通用响应模型测试（TDD：先写测试）"""

import pytest
from pydantic import BaseModel

from app.models.common import ApiResponse


class TestApiResponse:
    def test_success_defaults(self):
        resp = ApiResponse.success()
        assert resp.code == 0
        assert resp.message == "ok"
        assert resp.data is None

    def test_success_with_data(self):
        payload = {"quiz_id": "quiz_abc123", "title": "光合作用"}
        resp = ApiResponse.success(data=payload)
        assert resp.code == 0
        assert resp.data == payload
        assert resp.model_dump()["data"] == payload

    def test_success_custom_message(self):
        resp = ApiResponse.success(data={"a": 1}, message="创建成功")
        assert resp.message == "创建成功"

    def test_error_envelope(self):
        resp = ApiResponse.error(code=4000, message="输入内容包含不当内容")
        assert resp.code == 4000
        assert resp.message == "输入内容包含不当内容"
        assert resp.data is None

    def test_response_serializable_to_dict(self):
        class Inner(BaseModel):
            name: str

        resp = ApiResponse.success(data=Inner(name="闯闯"))
        dumped = resp.model_dump()
        assert dumped["data"] == {"name": "闯闯"}
