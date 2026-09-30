"""时区口径归一化测试（TDD）

## 背景

`created_at` 列用 MySQL 的 `CURRENT_TIMESTAMP` 填充（**服务器会话语时区**），
而所有时间范围过滤与聚合的"起点"用 Python 的朴素 `datetime.now()`
（**操作系统本地时区**）——见 `quiz_repository.get_user_answer_stats` /
`get_user_quiz_list` / `get_user_daily_stats`、`history_service.compute_streak`、
`user_service._week_start`。

两者若不在同一时区，"最近 7 天""本周闯关""连续打卡"会出现固定偏移，
而且**不报错**：只是数据静默地不对。当前之所以没出问题，仅仅是因为
MySQL 容器恰好带了 `TZ=Asia/Shanghai`；换成 UTC 机器或云数据库（多为 UTC）
就会退化成 8 小时偏移。

修复方式：连接层显式把会话时区设成本机本地偏移（`init_command`），
不再依赖容器的 `TZ` 环境变量。
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.db import mysql_time_zone_init_command


class TestOffsetFormat:
    """`SET time_zone` 需要 `+HH:MM` / `-HH:MM` 形式，且 MySQL 只接受整分钟。"""

    def test_east_eight(self):
        tz = timezone(timedelta(hours=8))
        assert mysql_time_zone_init_command(tz) == "SET time_zone='+08:00'"

    def test_utc_is_plus_zero(self):
        assert mysql_time_zone_init_command(timezone.utc) == "SET time_zone='+00:00'"

    def test_west(self):
        tz = timezone(timedelta(hours=-5))
        assert mysql_time_zone_init_command(tz) == "SET time_zone='-05:00'"

    def test_half_hour_offset(self):
        """印度 +05:30 —— 验证分钟位不是恒为 00。"""
        tz = timezone(timedelta(hours=5, minutes=30))
        assert mysql_time_zone_init_command(tz) == "SET time_zone='+05:30'"

    def test_quarter_hour_offset(self):
        """尼泊尔 +05:45 —— MySQL 支持整分钟偏移。"""
        tz = timezone(timedelta(hours=5, minutes=45))
        assert mysql_time_zone_init_command(tz) == "SET time_zone='+05:45'"

    def test_negative_half_hour(self):
        tz = timezone(timedelta(hours=-3, minutes=-30))
        assert mysql_time_zone_init_command(tz) == "SET time_zone='-03:30'"

    def test_statement_is_single_statement(self):
        """必须是单条语句（init_command 只接受一条）。"""
        stmt = mysql_time_zone_init_command(timezone.utc)
        assert stmt.count(";") <= 1
        assert stmt.strip().rstrip(";") == "SET time_zone='+00:00'"

    def test_defaults_to_local_timezone(self):
        """不传参数时使用本机本地时区，且与本地 UTC 偏移一致。"""
        stmt = mysql_time_zone_init_command()
        offset = datetime.now().astimezone().utcoffset()
        sign = "+" if offset >= timedelta(0) else "-"
        total = int(abs(offset).total_seconds())
        expected = f"SET time_zone='{sign}{total // 3600:02d}:{(total % 3600) // 60:02d}'"
        assert stmt == expected


class TestLocalTimezoneMatchesPython:
    """确保选用的时区与 datetime.now() 的口径一致（这是不偏移的前提）。"""

    def test_local_offset_used(self):
        stmt = mysql_time_zone_init_command()
        local = datetime.now().astimezone().utcoffset()
        total = int(abs(local).total_seconds())
        assert f"{total // 3600:02d}:{(total % 3600) // 60:02d}" in stmt


@pytest.mark.parametrize("bad", [timedelta(seconds=30), timedelta(seconds=-30)])
def test_rejects_sub_minute_offsets(bad):
    """MySQL 不接受秒级偏移；遇到历史时区（如 LMT）应抛错而不是写出非法语句。"""
    tz = timezone(bad)
    with pytest.raises(ValueError):
        mysql_time_zone_init_command(tz)
