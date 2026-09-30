"""用户系统端到端验收（真实 DeepSeek + 真实 MySQL）：
登录 → 出题落库 → 报告落库+XP → 档案/历史/详情/统计回看 → 匿名回归
运行：.venv\\Scripts\\python scripts/e2e_user_system.py（需后端已启动）
"""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_base import API_BASE as BASE  # noqa: E402


def post(client: httpx.Client, path: str, body: dict, token: str | None = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = client.post(f"{BASE}{path}", json=body, headers=headers, timeout=90)
    resp.raise_for_status()
    return resp.json()


def get(client: httpx.Client, path: str, token: str | None = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = client.get(f"{BASE}{path}", headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    # trust_env=False：本机环回地址不走系统代理（避免代理返回 502）
    with httpx.Client(timeout=90, trust_env=False) as client:
        # 1. 登录（开发降级模式）
        login = post(client, "/user/login", {"code": "dev_openid_e2e"})
        token = login["data"]["token"]
        print(
            f"1. LOGIN OK: user_id={login['data']['user']['id']} "
            f"nickname={login['data']['user']['nickname']} token_len={len(token)}"
        )

        # 2. 初始档案（记录基线：脚本需可重复运行，断言一律用增量而非绝对值）
        p0 = get(client, "/user/profile", token)["data"]
        print(
            f"2. PROFILE INIT: quiz_count={p0['quiz_count']} xp={p0['total_xp']} "
            f"level=Lv.{p0['level']['level']}-{p0['level']['title']}"
        )

        # 3. 出题（真实 DeepSeek，3 题）+ 落库
        quiz = post(
            client,
            "/quiz/generate",
            {"user_input": "勾股定理是什么？为什么重要？", "question_count": 3, "difficulty": "medium"},
            token,
        )["data"]
        quiz_id = quiz["quiz_id"]
        print(f"3. QUIZ OK: quiz_id={quiz_id} title={quiz['title']} questions={len(quiz['questions'])}")

        # 4. 全对提交 + 报告生成（落库 + XP）
        records = [
            {
                "question_id": q["id"],
                "selected_answers": q["answer"],
                "is_correct": True,
                "duration_ms": 2000,
            }
            for q in quiz["questions"]
        ]
        report = post(
            client,
            "/report/generate",
            {
                "quiz_id": quiz_id,
                "topic": quiz["title"],
                "questions": quiz["questions"],
                "answer_records": records,
            },
            token,
        )["data"]
        print(f"4. REPORT OK: accuracy={report['accuracy']} quote={report['share_quote']}")

        # 5. 档案更新（增量断言）
        p1 = get(client, "/user/profile", token)["data"]
        print(
            f"5. PROFILE UPDATED: quiz_count={p1['quiz_count']} correct={p1['correct_count']} "
            f"avg={p1['average_accuracy']} xp={p1['total_xp']} week={p1['week_quiz_count']} "
            f"streak={p1['streak_days']}"
        )
        assert p1["quiz_count"] == p0["quiz_count"] + 1, (
            f"闯关次数应 +1：{p0['quiz_count']} -> {p1['quiz_count']}"
        )
        assert p1["correct_count"] == p0["correct_count"] + len(records), (
            f"答对题数应 +{len(records)}：{p0['correct_count']} -> {p1['correct_count']}"
        )
        xp_gain = p1["total_xp"] - p0["total_xp"]
        assert xp_gain > 0, "本次闯关应累加 XP"
        # 全部答对时，XP 应等于该题库的分值总和（单选 10 / 多选 15 / 判断 10）
        XP_BY_TYPE = {"single": 10, "multiple": 15, "judge": 10}
        expected_xp = sum(XP_BY_TYPE[q["type"]] for q in quiz["questions"])
        assert xp_gain == expected_xp, f"XP 累加应为 {expected_xp}，实际 {xp_gain}"
        print(f"5b. XP DELTA OK: +{xp_gain}（符合 10/15/10 规则）")

        # 6. 历史列表
        hlist = get(client, "/user/quizzes?page=1&page_size=10&only_completed=true", token)["data"]
        first = hlist["items"][0]
        print(
            f"6. HISTORY LIST: total={hlist['total']} first={first['title']} "
            f"acc={first['accuracy']} has_report={first['has_report']} snippet={first['report_snippet']}"
        )
        assert first["has_report"] is True

        # 7. 历史详情
        detail = get(client, f"/user/quizzes/{quiz_id}", token)["data"]
        print(
            f"7. DETAIL OK: questions={len(detail['questions'])} "
            f"records={len(detail['answer_records'])} report_acc={detail['report']['accuracy']}"
        )

        # 8. 学习统计
        stats = get(client, "/user/stats", token)["data"]
        print(
            f"8. STATS OK: days={len(stats['days'])} avg7d={stats['average_accuracy_7d']} "
            f"mastery={len(stats['mastery'])} weak={len(stats['weak_points'])} streak={stats['streak_days']}"
        )
        assert len(stats["days"]) == 7
        assert stats["streak_days"] >= 1

        # 9. 匿名回归：出题/报告可用（不落库）；档案 401
        anon_quiz = post(
            client,
            "/quiz/generate",
            {"user_input": "为什么会有四季？", "question_count": 3, "difficulty": "medium"},
        )["data"]
        print(f"9a. ANON QUIZ OK: quiz_id={anon_quiz['quiz_id']} (not persisted)")
        anon_records = [
            {
                "question_id": q["id"],
                "selected_answers": q["answer"],
                "is_correct": True,
                "duration_ms": 1500,
            }
            for q in anon_quiz["questions"]
        ]
        anon_report = post(
            client,
            "/report/generate",
            {
                "quiz_id": anon_quiz["quiz_id"],
                "topic": anon_quiz["title"],
                "questions": anon_quiz["questions"],
                "answer_records": anon_records,
            },
        )["data"]
        print(f"9b. ANON REPORT OK: accuracy={anon_report['accuracy']} (not persisted)")
        resp = client.get(f"{BASE}/user/profile")
        assert resp.status_code == 401 and resp.json()["code"] == 4010
        print("9c. ANON PROFILE REJECTED: 401/4010")

        # 10. range 过滤
        week_list = get(client, "/user/quizzes?page=1&page_size=10&range=week", token)["data"]
        print(f"10. RANGE=WEEK LIST: total={week_list['total']}")

    print("========== E2E ACCEPTANCE PASSED ==========")


if __name__ == "__main__":
    main()
