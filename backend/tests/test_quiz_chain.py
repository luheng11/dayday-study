"""出题链测试（TDD，mock 大模型）"""

import pytest

from app.core.exceptions import QuizGenerationError
from app.llm.quiz_chain import generate_quiz
from tests.fake_llm import VALID_QUIZ_JSON, CapturingFakeModel


@pytest.fixture
def three_question_quiz_json() -> str:
    """3 题版题库（1 单选 + 1 多选 + 1 判断，符合 1:1:1 约定）"""
    return """{
      "title": "磁铁的秘密",
      "summary": "看不见的吸引力",
      "questions": [
        {
          "id": "q1",
          "type": "single",
          "stem": "磁铁两极相遇时，同名磁极会？",
          "options": [
            {"key": "A", "text": "相互排斥"},
            {"key": "B", "text": "相互吸引"},
            {"key": "C", "text": "没有反应"},
            {"key": "D", "text": "变成电流"}
          ],
          "answer": ["A"],
          "explanation": "①同名磁极相互排斥，所以选 A。②异名磁极才相互吸引。",
          "knowledge_point": "磁极规律",
          "difficulty": "easy"
        },
        {
          "id": "q2",
          "type": "multiple",
          "stem": "以下哪些东西能被磁铁吸住？",
          "options": [
            {"key": "A", "text": "铁钉"},
            {"key": "B", "text": "回形针"},
            {"key": "C", "text": "塑料尺"},
            {"key": "D", "text": "木筷子"}
          ],
          "answer": ["A", "B"],
          "explanation": "①磁铁只能吸铁、钴、镍，所以选 A 和 B。②塑料和木头都不行。",
          "knowledge_point": "磁铁吸铁",
          "difficulty": "medium"
        },
        {
          "id": "q3",
          "type": "judge",
          "stem": "磁铁有两极：南极和北极。",
          "options": [
            {"key": "A", "text": "正确"},
            {"key": "B", "text": "错误"}
          ],
          "answer": ["A"],
          "explanation": "①磁铁都有南极和北极两个磁极，所以这句话是对的，选 A。②指南针就是靠这个原理工作的。",
          "knowledge_point": "磁极",
          "difficulty": "easy"
        }
      ]
    }"""


class TestGenerateQuizSuccess:
    @pytest.mark.asyncio
    async def test_plain_json(self):
        model = CapturingFakeModel([VALID_QUIZ_JSON])
        quiz = await generate_quiz(
            user_input="光合作用", question_count=5, difficulty="medium", model=model
        )
        assert quiz.title == "光合作用"
        assert len(quiz.questions) == 5
        assert quiz.questions[0].type == "single"

    @pytest.mark.asyncio
    async def test_json_with_fence(self):
        fenced = "```json\n" + VALID_QUIZ_JSON + "\n```"
        model = CapturingFakeModel([fenced])
        quiz = await generate_quiz(
            user_input="光合作用", question_count=5, difficulty="medium", model=model
        )
        assert len(quiz.questions) == 5

    @pytest.mark.asyncio
    async def test_json_with_leading_noise(self):
        noisy = "好的，以下是为您生成的题库：\n" + VALID_QUIZ_JSON + "\n希望对你有帮助！"
        model = CapturingFakeModel([noisy])
        quiz = await generate_quiz(
            user_input="光合作用", question_count=5, difficulty="medium", model=model
        )
        assert quiz.title == "光合作用"

    @pytest.mark.asyncio
    async def test_three_questions(self, three_question_quiz_json):
        model = CapturingFakeModel([three_question_quiz_json])
        quiz = await generate_quiz(
            user_input="磁铁", question_count=3, difficulty="easy", model=model
        )
        assert len(quiz.questions) == 3
        types = {q.type for q in quiz.questions}
        assert types == {"single", "multiple", "judge"}

    @pytest.mark.asyncio
    async def test_prompt_contains_input_and_params(self):
        model = CapturingFakeModel([VALID_QUIZ_JSON])
        await generate_quiz(
            user_input="光合作用是怎么进行的",
            question_count=5,
            difficulty="medium",
            model=model,
        )
        text = model.joined_text()
        assert "光合作用是怎么进行的" in text
        assert "5" in text
        assert "medium" in text


class TestGenerateQuizRetry:
    @pytest.mark.asyncio
    async def test_retry_after_invalid_json(self):
        model = CapturingFakeModel(["这不是JSON", VALID_QUIZ_JSON])
        quiz = await generate_quiz(
            user_input="光合作用", question_count=5, difficulty="medium", model=model
        )
        assert model.call_count == 2
        assert len(quiz.questions) == 5

    @pytest.mark.asyncio
    async def test_retry_after_schema_invalid(self):
        bad = VALID_QUIZ_JSON.replace('"id": "q1"', '"id": 123', 1)
        model = CapturingFakeModel([bad, VALID_QUIZ_JSON])
        quiz = await generate_quiz(
            user_input="光合作用", question_count=5, difficulty="medium", model=model
        )
        assert model.call_count == 2
        assert len(quiz.questions) == 5

    @pytest.mark.asyncio
    async def test_retry_after_wrong_count(self):
        # 截掉最后一题：得到合法但只有 4 题的 JSON，触发题目数量校验
        cut = VALID_QUIZ_JSON[: VALID_QUIZ_JSON.rfind("},\n    {")] + "\n  ]\n}"
        model = CapturingFakeModel([cut, VALID_QUIZ_JSON])
        quiz = await generate_quiz(
            user_input="光合作用", question_count=5, difficulty="medium", model=model
        )
        assert model.call_count == 2
        assert len(quiz.questions) == 5

    @pytest.mark.asyncio
    async def test_retry_after_integrity_violation(self):
        bad = VALID_QUIZ_JSON.replace('"answer": ["A"],\n      "explanation": "①叶绿体',
                                      '"answer": ["Z"],\n      "explanation": "①叶绿体', 1)
        model = CapturingFakeModel([bad, VALID_QUIZ_JSON])
        quiz = await generate_quiz(
            user_input="光合作用", question_count=5, difficulty="medium", model=model
        )
        assert model.call_count == 2
        assert len(quiz.questions) == 5

    @pytest.mark.asyncio
    async def test_retry_after_empty_content(self):
        model = CapturingFakeModel(["", VALID_QUIZ_JSON])
        quiz = await generate_quiz(
            user_input="光合作用", question_count=5, difficulty="medium", model=model
        )
        assert model.call_count == 2
        assert len(quiz.questions) == 5


class TestGenerateQuizExhausted:
    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        model = CapturingFakeModel(["坏数据"] * 10)
        with pytest.raises(QuizGenerationError):
            await generate_quiz(
                user_input="光合作用", question_count=5, difficulty="medium", model=model
            )
        # 默认最多 3 次尝试
        assert model.call_count == 3

    @pytest.mark.asyncio
    async def test_error_message_friendly(self):
        model = CapturingFakeModel(["坏数据"] * 10)
        with pytest.raises(QuizGenerationError, match="题库生成失败"):
            await generate_quiz(
                user_input="光合作用", question_count=5, difficulty="medium", model=model
            )
