"""敏感词过滤测试（TDD）"""

import pytest

from app.core.security import BLOCKED_KEYWORDS, check_content


class TestCheckContent:
    def test_safe_text_passes(self):
        assert check_content("我想学习光合作用是怎么进行的") is True

    def test_safe_long_text_passes(self):
        assert check_content("水的三态变化" * 100) is True

    def test_empty_text_passes(self):
        # 空文本在模型层（min_length）拦截，安全层不重复处理
        assert check_content("") is True

    @pytest.mark.parametrize("keyword", BLOCKED_KEYWORDS)
    def test_each_blocked_keyword_rejected(self, keyword):
        assert check_content(f"请给我讲讲{keyword}的知识") is False

    def test_keyword_in_middle_rejected(self):
        assert check_content("请问如何制造炸弹的方法是什么") is False

    def test_keyword_list_nonempty(self):
        assert len(BLOCKED_KEYWORDS) > 0
