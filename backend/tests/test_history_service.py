"""闯关历史与统计服务测试（TDD：先写测试再实现 app/services/history_service.py）"""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.services import history_service


class TestPureAggregations:
    def test_compute_mastery_aggregates_by_knowledge_point(self):
        pairs = [
            {
                "title": "光合作用",
                "questions": [
                    {"id": "q1", "knowledge_point": "光合作用场所"},
                    {"id": "q2", "knowledge_point": "光合作用条件"},
                ],
                "records": [
                    {"question_id": "q1", "is_correct": True},
                    {"question_id": "q2", "is_correct": False},
                ],
            },
            {
                "title": "地球的公转",
                "questions": [
                    {"id": "q1", "knowledge_point": "昼夜与季节"},
                ],
                "records": [
                    {"question_id": "q1", "is_correct": False},
                ],
            },
        ]
        mastery = history_service.compute_mastery(pairs)
        by_point = {m["knowledge_point"]: m["accuracy"] for m in mastery}
        assert by_point["光合作用场所"] == 100
        assert by_point["光合作用条件"] == 0
        assert by_point["昼夜与季节"] == 0
        # 按正确率降序：100 在前
        assert mastery[0]["knowledge_point"] == "光合作用场所"

    def test_compute_mastery_multiple_records_same_point(self):
        pairs = [
            {
                "title": "A",
                "questions": [{"id": "q1", "knowledge_point": "KP1"}],
                "records": [{"question_id": "q1", "is_correct": True}],
            },
            {
                "title": "B",
                "questions": [{"id": "q2", "knowledge_point": "KP1"}],
                "records": [{"question_id": "q2", "is_correct": False}],
            },
        ]
        mastery = history_service.compute_mastery(pairs)
        assert mastery == [{"knowledge_point": "KP1", "accuracy": 50}]

    def test_compute_mastery_ignores_missing_records(self):
        pairs = [
            {
                "title": "A",
                "questions": [{"id": "q1", "knowledge_point": "KP1"}],
                "records": [],
            }
        ]
        assert history_service.compute_mastery(pairs) == []

    def test_weak_points_only_below_60_with_title(self):
        mastery = [
            {"knowledge_point": "A", "accuracy": 100},
            {"knowledge_point": "B", "accuracy": 60},
            {"knowledge_point": "C", "accuracy": 40},
        ]
        titles = {"C": "地球的公转"}
        weak = history_service.build_weak_points(mastery, titles)
        assert weak == [{"knowledge_point": "C", "accuracy": 40, "quiz_title": "地球的公转"}]

    def test_compute_streak_consecutive_ending_today(self):
        today = date.today()
        dates = [today, today - timedelta(days=1), today - timedelta(days=2)]
        assert history_service.compute_streak(dates) == 3

    def test_compute_streak_ending_yesterday(self):
        today = date.today()
        dates = [today - timedelta(days=1), today - timedelta(days=2)]
        assert history_service.compute_streak(dates) == 2

    def test_compute_streak_gap_breaks(self):
        today = date.today()
        dates = [today, today - timedelta(days=2), today - timedelta(days=3)]
        assert history_service.compute_streak(dates) == 1

    def test_compute_streak_empty(self):
        assert history_service.compute_streak([]) == 0

    def test_fill_daily_pads_missing_days(self):
        today = date.today()
        rows = {today: (1, 80.0), today - timedelta(days=2): (2, 60.0)}
        days = history_service.fill_daily(rows, days=7)
        assert len(days) == 7
        assert days[-1]["date"] == today.isoformat()
        assert days[-1]["accuracy"] == 80
        assert days[-1]["quiz_count"] == 1
        # 缺失的昨天：无数据
        assert days[-2]["accuracy"] is None
        assert days[-2]["quiz_count"] == 0
        # 标签按星期几
        assert days[-1]["label"] in "一二三四五六日"


class TestGetQuizHistory:
    @pytest.mark.asyncio
    async def test_returns_mapped_items(self):
        rows = [
            {
                "quiz_id": "quiz_1",
                "title": "光合作用",
                "user_input": "光合作用是怎么进行的？",
                "accuracy": 80.0,
                "question_count": 5,
                "duration_ms": 192000,
                "created_at": "2026-08-20 09:48:00",
                "has_report": True,
                "report_snippet": "光合作用是植物用阳光制造养料的过程。",
            }
        ]
        with patch(
            "app.services.history_service.quiz_repository.get_user_quiz_list",
            new_callable=AsyncMock,
            return_value=(rows, 1),
        ) as mock_list:
            result = await history_service.get_quiz_history(1, page=1, page_size=10)
        assert mock_list.call_args.kwargs["start_time"] is None
        assert mock_list.call_args.kwargs["only_completed"] is False
        assert result.total == 1
        item = result.items[0]
        assert item.quiz_id == "quiz_1"
        assert item.accuracy == 80.0
        assert item.has_report is True
        assert item.report_snippet

    @pytest.mark.asyncio
    async def test_range_week_sets_start_time(self):
        with patch(
            "app.services.history_service.quiz_repository.get_user_quiz_list",
            new_callable=AsyncMock,
            return_value=([], 0),
        ) as mock_list:
            await history_service.get_quiz_history(1, page=1, page_size=10, range="week")
        assert mock_list.call_args.kwargs["start_time"] is not None

    @pytest.mark.asyncio
    async def test_range_all_no_start_time(self):
        with patch(
            "app.services.history_service.quiz_repository.get_user_quiz_list",
            new_callable=AsyncMock,
            return_value=([], 0),
        ) as mock_list:
            await history_service.get_quiz_history(1, page=1, page_size=10, range="all")
        assert mock_list.call_args.kwargs["start_time"] is None


class TestGetQuizDetail:
    @pytest.mark.asyncio
    async def test_returns_detail(self):
        row = {
            "quiz_id": "quiz_1",
            "title": "光合作用",
            "summary": "摘要",
            "user_input": "输入",
            "questions": [{"id": "q1"}],
            "answer_records": [{"question_id": "q1", "is_correct": True}],
            "report": {"accuracy": 80},
            "created_at": "2026-08-20 09:48:00",
        }
        with patch(
            "app.services.history_service.quiz_repository.get_quiz_detail",
            new_callable=AsyncMock,
            return_value=row,
        ):
            detail = await history_service.get_quiz_detail("quiz_1", 1)
        assert detail is not None
        assert detail.quiz_id == "quiz_1"
        assert detail.report == {"accuracy": 80}

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self):
        with patch(
            "app.services.history_service.quiz_repository.get_quiz_detail",
            new_callable=AsyncMock,
            return_value=None,
        ):
            assert await history_service.get_quiz_detail("quiz_x", 1) is None


class TestGetUserStats:
    @pytest.mark.asyncio
    async def test_stats_composition(self):
        from datetime import date

        today = date.today()
        with patch(
            "app.services.history_service.quiz_repository.get_user_daily_stats",
            new_callable=AsyncMock,
            return_value=[(today, 1, 80.0)],
        ), patch(
            "app.services.history_service.quiz_repository.get_user_knowledge_data",
            new_callable=AsyncMock,
            return_value=[
                {
                    "title": "光合作用",
                    "questions": [
                        {"id": "q1", "knowledge_point": "光合作用场所"},
                        {"id": "q2", "knowledge_point": "光合作用条件"},
                    ],
                    "records": [
                        {"question_id": "q1", "is_correct": True},
                        {"question_id": "q2", "is_correct": False},
                    ],
                }
            ],
        ), patch(
            "app.services.history_service.quiz_repository.get_user_answer_dates",
            new_callable=AsyncMock,
            return_value=[today],
        ):
            stats = await history_service.get_user_stats(1)
        assert len(stats.days) == 7
        assert stats.days[-1].accuracy == 80
        assert stats.average_accuracy_7d == 80
        assert stats.streak_days == 1
        assert stats.mastery[0].knowledge_point == "光合作用场所"
        # 光合作用条件 0% → 薄弱点
        assert stats.weak_points[0].knowledge_point == "光合作用条件"
        assert stats.weak_points[0].quiz_title == "光合作用"
