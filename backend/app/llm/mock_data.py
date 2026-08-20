"""Mock 模式内置数据：无 DeepSeek Key 时用于演示与前后端联调（LLM_MOCK=true）

数据为 K12 示例题库「光合作用」与通用报告模板，内容质量与正式 Prompt 输出结构一致。
"""

from app.models.quiz import Question, QuizOutput
from app.models.report import ReportOutput

_MOCK_QUESTIONS_JSON = [
    {
        "id": "q1",
        "type": "single",
        "stem": "光合作用主要发生在植物细胞的哪个部位？",
        "options": [
            {"key": "A", "text": "叶绿体"},
            {"key": "B", "text": "线粒体"},
            {"key": "C", "text": "细胞核"},
            {"key": "D", "text": "液泡"},
        ],
        "answer": ["A"],
        "explanation": "①叶绿体是光合作用的场所，所以选 A。②它就像植物细胞里的能量工厂，把阳光变成糖分。",
        "knowledge_point": "光合作用场所",
        "difficulty": "easy",
    },
    {
        "id": "q2",
        "type": "single",
        "stem": "光合作用释放到空气中的气体是？",
        "options": [
            {"key": "A", "text": "二氧化碳"},
            {"key": "B", "text": "氧气"},
            {"key": "C", "text": "氮气"},
            {"key": "D", "text": "水蒸气"},
        ],
        "answer": ["B"],
        "explanation": "①植物吸入二氧化碳、放出氧气，所以选 B。②这是最易错的一点，记牢：吸入 CO₂，放出 O₂。",
        "knowledge_point": "光合作用产物",
        "difficulty": "medium",
    },
    {
        "id": "q3",
        "type": "single",
        "stem": "植物在白天进行光合作用，主要利用什么能量？",
        "options": [
            {"key": "A", "text": "阳光"},
            {"key": "B", "text": "风能"},
            {"key": "C", "text": "地热"},
            {"key": "D", "text": "电能"},
        ],
        "answer": ["A"],
        "explanation": "①光合作用靠的是阳光，所以选 A。②没有光，植物就无法制造养料。",
        "knowledge_point": "光合作用条件",
        "difficulty": "easy",
    },
    {
        "id": "q4",
        "type": "multiple",
        "stem": "以下哪些是光合作用需要的条件？",
        "options": [
            {"key": "A", "text": "阳光"},
            {"key": "B", "text": "水"},
            {"key": "C", "text": "二氧化碳"},
            {"key": "D", "text": "氧气"},
        ],
        "answer": ["A", "B", "C"],
        "explanation": "①光合作用三件套：阳光+水+二氧化碳，选 ABC。②氧气是结果，不是条件哦！",
        "knowledge_point": "光合作用条件",
        "difficulty": "medium",
    },
    {
        "id": "q5",
        "type": "judge",
        "stem": "植物在夜晚也会进行光合作用。",
        "options": [
            {"key": "A", "text": "正确"},
            {"key": "B", "text": "错误"},
        ],
        "answer": ["B"],
        "explanation": "①没有光，光合作用无法进行，所以这句话是错的，选 B。②夜晚植物主要进行呼吸作用。",
        "knowledge_point": "光合作用与昼夜",
        "difficulty": "hard",
    },
]

_MOCK_QUESTIONS = [Question(**q) for q in _MOCK_QUESTIONS_JSON]


def build_mock_quiz(user_input: str, question_count: int, difficulty: str) -> QuizOutput:
    """构造演示题库：3 题取 1:1:1（q1 单选 / q4 多选 / q5 判断），其余取完整 5 题，>5 循环补齐。"""
    if question_count == 3:
        pool = [0, 3, 4]  # q1 单选、q4 多选、q5 判断
    else:
        pool = list(range(len(_MOCK_QUESTIONS)))

    questions: list[Question] = []
    for i in range(question_count):
        base = _MOCK_QUESTIONS[pool[i % len(pool)]]
        copy = base.model_copy(deep=True)
        copy.id = f"q{i + 1}"
        questions.append(copy)

    return QuizOutput(
        title=user_input.strip()[:30] or "闯关练习",
        summary=f"围绕「{user_input.strip()[:30]}」生成的演示题库（Mock 模式）",
        questions=questions,
    )


def build_mock_report(topic: str, score_summary: dict) -> ReportOutput:
    """构造演示报告：accuracy 直接采用本地统计。"""
    correct = score_summary.get("correct", 0)
    total = score_summary.get("total", 0)
    if total > 0 and correct == total:
        weak: list[str] = []
    else:
        weak = ["部分知识点还需要再巩固"]

    return ReportOutput(
        accuracy=score_summary.get("accuracy", 0),
        mastered_points=["闯关完成的知识点"],
        weak_points=weak,
        three_line_summary=[
            f"你已经完成了「{topic}」的闯关练习。",
            "把题目里的讲解再读一遍，记忆会更牢固。",
            "坚持每天闯一关，知识会越来越扎实。",
        ],
        advice=[
            "把做错的题目再闯一遍，直到全对",
            "用自己的话把今天学的讲给家人听一听",
        ],
        share_quote="把不会的，变成会的。",
    )
