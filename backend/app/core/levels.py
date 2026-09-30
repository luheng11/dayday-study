"""等级体系：按累计经验值计算等级与徽章（前端只渲染，规则集中在后端）

门槛（用户确认）：0 / 100 / 300 / 600 / 1000 / 1500 / 2100 / 2800 / 3600 / 4500
"""

from typing import Optional

# 每级起始经验值（下标 0 → Lv.1）
LEVEL_THRESHOLDS: list[int] = [0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500]

# 徽章名（与阈值一一对应）
LEVEL_TITLES: list[str] = [
    "闯关新星",
    "学习小能手",
    "知识探险家",
    "闯关小勇士",
    "智慧小达人",
    "闯关小达人",
    "学霸小先锋",
    "知识领航员",
    "学习之星",
    "闯关大师",
]


def get_level_info(total_xp: int) -> dict:
    """返回 {level, title, level_start_xp, level_end_xp, is_max}。

    - level_end_xp 为下一级门槛；最高级为 None。
    - XP 进度条渲染：进度 = total_xp - level_start_xp，总长 = level_end_xp - level_start_xp。
    """
    xp = max(0, int(total_xp))
    level = 1
    for idx, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            level = idx + 1

    is_max = level >= len(LEVEL_THRESHOLDS)
    return {
        "level": level,
        "title": LEVEL_TITLES[level - 1],
        "level_start_xp": LEVEL_THRESHOLDS[level - 1],
        "level_end_xp": None if is_max else LEVEL_THRESHOLDS[level],
        "is_max": is_max,
    }
