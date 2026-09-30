"""时区归一化的**真实数据库**验证（RUN_MYSQL_TESTS=1 时运行）

这是真正能抓住"MySQL 服务器时区 ≠ 应用本地时区"的那条测试：
单测只能验证 SQL 字符串拼得对，只有连上真实 MySQL 才能确认
`CURRENT_TIMESTAMP` 落库的值与 Python `datetime.now()` 处于同一时区。

不带修复时，只要 MySQL 跑在 UTC 而机器在 UTC+8，这里的断言就会失败。
"""

import os
from datetime import datetime, timedelta

import pytest

from tests.test_repositories_mysql import test_db  # noqa: F401 —— 复用建库/清库 fixture

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_MYSQL_TESTS") != "1",
    reason="需要真实 MySQL 环境：设置 RUN_MYSQL_TESTS=1 运行",
)

from app.core import db as db_module  # noqa: E402


class TestSessionTimeZone:
    async def test_session_timezone_is_set(self, test_db):  # noqa: F811
        """连接会话时区应被显式设定（而不是依赖容器 TZ=... 的默认值）。"""
        pool = db_module.get_mysql_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT @@session.time_zone")
                row = await cur.fetchone()
        # init_command 生效后应是一个显式偏移，而不是 SYSTEM
        assert row is not None
        assert row[0] != "SYSTEM", "会话时区仍是 SYSTEM：init_command 未生效"

    async def test_db_now_matches_python_now(self, test_db):  # noqa: F811
        """核心断言：数据库 NOW() 与 Python 本地时间必须同一时区（容差 60s）。"""
        pool = db_module.get_mysql_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT NOW()")
                row = await cur.fetchone()
        db_now: datetime = row[0]
        py_now = datetime.now()
        drift = abs((db_now - py_now).total_seconds())
        assert drift < 60, (
            f"数据库时间与本地时间相差 {drift:.0f}s（{db_now} vs {py_now}）——"
            f"MySQL 与本机不在同一时区，'最近7天/本周/连续打卡'会有固定偏移"
        )

    async def test_created_at_round_trip(self, test_db):  # noqa: F811
        """落库的 created_at 必须落在 Python 视角的"现在"附近。"""
        from app.repositories import user_repository

        user = await user_repository.create_user("openid_tz")
        pool = db_module.get_mysql_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT created_at FROM users WHERE id = %s", (user["id"],)
                )
                row = await cur.fetchone()
        created_at: datetime = row[0]
        drift = abs((datetime.now() - created_at).total_seconds())
        assert drift < 60, (
            f"created_at={created_at} 与本地现在相差 {drift:.0f}s，时间戳口径不一致"
        )

    async def test_seven_day_window_boundary(self, test_db):  # noqa: F811
        """近 7 天窗口的边界：刚写入的记录必须落在窗口内。

        注意：这条**只在本地时间凌晨（约 00:00–08:00）才会真正触发** 8 小时偏移
        的失败——因为落库时间戳落到前一天时，"今天"的桶才会错位。白天运行时即便
        时区没对齐它也会通过，所以它**不是**主防线；主防线是上面的
        `test_session_timezone_is_set` / `test_db_now_matches_python_now`。
        """
        from app.repositories import quiz_repository, user_repository

        user = await user_repository.create_user("openid_tz2")
        await quiz_repository.save_quiz_session(
            quiz_id="quiz_tz_1",
            user_id=user["id"],
            title="时区边界",
            summary="s",
            user_input="i",
            questions_json=[],
        )
        await quiz_repository.save_answer_record(
            quiz_id="quiz_tz_1",
            user_id=user["id"],
            records_json=[],
            total_questions=1,
            correct_count=1,
            accuracy=100.0,
            total_duration_ms=1000,
        )

        week_start = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=6)
        stats = await quiz_repository.get_user_answer_stats(user["id"], since=week_start)
        assert stats["quiz_count"] == 1, (
            f"刚写入的记录未落入近 7 天窗口（quiz_count={stats['quiz_count']}）——"
            f"时间窗口与落库时间戳时区不一致"
        )

        daily = await quiz_repository.get_user_daily_stats(user["id"], days=7)
        assert sum(c for _, c, _ in daily) == 1, "当日统计未包含刚写入的记录"
