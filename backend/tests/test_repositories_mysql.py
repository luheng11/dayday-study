"""仓储层真实 MySQL 集成测试（RUN_MYSQL_TESTS=1 时运行）

覆盖：建库建表、用户 CRUD、题库/答题/报告落库与回查、统计聚合 SQL。
运行前需准备好 MySQL（docker mysql:8），测试使用独立库 MYSQL_TEST_DATABASE（默认 chuangguan_test）。
"""

import os
from datetime import datetime, timedelta

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_MYSQL_TESTS") != "1",
    reason="需要真实 MySQL 环境：设置 RUN_MYSQL_TESTS=1 运行",
)

from app.core import db as db_module
from app.core.config import get_settings
from app.repositories import quiz_repository, user_repository

TABLES = ["reports", "answer_records", "quiz_sessions", "users"]


async def _truncate_all() -> None:
    pool = db_module.get_mysql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for table in TABLES:
                await cur.execute(f"DELETE FROM {table}")


@pytest.fixture
async def test_db(monkeypatch):
    """初始化独立测试库连接池，每个测试前清空数据。"""
    settings = get_settings()
    monkeypatch.setattr(
        settings, "mysql_database", os.environ.get("MYSQL_TEST_DATABASE", "chuangguan_test")
    )
    await db_module.close_mysql_pool()
    await db_module.init_mysql()
    await _truncate_all()
    yield
    await _truncate_all()
    await db_module.close_mysql_pool()


@pytest.fixture
async def user_a(test_db):
    return await user_repository.create_user("openid_a")


@pytest.fixture
async def user_b(test_db):
    return await user_repository.create_user("openid_b")


class TestDbInit:
    async def test_tables_created(self, test_db):
        pool = db_module.get_mysql_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SHOW TABLES")
                rows = await cur.fetchall()
        names = {r[0] for r in rows}
        for table in TABLES:
            assert table in names

    async def test_reinit_idempotent_without_warnings(self, test_db):
        """重复初始化（服务重启场景）不报「已存在」警告。"""
        import warnings

        await db_module.close_mysql_pool()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await db_module.init_mysql()
        assert db_module.get_mysql_pool() is not None
        assert all(
            "already exists" not in str(w.message).lower() for w in caught
        ), [str(w.message) for w in caught]


class TestUserRepository:
    async def test_create_and_find_by_openid(self, test_db):
        user = await user_repository.create_user("openid_1")
        assert user["id"] > 0
        assert user["nickname"] == "学习者"
        assert user["total_xp"] == 0

        found = await user_repository.find_user_by_openid("openid_1")
        assert found["id"] == user["id"]

        assert await user_repository.find_user_by_openid("missing") is None

    async def test_get_user_by_id(self, test_db, user_a):
        found = await user_repository.get_user_by_id(user_a["id"])
        assert found["nickname"] == "学习者"
        assert await user_repository.get_user_by_id(999999) is None

    async def test_update_user_profile(self, test_db, user_a):
        await user_repository.update_user_profile(
            user_a["id"], "小闯同学", "https://example.com/a.png"
        )
        found = await user_repository.get_user_by_id(user_a["id"])
        assert found["nickname"] == "小闯同学"
        assert found["avatar_url"] == "https://example.com/a.png"

        # 只更新昵称
        await user_repository.update_user_profile(user_a["id"], "新昵称", None)
        found = await user_repository.get_user_by_id(user_a["id"])
        assert found["nickname"] == "新昵称"
        assert found["avatar_url"] == "https://example.com/a.png"

    async def test_add_user_xp_accumulates(self, test_db, user_a):
        await user_repository.add_user_xp(user_a["id"], 35)
        await user_repository.add_user_xp(user_a["id"], 15)
        found = await user_repository.get_user_by_id(user_a["id"])
        assert found["total_xp"] == 50


class TestQuizRepositoryPersistence:
    async def _save_full_round(self, user_id: int, quiz_id: str) -> None:
        await quiz_repository.save_quiz_session(
            quiz_id=quiz_id,
            user_id=user_id,
            title="光合作用",
            summary="摘要",
            user_input="光合作用是怎么进行的？",
            questions_json=[
                {"id": "q1", "knowledge_point": "光合作用场所", "type": "single"},
                {"id": "q2", "knowledge_point": "光合作用条件", "type": "single"},
            ],
        )
        await quiz_repository.save_answer_record(
            quiz_id=quiz_id,
            user_id=user_id,
            records_json=[
                {"question_id": "q1", "selected_answers": ["A"], "is_correct": True, "duration_ms": 3000},
                {"question_id": "q2", "selected_answers": ["B"], "is_correct": False, "duration_ms": 5000},
            ],
            total_questions=2,
            correct_count=1,
            accuracy=50.0,
            total_duration_ms=8000,
        )
        await quiz_repository.save_report(
            quiz_id=quiz_id,
            user_id=user_id,
            report_json={
                "accuracy": 50,
                "mastered_points": ["光合作用场所"],
                "weak_points": ["光合作用条件"],
                "three_line_summary": ["总结一", "总结二", "总结三"],
                "advice": ["建议一"],
                "share_quote": "金句",
            },
        )

    async def test_answer_record_upsert(self, test_db, user_a):
        await quiz_repository.save_quiz_session(
            quiz_id="quiz_up",
            user_id=user_a["id"],
            title="T",
            summary="S",
            user_input="U",
            questions_json=[{"id": "q1"}],
        )
        inserted = await quiz_repository.save_answer_record(
            quiz_id="quiz_up",
            user_id=user_a["id"],
            records_json=[{"question_id": "q1", "is_correct": True, "duration_ms": 1000}],
            total_questions=1,
            correct_count=1,
            accuracy=100.0,
            total_duration_ms=1000,
        )
        assert inserted is True
        # 第二次（重试）应更新而非重复插入，并返回 False
        inserted_again = await quiz_repository.save_answer_record(
            quiz_id="quiz_up",
            user_id=user_a["id"],
            records_json=[{"question_id": "q1", "is_correct": True, "duration_ms": 1000}],
            total_questions=1,
            correct_count=1,
            accuracy=100.0,
            total_duration_ms=1000,
        )
        assert inserted_again is False

    async def test_roundtrip_detail(self, test_db, user_a):
        await self._save_full_round(user_a["id"], "quiz_rt")
        detail = await quiz_repository.get_quiz_detail("quiz_rt", user_a["id"])
        assert detail is not None
        assert detail["title"] == "光合作用"
        assert len(detail["questions"]) == 2
        assert len(detail["answer_records"]) == 2
        assert detail["report"]["share_quote"] == "金句"

    async def test_detail_not_found_for_other_user(self, test_db, user_a, user_b):
        await self._save_full_round(user_a["id"], "quiz_priv")
        assert await quiz_repository.get_quiz_detail("quiz_priv", user_b["id"]) is None

    async def test_history_list_fields_and_pagination(self, test_db, user_a):
        await self._save_full_round(user_a["id"], "quiz_h1")
        await self._save_full_round(user_a["id"], "quiz_h2")

        items, total = await quiz_repository.get_user_quiz_list(user_a["id"], 1, 1)
        assert total == 2
        assert len(items) == 1
        item = items[0]
        assert item["quiz_id"] == "quiz_h2"  # 最新的在前
        assert item["accuracy"] == 50.0
        assert item["question_count"] == 2
        assert item["duration_ms"] == 8000
        assert item["has_report"] is True
        assert item["report_snippet"] == "总结一"
        assert item["user_input"] == "光合作用是怎么进行的？"
        assert item["created_at"]

    async def test_history_only_completed_filter(self, test_db, user_a):
        await self._save_full_round(user_a["id"], "quiz_done")
        # 只出题、未答题
        await quiz_repository.save_quiz_session(
            quiz_id="quiz_todo",
            user_id=user_a["id"],
            title="未完成",
            summary="S",
            user_input="U",
            questions_json=[{"id": "q1"}],
        )
        items, total = await quiz_repository.get_user_quiz_list(
            user_a["id"], 1, 10, only_completed=True
        )
        assert total == 1
        assert items[0]["quiz_id"] == "quiz_done"

    async def test_history_start_time_filter(self, test_db, user_a):
        await self._save_full_round(user_a["id"], "quiz_recent")
        items, total = await quiz_repository.get_user_quiz_list(
            user_a["id"], 1, 10, start_time=datetime.now() - timedelta(days=7)
        )
        assert total == 1
        items, total = await quiz_repository.get_user_quiz_list(
            user_a["id"], 1, 10, start_time=datetime.now() + timedelta(days=1)
        )
        assert total == 0

    async def test_answer_stats(self, test_db, user_a, user_b):
        await self._save_full_round(user_a["id"], "quiz_s1")
        await self._save_full_round(user_b["id"], "quiz_s2")  # 不干扰

        stats = await quiz_repository.get_user_answer_stats(user_a["id"])
        assert stats["quiz_count"] == 1
        assert stats["correct_count"] == 1
        assert stats["average_accuracy"] == 50
        assert stats["total_duration_ms"] == 8000

        # 时间过滤：未来起点 → 0
        stats_future = await quiz_repository.get_user_answer_stats(
            user_a["id"], since=datetime.now() + timedelta(days=1)
        )
        assert stats_future["quiz_count"] == 0

    async def test_daily_stats_and_dates(self, test_db, user_a):
        await self._save_full_round(user_a["id"], "quiz_d1")
        rows = await quiz_repository.get_user_daily_stats(user_a["id"], days=7)
        assert len(rows) == 1
        date_val, count, acc = rows[0]
        assert count == 1
        assert float(acc) == 50.0

        dates = await quiz_repository.get_user_answer_dates(user_a["id"])
        assert len(dates) == 1
        assert dates[0] == date_val

    async def test_knowledge_data_pairs(self, test_db, user_a):
        await self._save_full_round(user_a["id"], "quiz_kd")
        pairs = await quiz_repository.get_user_knowledge_data(user_a["id"])
        assert len(pairs) == 1
        assert pairs[0]["title"] == "光合作用"
        assert len(pairs[0]["questions"]) == 2
        assert len(pairs[0]["records"]) == 2
