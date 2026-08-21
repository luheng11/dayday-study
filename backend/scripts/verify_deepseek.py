"""真实 DeepSeek 出题验证（LLM_MOCK=false 且已填 Key 时使用）

用法：
    .venv\\Scripts\\python scripts/verify_deepseek.py [主题]
"""

import asyncio
import sys
from pathlib import Path

# 保证从任意目录执行都能导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.llm.quiz_chain import generate_quiz  # noqa: E402


async def main() -> int:
    topic = sys.argv[1] if len(sys.argv) > 1 else "20以内的加减法"
    print(f"主题：{topic}（真实 DeepSeek 出题，3 题 / easy，最多 {60}s）")
    try:
        quiz = await generate_quiz(
            user_input=topic, question_count=3, difficulty="easy"
        )
    except Exception as exc:
        print(f"出题失败：{type(exc).__name__}: {exc}")
        return 1

    print(f"标题：{quiz.title}")
    print(f"摘要：{quiz.summary}")
    for q in quiz.questions:
        print(f"  [{q.type}/{q.difficulty}] {q.stem}")
        print(f"    答案: {q.answer}  知识点: {q.knowledge_point}")
    print("\n验证通过：真实 AI 出题正常")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
