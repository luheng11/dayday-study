"""端到端冒烟脚本：模拟小程序前端的完整调用链

  异步出题 → 轮询 → 提交答题记录 → 生成报告 → 校验正确率
  用法：先启动后端（LLM_MOCK=true），再执行：
    python scripts/e2e_smoke.py
"""

import asyncio
import sys

# Windows 控制台 GBK 下避免 emoji 输出报错
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx

BASE = "http://127.0.0.1:8000/api/v1"


async def main() -> int:
    # trust_env=False：忽略环境代理设置，直连本地服务
    async with httpx.AsyncClient(base_url=BASE, timeout=60, trust_env=False) as client:
        # 1. 健康检查
        health = (await client.get("/health")).json()
        assert health["code"] == 0, health
        print(f"[1/5] health OK: {health['data']['status']}")

        # 2. 异步出题
        create = (
            await client.post(
                "/quiz/generate/async",
                json={
                    "user_input": "光合作用是怎么进行的？",
                    "question_count": 5,
                    "difficulty": "medium",
                },
            )
        ).json()
        assert create["code"] == 0, create
        task_id = create["data"]["task_id"]
        print(f"[2/5] 异步出题任务已创建: {task_id}")

        # 3. 轮询任务（前端为 1.2s 间隔、60s 上限）
        result = None
        for _ in range(50):
            await asyncio.sleep(1.2)
            poll = (await client.get(f"/quiz/task/{task_id}")).json()
            assert poll["code"] == 0, poll
            status = poll["data"]["status"]
            print(f"      轮询状态: {status}")
            if status == "completed":
                result = poll["data"]["result"]
                break
            if status == "failed":
                print(f"      FAILED: {poll['data']['error_message']}")
                return 1
        assert result is not None, "任务超时未完成"
        questions = result["questions"]
        assert len(questions) == 5
        print(f"[3/5] 题库生成成功: {result['title']}（{len(questions)} 题）")

        # 4. 模拟前端本地判分：前 2 题答对、后 3 题答错
        records = []
        for i, q in enumerate(questions):
            is_correct = i < 2
            records.append(
                {
                    "question_id": q["id"],
                    "selected_answers": list(q["answer"]) if is_correct else ["Z"],
                    "is_correct": is_correct,
                    "duration_ms": 3000 + i * 500,
                }
            )

        # 5. 生成报告（服务端权威判分 → 正确率 40）
        report = (
            await client.post(
                "/report/generate",
                json={
                    "quiz_id": result["quiz_id"],
                    "topic": result["title"],
                    "questions": questions,
                    "answer_records": records,
                },
            )
        ).json()
        assert report["code"] == 0, report
        data = report["data"]
        assert data["accuracy"] == 40, f"正确率应为 40，实际 {data['accuracy']}"
        assert len(data["three_line_summary"]) == 3
        print(f"[5/5] 报告生成成功: 正确率 {data['accuracy']}%")
        print(f"      三句总结: {data['three_line_summary'][0]}")
        print(f"      分享金句: {data['share_quote']}")

    print("\n✅ 端到端闭环验证通过：输入 → 出题 → 轮询 → 答题 → 报告")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
