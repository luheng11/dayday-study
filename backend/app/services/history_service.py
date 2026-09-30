"""闯关历史与学习统计服务（原型 04 数据支撑）"""

from datetime import date, datetime, timedelta

from app.models.user import (
    DailyStat,
    MasteryItem,
    QuizDetailResponse,
    QuizHistoryItem,
    QuizHistoryList,
    UserStats,
    WeakPointItem,
)
from app.repositories import quiz_repository

# 薄弱知识点阈值：正确率 < 60%
WEAK_ACCURACY_THRESHOLD = 60

# 原型筛选范围（range 参数）
_RANGE_DAYS = {"week": 7, "month": None}


def _range_start(range_: str) -> datetime | None:
    """range=week → 最近 7 天起点；range=month → 本月 1 日 00:00；all → None。"""
    if range_ == "week":
        return datetime.now() - timedelta(days=7)
    if range_ == "month":
        now = datetime.now()
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


# ---- 纯函数聚合（单元测试覆盖） ----


def compute_mastery(pairs: list[dict]) -> list[dict]:
    """按知识点聚合正确率。

    pairs: [{title, questions: [{id, knowledge_point}], records: [{question_id, is_correct}]}]
    返回 [{knowledge_point, accuracy}]，按正确率降序。
    """
    correct: dict[str, int] = {}
    total: dict[str, int] = {}
    for pair in pairs:
        point_map = {q.get("id"): q.get("knowledge_point") for q in pair.get("questions", [])}
        for record in pair.get("records", []):
            point = point_map.get(record.get("question_id"))
            if not point:
                continue
            total[point] = total.get(point, 0) + 1
            if record.get("is_correct"):
                correct[point] = correct.get(point, 0) + 1

    mastery = [
        {"knowledge_point": point, "accuracy": round(correct.get(point, 0) / total[point] * 100)}
        for point in total
    ]
    mastery.sort(key=lambda m: (-m["accuracy"], m["knowledge_point"]))
    return mastery


def build_weak_points(mastery: list[dict], titles: dict[str, str]) -> list[dict]:
    """正确率 < 60% 的知识点 → 回炉提醒（附所属主题，取最近一次出现的主题）。"""
    weak = []
    for item in mastery:
        if item["accuracy"] < WEAK_ACCURACY_THRESHOLD:
            weak.append(
                {
                    "knowledge_point": item["knowledge_point"],
                    "accuracy": item["accuracy"],
                    "quiz_title": titles.get(item["knowledge_point"], ""),
                }
            )
    return weak


def compute_streak(dates: list) -> int:
    """连续学习天数：从今天（今天无记录则昨天）向前连续的天数。"""
    date_set = {d for d in dates if isinstance(d, date)}
    if not date_set:
        return 0

    today = date.today()
    anchor = today if today in date_set else today - timedelta(days=1)
    if anchor not in date_set:
        return 0

    streak = 0
    cursor = anchor
    while cursor in date_set:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def fill_daily(rows: dict, days: int = 7) -> list[dict]:
    """补齐近 N 天每日数据（含今天）：缺失日 accuracy=None。

    rows: {date: (quiz_count, accuracy)}；返回按日期升序的 [{date, label, accuracy, quiz_count}]。
    """
    today = date.today()
    result = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        row = rows.get(day)
        result.append(
            {
                "date": day.isoformat(),
                "label": "一二三四五六日"[day.weekday()],
                "accuracy": row[1] if row else None,
                "quiz_count": row[0] if row else 0,
            }
        )
    return result


# ---- 服务编排 ----


async def get_quiz_history(
    user_id: int,
    page: int = 1,
    page_size: int = 10,
    range: str = "all",
    only_completed: bool = False,
) -> QuizHistoryList:
    """闯关历史分页列表（含答题统计与报告摘要）。"""
    items, total = await quiz_repository.get_user_quiz_list(
        user_id=user_id,
        page=page,
        page_size=page_size,
        start_time=_range_start(range),
        only_completed=only_completed,
    )
    return QuizHistoryList(
        items=[QuizHistoryItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_quiz_detail(quiz_id: str, user_id: int) -> QuizDetailResponse | None:
    """单次闯关完整详情。"""
    detail = await quiz_repository.get_quiz_detail(quiz_id, user_id)
    if detail is None:
        return None
    return QuizDetailResponse(**detail)


async def get_user_stats(user_id: int) -> UserStats:
    """学习统计（原型 4.2）：7 日正确率、知识点掌握度、薄弱点、连续打卡。"""
    daily_rows = await quiz_repository.get_user_daily_stats(user_id, days=7)
    rows_map = {d: (count, acc) for d, count, acc in daily_rows}
    days = fill_daily(rows_map, days=7)

    pairs = await quiz_repository.get_user_knowledge_data(user_id)
    mastery = compute_mastery(pairs)
    titles: dict[str, str] = {}
    for pair in pairs:
        for q in pair.get("questions", []):
            point = q.get("knowledge_point")
            if point:
                titles.setdefault(point, pair.get("title", ""))

    dates = await quiz_repository.get_user_answer_dates(user_id)

    valid = [d["accuracy"] for d in days if d["accuracy"] is not None]
    average_7d = round(sum(valid) / len(valid)) if valid else 0

    return UserStats(
        days=[DailyStat(**d) for d in days],
        average_accuracy_7d=average_7d,
        mastery=[MasteryItem(**m) for m in mastery],
        weak_points=[
            WeakPointItem(**w) for w in build_weak_points(mastery, titles)
        ],
        streak_days=compute_streak(dates),
    )
