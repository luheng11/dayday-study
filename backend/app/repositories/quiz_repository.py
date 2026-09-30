"""题库 / 答题 / 报告数据访问层（MySQL）

- 落库函数在连接池未初始化时静默返回（可选登录：无 DB 不影响核心流程）；
- answer_records / reports 按 quiz_id 唯一，重复提交走 upsert（报告重试不重复计 XP）。
"""

import json
from datetime import datetime
from typing import Optional

from app.core.db import get_mysql_pool


def _parse_json(value):
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return value


def _format_dt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


# ---- 写入 ----


async def save_quiz_session(
    quiz_id: str,
    user_id: Optional[int],
    title: str,
    summary: str,
    user_input: str,
    questions_json: list,
) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO quiz_sessions "
                "(quiz_id, user_id, title, summary, user_input, questions_json) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    quiz_id,
                    user_id,
                    title,
                    summary,
                    user_input,
                    json.dumps(questions_json, ensure_ascii=False),
                ),
            )


async def save_answer_record(
    quiz_id: str,
    user_id: Optional[int],
    records_json: list,
    total_questions: int,
    correct_count: int,
    accuracy: float,
    total_duration_ms: int,
) -> bool:
    """upsert 答题记录。返回 True=新插入（可计 XP），False=更新已有记录。"""
    pool = get_mysql_pool()
    if pool is None:
        return False
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO answer_records "
                "(quiz_id, user_id, records_json, total_questions, correct_count, "
                " accuracy, total_duration_ms) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) AS new "
                "ON DUPLICATE KEY UPDATE "
                "  user_id = new.user_id,"
                "  records_json = new.records_json,"
                "  total_questions = new.total_questions,"
                "  correct_count = new.correct_count,"
                "  accuracy = new.accuracy,"
                "  total_duration_ms = new.total_duration_ms",
                (
                    quiz_id,
                    user_id,
                    json.dumps(records_json, ensure_ascii=False),
                    total_questions,
                    correct_count,
                    accuracy,
                    total_duration_ms,
                ),
            )
            # INSERT 成功 rowcount=1；UPDATE（含无变化）为 0 或 2
            return cur.rowcount == 1


async def save_report(quiz_id: str, user_id: Optional[int], report_json: dict) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO reports (quiz_id, user_id, report_json) "
                "VALUES (%s, %s, %s) AS new "
                "ON DUPLICATE KEY UPDATE "
                "  user_id = new.user_id, report_json = new.report_json",
                (quiz_id, user_id, json.dumps(report_json, ensure_ascii=False)),
            )


# ---- 查询 ----


async def get_user_answer_stats(
    user_id: int, since: Optional[datetime] = None
) -> dict:
    """用户答题统计（闯关次数/答对题数/平均正确率/总用时），可限定起始时间。"""
    pool = get_mysql_pool()
    if pool is None:
        return {"quiz_count": 0, "correct_count": 0, "average_accuracy": 0, "total_duration_ms": 0}
    params: list = [user_id]
    where = "user_id = %s"
    if since is not None:
        where += " AND created_at >= %s"
        params.append(since)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*), COALESCE(SUM(correct_count), 0), "
                f"COALESCE(AVG(accuracy), 0), COALESCE(SUM(total_duration_ms), 0) "
                f"FROM answer_records WHERE {where}",
                tuple(params),
            )
            row = await cur.fetchone()
            if row is None:
                return {"quiz_count": 0, "correct_count": 0, "average_accuracy": 0, "total_duration_ms": 0}
            return {
                "quiz_count": int(row[0]),
                "correct_count": int(row[1]),
                "average_accuracy": round(float(row[2])),
                "total_duration_ms": int(row[3]),
            }


async def get_user_quiz_list(
    user_id: int,
    page: int,
    page_size: int,
    start_time: Optional[datetime] = None,
    only_completed: bool = False,
) -> tuple[list[dict], int]:
    """分页历史列表（含答题统计与报告摘要）。返回 (items, total)。"""
    pool = get_mysql_pool()
    if pool is None:
        return [], 0

    where = "qs.user_id = %s"
    params: list = [user_id]
    if start_time is not None:
        where += " AND qs.created_at >= %s"
        params.append(start_time)
    if only_completed:
        where += " AND ar.quiz_id IS NOT NULL"

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) FROM quiz_sessions qs "
                f"LEFT JOIN answer_records ar ON qs.quiz_id = ar.quiz_id "
                f"WHERE {where}",
                tuple(params),
            )
            row = await cur.fetchone()
            total = int(row[0]) if row else 0

            offset = (page - 1) * page_size
            await cur.execute(
                "SELECT qs.quiz_id, qs.title, qs.user_input, "
                "       COALESCE(ar.accuracy, 0), COALESCE(ar.total_questions, 0), "
                "       COALESCE(ar.total_duration_ms, 0), qs.created_at, rp.report_json "
                "FROM quiz_sessions qs "
                "LEFT JOIN answer_records ar ON qs.quiz_id = ar.quiz_id "
                "LEFT JOIN reports rp ON qs.quiz_id = rp.quiz_id "
                f"WHERE {where} "
                "ORDER BY qs.created_at DESC, qs.id DESC "
                "LIMIT %s OFFSET %s",
                tuple(params + [page_size, offset]),
            )
            rows = await cur.fetchall()

    items = []
    for r in rows:
        report = _parse_json(r[7]) if r[7] is not None else None
        snippet = None
        if isinstance(report, dict):
            summary_lines = report.get("three_line_summary") or []
            if summary_lines:
                snippet = summary_lines[0]
        items.append(
            {
                "quiz_id": r[0],
                "title": r[1],
                "user_input": r[2],
                "accuracy": float(r[3]),
                "question_count": int(r[4]),
                "duration_ms": int(r[5]),
                "created_at": _format_dt(r[6]),
                "has_report": report is not None,
                "report_snippet": snippet,
            }
        )
    return items, total


async def get_quiz_detail(quiz_id: str, user_id: int) -> Optional[dict]:
    """单次闯关完整详情（题库 + 答题记录 + 报告），仅本人可见。"""
    pool = get_mysql_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT quiz_id, title, summary, user_input, questions_json, created_at "
                "FROM quiz_sessions WHERE quiz_id = %s AND user_id = %s",
                (quiz_id, user_id),
            )
            qs_row = await cur.fetchone()
            if qs_row is None:
                return None

            result = {
                "quiz_id": qs_row[0],
                "title": qs_row[1],
                "summary": qs_row[2],
                "user_input": qs_row[3],
                "questions": _parse_json(qs_row[4]),
                "created_at": _format_dt(qs_row[5]),
            }

            await cur.execute(
                "SELECT records_json FROM answer_records WHERE quiz_id = %s", (quiz_id,)
            )
            ar_row = await cur.fetchone()
            if ar_row:
                result["answer_records"] = _parse_json(ar_row[0])

            await cur.execute(
                "SELECT report_json FROM reports WHERE quiz_id = %s", (quiz_id,)
            )
            rp_row = await cur.fetchone()
            if rp_row:
                result["report"] = _parse_json(rp_row[0])

            return result


async def get_user_daily_stats(user_id: int, days: int = 7) -> list[tuple]:
    """近 N 天每日答题统计：[(date, quiz_count, avg_accuracy)]。"""
    pool = get_mysql_pool()
    if pool is None:
        return []
    from datetime import timedelta

    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=days - 1
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT DATE(created_at) AS d, COUNT(*), AVG(accuracy) "
                "FROM answer_records WHERE user_id = %s AND created_at >= %s "
                "GROUP BY d ORDER BY d",
                (user_id, start),
            )
            rows = await cur.fetchall()
    return [(r[0], int(r[1]), round(float(r[2]))) for r in rows]


async def get_user_knowledge_data(user_id: int) -> list[dict]:
    """用户全部（题库知识点 + 答题记录）对，供知识点掌握度聚合。"""
    pool = get_mysql_pool()
    if pool is None:
        return []
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT qs.title, qs.questions_json, ar.records_json "
                "FROM quiz_sessions qs "
                "JOIN answer_records ar ON qs.quiz_id = ar.quiz_id "
                "WHERE qs.user_id = %s",
                (user_id,),
            )
            rows = await cur.fetchall()
    return [
        {
            "title": r[0],
            "questions": _parse_json(r[1]) or [],
            "records": _parse_json(r[2]) or [],
        }
        for r in rows
    ]


async def get_user_answer_dates(user_id: int) -> list:
    """用户答题日期（去重，降序），用于连续学习天数计算。"""
    pool = get_mysql_pool()
    if pool is None:
        return []
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT DISTINCT DATE(created_at) AS d FROM answer_records "
                "WHERE user_id = %s ORDER BY d DESC",
                (user_id,),
            )
            rows = await cur.fetchall()
    return [r[0] for r in rows]
