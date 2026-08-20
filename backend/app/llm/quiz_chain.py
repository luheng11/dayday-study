"""出题 Chain：Prompt → DeepSeek → JSON 兜底解析 → Pydantic 校验 → 完整性校验 → 重试

JSON 输出五级保障（方案设计 4.3）：
1. Prompt 明确要求「只输出合法 JSON」；
2. extract_json 兼容 ```json 代码块包裹与前后噪声；
3. Pydantic Schema 校验（QuizOutput.model_validate）；
4. 字段完整性校验（validate_quiz_output：题数/选项/答案/题型）；
5. 失败自动重试（默认最多 3 次），仍失败抛出用户友好错误，绝不让脏数据到前端。
"""

import structlog
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.core.exceptions import QuizGenerationError
from app.llm.json_utils import extract_json
from app.models.quiz import QuizOutput
from app.prompts.quiz_prompt import (
    QUIZ_HUMAN_PROMPT,
    QUIZ_SYSTEM_PROMPT,
    SEARCH_CONTEXT_TEMPLATE,
    format_type_ratio_instruction,
)
from app.services.quiz_validation import validate_quiz_output

logger = structlog.get_logger()


async def generate_quiz(
    user_input: str,
    question_count: int = 5,
    difficulty: str = "mixed",
    search_context: str = "",
    model=None,
) -> QuizOutput:
    """生成题库。model 可注入（测试用 fake），缺省走 DeepSeek。"""
    settings = get_settings()

    if model is None:
        from app.llm.langchain_factory import get_chat_model

        model = get_chat_model(
            temperature=settings.quiz_temperature,
            top_p=settings.quiz_top_p,
            timeout=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )

    search_context_section = (
        SEARCH_CONTEXT_TEMPLATE.format(search_context=search_context)
        if search_context
        else ""
    )

    prompt = ChatPromptTemplate.from_messages(
        [("system", QUIZ_SYSTEM_PROMPT), ("human", QUIZ_HUMAN_PROMPT)]
    )
    chain = prompt | model

    messages = {
        "user_input": user_input,
        "question_count": question_count,
        "difficulty": difficulty,
        "type_ratio_instruction": format_type_ratio_instruction(question_count),
        "search_context_section": search_context_section,
    }

    for attempt in range(1, settings.llm_max_attempts + 1):
        try:
            result = await chain.ainvoke(messages)
            content = getattr(result, "content", None)
            if not content or not str(content).strip():
                raise ValueError("LLM 返回内容为空")

            data = extract_json(str(content))
            quiz = QuizOutput.model_validate(data)
            validate_quiz_output(quiz, expected_count=question_count)
            return quiz
        except Exception as exc:  # noqa: BLE001 —— 任何失败都进入重试兜底
            logger.warning(
                "quiz_generation_attempt_failed",
                attempt=attempt,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    raise QuizGenerationError("题库生成失败，请稍后重试")
