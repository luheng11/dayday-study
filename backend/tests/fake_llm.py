"""测试辅助：Fake LLM（不消耗 API 额度）

langchain 1.x 中 RunnableSequence 只接受真正的 Runnable / callable / dict，
因此 fake 模型直接继承 FakeListChatModel（官方测试用假模型）。
"""

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage
from pydantic import PrivateAttr


def make_fake_model(responses: list[str]) -> FakeListChatModel:
    """按顺序返回给定文本的假模型（耗尽后重复最后一条）。"""
    return FakeListChatModel(responses=list(responses), sleep=0)


class CapturingFakeModel(FakeListChatModel):
    """FakeListChatModel 子类：额外记录每次调用的消息与次数。

    注意：
    - langchain-core 1.x 的 FakeListChatModel 接收 list[str]；
    - 它是 Pydantic 模型，实例状态必须用 PrivateAttr 声明。
    """

    _calls: list[list] = PrivateAttr(default_factory=list)
    _call_count: int = PrivateAttr(default=0)

    def __init__(self, responses: list[str]):
        super().__init__(responses=list(responses), sleep=0)

    @property
    def calls(self) -> list[list]:
        return self._calls

    @property
    def call_count(self) -> int:
        return self._call_count

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # 注意：这里不记录调用——FakeListChatModel 的异步路径内部可能
        # 再次调用 _generate，若两边都记录会导致次数翻倍。
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self._record(messages)
        return await super()._agenerate(
            messages, stop=stop, run_manager=run_manager, **kwargs
        )

    def _record(self, messages) -> None:
        self._call_count += 1
        self._calls.append(list(messages))

    def last_messages(self) -> list:
        return self.calls[-1]

    def joined_text(self) -> str:
        parts = []
        for msg in self.calls[-1]:
            content = getattr(msg, "content", "")
            parts.append(str(content))
        return "\n".join(parts)


VALID_QUIZ_JSON = """{
  "title": "光合作用",
  "summary": "植物用阳光制造养料的过程",
  "questions": [
    {
      "id": "q1",
      "type": "single",
      "stem": "光合作用主要发生在植物细胞的哪个部位？",
      "options": [
        {"key": "A", "text": "叶绿体"},
        {"key": "B", "text": "线粒体"},
        {"key": "C", "text": "细胞核"},
        {"key": "D", "text": "液泡"}
      ],
      "answer": ["A"],
      "explanation": "①叶绿体是光合作用的场所，所以选 A。②它就像植物细胞里的能量工厂。",
      "knowledge_point": "光合作用场所",
      "difficulty": "easy"
    },
    {
      "id": "q2",
      "type": "single",
      "stem": "光合作用释放的气体是？",
      "options": [
        {"key": "A", "text": "二氧化碳"},
        {"key": "B", "text": "氧气"},
        {"key": "C", "text": "氮气"},
        {"key": "D", "text": "水蒸气"}
      ],
      "answer": ["B"],
      "explanation": "①植物吸入二氧化碳、放出氧气，所以选 B。②这是最易错的一点，记牢！",
      "knowledge_point": "光合作用产物",
      "difficulty": "medium"
    },
    {
      "id": "q3",
      "type": "single",
      "stem": "光合作用需要光吗？",
      "options": [
        {"key": "A", "text": "需要"},
        {"key": "B", "text": "不需要"},
        {"key": "C", "text": "有时需要"},
        {"key": "D", "text": "不确定"}
      ],
      "answer": ["A"],
      "explanation": "①光是光合作用的条件之一，所以选 A。②没有光，植物无法制造养料。",
      "knowledge_point": "光合作用条件",
      "difficulty": "easy"
    },
    {
      "id": "q4",
      "type": "multiple",
      "stem": "以下哪些是光合作用需要的条件？",
      "options": [
        {"key": "A", "text": "阳光"},
        {"key": "B", "text": "水"},
        {"key": "C", "text": "二氧化碳"},
        {"key": "D", "text": "氧气"}
      ],
      "answer": ["A", "B", "C"],
      "explanation": "①光合作用三件套：阳光+水+二氧化碳，选 ABC。②氧气是产物不是条件。",
      "knowledge_point": "光合作用条件",
      "difficulty": "medium"
    },
    {
      "id": "q5",
      "type": "judge",
      "stem": "植物在夜晚也会进行光合作用。",
      "options": [
        {"key": "A", "text": "正确"},
        {"key": "B", "text": "错误"}
      ],
      "answer": ["B"],
      "explanation": "①没有光，光合作用无法进行，所以这句话是错的，选 B。②夜晚植物主要进行呼吸作用。",
      "knowledge_point": "光合作用与昼夜",
      "difficulty": "hard"
    }
  ]
}"""

VALID_REPORT_JSON = """{
  "accuracy": 80,
  "mastered_points": ["光合作用的场所", "光合作用的条件"],
  "weak_points": ["产物与原料的区分"],
  "three_line_summary": [
    "光合作用是植物用阳光+水+二氧化碳制造养料和氧气的过程。",
    "它发生在细胞的叶绿体里，所以叶子才绿油油的。",
    "记住「吸入 CO₂、放出 O₂」，就抓住了最易错的一点。"
  ],
  "advice": [
    "把「吸入 CO₂ / 放出 O₂」做成一张小卡片贴在书桌前",
    "明天同一时间再来闯一次，正确率冲 100%"
  ],
  "share_quote": "把不会的，变成会的。"
}"""
