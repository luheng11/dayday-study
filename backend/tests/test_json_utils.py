"""JSON 兜底解析测试（TDD）"""

import json

import pytest

from app.llm.json_utils import extract_json


class TestExtractJson:
    def test_plain_json(self):
        raw = '{"title": "光合作用", "questions": []}'
        data = extract_json(raw)
        assert data == {"title": "光合作用", "questions": []}

    def test_json_fence_with_language(self):
        raw = '```json\n{"title": "光合作用"}\n```'
        assert extract_json(raw) == {"title": "光合作用"}

    def test_json_fence_without_language(self):
        raw = '```\n{"title": "光合作用"}\n```'
        assert extract_json(raw) == {"title": "光合作用"}

    def test_leading_and_trailing_noise(self):
        raw = '好的，以下是题目：\n{"title": "光合作用", "questions": []}\n希望有帮助！'
        assert extract_json(raw)["title"] == "光合作用"

    def test_nested_object_with_braces_inside_strings(self):
        payload = {
            "title": "光合作用",
            "questions": [
                {
                    "id": "q1",
                    "explanation": "公式：{光} + {水} → 糖。注意花括号不是 JSON。",
                }
            ],
        }
        raw = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
        data = extract_json(raw)
        assert data["questions"][0]["explanation"].startswith("公式")

    def test_array_root(self):
        raw = '[{"id": "q1"}, {"id": "q2"}]'
        assert extract_json(raw) == [{"id": "q1"}, {"id": "q2"}]

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError):
            extract_json("这不是 JSON 内容")

    def test_empty_content_raises(self):
        with pytest.raises(ValueError):
            extract_json("")

    def test_unbalanced_braces_raises(self):
        with pytest.raises(ValueError):
            extract_json('{"title": "光合作用"')
