"""Mock 模式内置题库：无 DeepSeek Key 时用于演示与前后端联调（LLM_MOCK=true）

按输入主题关键词匹配 5 套 K12 题库（数学/光合作用/火山/磁铁/通用常识），
让演示数据与主题对应。每套结构：q1~q3 单选、q4 多选、q5 判断——
3 题模式取 [q1, q4, q5] 即 1:1:1 配比。
"""

from app.models.quiz import Question, QuizOutput
from app.models.report import ReportOutput

_Q = {
    "single": "single",
    "multiple": "multiple",
    "judge": "judge",
}


def _make_question(
    qid: str,
    qtype: str,
    stem: str,
    options: list[dict],
    answer: list[str],
    explanation: str,
    knowledge_point: str,
    difficulty: str = "easy",
) -> Question:
    return Question(
        id=qid,
        type=qtype,  # type: ignore[arg-type]
        stem=stem,
        options=options,
        answer=answer,
        explanation=explanation,
        knowledge_point=knowledge_point,
        difficulty=difficulty,  # type: ignore[arg-type]
    )


MATH_QUIZ = [
    _make_question(
        "q1", _Q["single"], "8 + 7 等于多少？",
        [{"key": "A", "text": "14"}, {"key": "B", "text": "15"},
         {"key": "C", "text": "16"}, {"key": "D", "text": "17"}],
        ["B"],
        "①8 加 7 等于 15，所以选 B。②可以这样算：先把 8 看成 5+3，5+7=12，再加 3 就是 15。",
        "进位加法",
    ),
    _make_question(
        "q2", _Q["single"], "15 - 9 等于多少？",
        [{"key": "A", "text": "5"}, {"key": "B", "text": "6"},
         {"key": "C", "text": "7"}, {"key": "D", "text": "8"}],
        ["B"],
        "①15 减 9 等于 6，所以选 B。②想：9+6=15，所以 15-9=6，加减法是一对好朋友。",
        "退位减法",
    ),
    _make_question(
        "q3", _Q["single"], "6 + 9 等于多少？",
        [{"key": "A", "text": "14"}, {"key": "B", "text": "15"},
         {"key": "C", "text": "16"}, {"key": "D", "text": "17"}],
        ["B"],
        "①6 加 9 等于 15，所以选 B。②把 6 拆成 1+5，1+9=10，再加 5 就是 15。",
        "凑十法",
    ),
    _make_question(
        "q4", _Q["multiple"], "下面哪些算式的结果等于 12？（可多选）",
        [{"key": "A", "text": "7 + 5"}, {"key": "B", "text": "20 - 8"},
         {"key": "C", "text": "4 + 9"}, {"key": "D", "text": "6 + 6"}],
        ["A", "B", "D"],
        "①7+5=12、20-8=12、6+6=12，所以选 A、B、D。②4+9=13，不是 12，小心别选它哦。",
        "20以内加减法",
        "medium",
    ),
    _make_question(
        "q5", _Q["judge"], "9 + 8 = 17，这个算式是正确的。",
        [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
        ["A"],
        "①9 加 8 确实等于 17，所以这句话是对的，选 A。②可以用 9+1+7=17 来验证。",
        "算式判断",
    ),
]

PHOTOSYNTHESIS_QUIZ = [
    _make_question(
        "q1", _Q["single"], "光合作用主要发生在植物细胞的哪个部位？",
        [{"key": "A", "text": "叶绿体"}, {"key": "B", "text": "线粒体"},
         {"key": "C", "text": "细胞核"}, {"key": "D", "text": "液泡"}],
        ["A"],
        "①叶绿体是光合作用的场所，所以选 A。②它就像植物细胞里的能量工厂，把阳光变成糖分。",
        "光合作用场所",
    ),
    _make_question(
        "q2", _Q["single"], "光合作用释放到空气中的气体是？",
        [{"key": "A", "text": "二氧化碳"}, {"key": "B", "text": "氧气"},
         {"key": "C", "text": "氮气"}, {"key": "D", "text": "水蒸气"}],
        ["B"],
        "①植物吸入二氧化碳、放出氧气，所以选 B。②这是最易错的一点，记牢：吸入 CO₂，放出 O₂。",
        "光合作用产物",
        "medium",
    ),
    _make_question(
        "q3", _Q["single"], "植物进行光合作用主要利用什么能量？",
        [{"key": "A", "text": "阳光"}, {"key": "B", "text": "风能"},
         {"key": "C", "text": "地热"}, {"key": "D", "text": "电能"}],
        ["A"],
        "①光合作用靠的是阳光，所以选 A。②没有光，植物就无法制造养料。",
        "光合作用条件",
    ),
    _make_question(
        "q4", _Q["multiple"], "以下哪些是光合作用需要的条件？（可多选）",
        [{"key": "A", "text": "阳光"}, {"key": "B", "text": "水"},
         {"key": "C", "text": "二氧化碳"}, {"key": "D", "text": "氧气"}],
        ["A", "B", "C"],
        "①光合作用三件套：阳光+水+二氧化碳，选 ABC。②氧气是结果，不是条件哦！",
        "光合作用条件",
        "medium",
    ),
    _make_question(
        "q5", _Q["judge"], "植物在夜晚也会进行光合作用。",
        [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
        ["B"],
        "①没有光，光合作用无法进行，所以这句话是错的，选 B。②夜晚植物主要进行呼吸作用。",
        "光合作用与昼夜",
        "hard",
    ),
]

VOLCANO_QUIZ = [
    _make_question(
        "q1", _Q["single"], "火山喷发时喷出的高温液体叫什么？",
        [{"key": "A", "text": "岩浆"}, {"key": "B", "text": "海水"},
         {"key": "C", "text": "石油"}, {"key": "D", "text": "泥浆"}],
        ["A"],
        "①火山喷出的高温液体是岩浆，所以选 A。②岩浆喷出地面后就叫「熔岩」啦。",
        "岩浆与熔岩",
    ),
    _make_question(
        "q2", _Q["single"], "火山喷发是地球哪个部分的活动引起的？",
        [{"key": "A", "text": "大气层"}, {"key": "B", "text": "地壳和地幔"},
         {"key": "C", "text": "海洋"}, {"key": "D", "text": "月亮"}],
        ["B"],
        "①火山喷发来自地壳和地幔深处的岩浆活动，所以选 B。②地球内部可热啦，像一锅滚烫的汤。",
        "地球内部结构",
    ),
    _make_question(
        "q3", _Q["single"], "岩浆冲出地面的「出口」叫什么？",
        [{"key": "A", "text": "火山口"}, {"key": "B", "text": "山洞"},
         {"key": "C", "text": "峡谷"}, {"key": "D", "text": "盆地"}],
        ["A"],
        "①岩浆喷出的出口叫火山口，所以选 A。②火山口就像火山的「嘴巴」。",
        "火山结构",
    ),
    _make_question(
        "q4", _Q["multiple"], "火山喷发可能带来哪些东西？（可多选）",
        [{"key": "A", "text": "火山灰"}, {"key": "B", "text": "熔岩"},
         {"key": "C", "text": "水蒸气"}, {"key": "D", "text": "冰川"}],
        ["A", "B", "C"],
        "①火山喷发会喷出火山灰、熔岩和大量气体（如水蒸气），选 ABC。②冰川不是火山喷出来的哦。",
        "火山喷发物",
        "medium",
    ),
    _make_question(
        "q5", _Q["judge"], "火山喷发时喷出的岩浆，来自地球的内部。",
        [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
        ["A"],
        "①岩浆确实来自地球内部，所以这句话是对的，选 A。②地球内部温度很高，岩石会熔化成岩浆。",
        "岩浆来源",
    ),
]

MAGNET_QUIZ = [
    _make_question(
        "q1", _Q["single"], "磁铁的两极相遇时，同名磁极会？",
        [{"key": "A", "text": "相互排斥"}, {"key": "B", "text": "相互吸引"},
         {"key": "C", "text": "没有反应"}, {"key": "D", "text": "变成电流"}],
        ["A"],
        "①同名磁极相互排斥，所以选 A。②异名磁极才相互吸引，记住「同极相斥、异极相吸」。",
        "磁极规律",
    ),
    _make_question(
        "q2", _Q["single"], "指南针的指针总是指向哪个方向？",
        [{"key": "A", "text": "东方"}, {"key": "B", "text": "西方"},
         {"key": "C", "text": "南方和北方"}, {"key": "D", "text": "随机方向"}],
        ["C"],
        "①指南针靠地球磁场工作，指针总指向南北方向，所以选 C。②在森林里迷路时它就是救命小帮手。",
        "指南针原理",
    ),
    _make_question(
        "q3", _Q["single"], "磁铁隔着纸片还能吸住铁钉吗？",
        [{"key": "A", "text": "能"}, {"key": "B", "text": "不能"},
         {"key": "C", "text": "只有湿纸才能"}, {"key": "D", "text": "要看天气"}],
        ["A"],
        "①磁力可以穿过纸片等非金属物体，所以选 A。②试试隔着玻璃吸回形针，也很好玩！",
        "磁力穿透",
    ),
    _make_question(
        "q4", _Q["multiple"], "以下哪些东西能被磁铁吸住？（可多选）",
        [{"key": "A", "text": "铁钉"}, {"key": "B", "text": "回形针"},
         {"key": "C", "text": "塑料尺"}, {"key": "D", "text": "木筷子"}],
        ["A", "B"],
        "①磁铁能吸铁、钴、镍等金属，铁钉和回形针都是铁做的，选 A、B。②塑料和木头都不行。",
        "磁性材料",
        "medium",
    ),
    _make_question(
        "q5", _Q["judge"], "磁铁有两个磁极：南极和北极。",
        [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
        ["A"],
        "①磁铁都有南极和北极两个磁极，所以这句话是对的，选 A。②指南针就是靠这两个磁极工作的。",
        "磁极",
    ),
]

GENERAL_QUIZ = [
    _make_question(
        "q1", _Q["single"], "一天有多少个小时？",
        [{"key": "A", "text": "12 小时"}, {"key": "B", "text": "24 小时"},
         {"key": "C", "text": "36 小时"}, {"key": "D", "text": "48 小时"}],
        ["B"],
        "①地球自转一圈是一天，约 24 小时，所以选 B。②白天和黑夜加起来就是 24 小时。",
        "时间常识",
    ),
    _make_question(
        "q2", _Q["single"], "一年有几个季节？",
        [{"key": "A", "text": "2 个"}, {"key": "B", "text": "3 个"},
         {"key": "C", "text": "4 个"}, {"key": "D", "text": "5 个"}],
        ["C"],
        "①一年有春夏秋冬四个季节，所以选 C。②每个季节大约 3 个月。",
        "四季",
    ),
    _make_question(
        "q3", _Q["single"], "红灯亮起时，过马路应该怎么做？",
        [{"key": "A", "text": "快速跑过去"}, {"key": "B", "text": "停下来等绿灯"},
         {"key": "C", "text": "慢慢走"}, {"key": "D", "text": "看心情决定"}],
        ["B"],
        "①红灯停、绿灯行，所以选 B。②安全第一，等绿灯亮了再走斑马线。",
        "交通安全",
    ),
    _make_question(
        "q4", _Q["multiple"], "下面哪些是水果？（可多选）",
        [{"key": "A", "text": "苹果"}, {"key": "B", "text": "香蕉"},
         {"key": "C", "text": "白菜"}, {"key": "D", "text": "西瓜"}],
        ["A", "B", "D"],
        "①苹果、香蕉、西瓜都是水果，选 A、B、D。②白菜是蔬菜，不是水果哦。",
        "生活常识",
    ),
    _make_question(
        "q5", _Q["judge"], "饭前洗手能让小手更干净卫生。",
        [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
        ["A"],
        "①饭前洗手能洗掉细菌，更卫生，所以选 A。②记得用七步洗手法，洗得更干净！",
        "卫生习惯",
    ),
]

_QUIZZES = {
    "math": MATH_QUIZ,
    "photosynthesis": PHOTOSYNTHESIS_QUIZ,
    "volcano": VOLCANO_QUIZ,
    "magnet": MAGNET_QUIZ,
    "general": GENERAL_QUIZ,
}

_KEYWORDS = {
    "math": ["加减法", "加法", "减法", "乘法", "除法", "口算", "算术", "数学", "算式", "计算", "数字"],
    "photosynthesis": ["光合", "植物", "生物", "叶绿", "叶子"],
    "volcano": ["火山", "地震", "岩浆", "地质"],
    "magnet": ["磁铁", "磁力", "磁场", "指南针", "磁极"],
}


def _match_quiz_key(topic: str) -> str:
    """按主题关键词匹配题库集"""
    for key, words in _KEYWORDS.items():
        if any(w in topic for w in words):
            return key
    return "general"


def build_mock_quiz(user_input: str, question_count: int, difficulty: str) -> QuizOutput:
    """构造演示题库：按主题匹配内容；3 题取 [q1,q4,q5]（1:1:1），>5 循环补齐。"""
    topic = user_input.strip()
    key = _match_quiz_key(topic)
    pool = _QUIZZES[key]

    if question_count == 3:
        indices = [0, 3, 4]  # 单选 / 多选 / 判断 各 1
    else:
        indices = list(range(len(pool)))

    questions: list[Question] = []
    for i in range(question_count):
        base = pool[indices[i % len(indices)]]
        copy = base.model_copy(deep=True)
        copy.id = f"q{i + 1}"
        questions.append(copy)

    return QuizOutput(
        title=topic[:30] or "闯关练习",
        summary=f"「{topic[:30]}」演示题库（Mock 模式，接入 DeepSeek Key 后由 AI 真实生成）",
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
