"""等级体系单元测试（TDD：先写测试再实现 app/core/levels.py）

等级门槛（用户确认）：0 / 100 / 300 / 600 / 1000 / 1500 / 2100 / 2800 / 3600 / 4500
徽章名：闯关新星→学习小能手→知识探险家→闯关小勇士→智慧小达人→闯关小达人→学霸小先锋→知识领航员→学习之星→闯关大师
"""

import pytest

from app.core.levels import get_level_info


class TestGetLevelInfo:
    def test_zero_xp_is_level_one(self):
        info = get_level_info(0)
        assert info["level"] == 1
        assert info["title"] == "闯关新星"
        assert info["level_start_xp"] == 0
        assert info["level_end_xp"] == 100
        assert info["is_max"] is False

    def test_level_boundaries(self):
        # 99 仍是 Lv1；100 升 Lv2
        assert get_level_info(99)["level"] == 1
        lv2 = get_level_info(100)
        assert lv2["level"] == 2
        assert lv2["title"] == "学习小能手"
        assert lv2["level_start_xp"] == 100
        assert lv2["level_end_xp"] == 300

    def test_mid_levels(self):
        assert get_level_info(299)["level"] == 2
        assert get_level_info(300)["level"] == 3
        assert get_level_info(599)["level"] == 3
        assert get_level_info(600)["level"] == 4
        assert get_level_info(1500)["level"] == 6
        assert get_level_info(1500)["title"] == "闯关小达人"

    def test_max_level(self):
        info = get_level_info(4500)
        assert info["level"] == 10
        assert info["title"] == "闯关大师"
        assert info["is_max"] is True
        assert info["level_end_xp"] is None

    def test_beyond_max_stays_max(self):
        info = get_level_info(999999)
        assert info["is_max"] is True
        assert info["level"] == 10
