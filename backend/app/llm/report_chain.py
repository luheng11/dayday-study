"""报告 Chain：Prompt → DeepSeek → JSON 兜底解析 → Pydantic 校验 → 完整性校验 → 重试

accuracy 由本地统计覆盖（见 report_service），不信任模型输出。
"""

import structlog
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.core.exceptions import ReportGenerationError, ReportIntegrityError
from app.llm.json_utils import extract_json
from app.models.report import ReportOutput
from app.prompts.report_prompt import REPORT_HUMAN_PROMPT, REPORT_SYSTEM_PROMPT

logger = structlog.get_logger()


def _validate_report(report: ReportOutput) -> None:
    if len(report.three_line_summary) != 3:
        raise ReportIntegrityError(
            f"三句总结必须恰好 3 句，实际 {len(report.three_line_summary)} 句"
        )
    if not report.advice:
        raise ReportIntegrityError("复习建议不能为空")
    if not report.share_quote.strip():
        raise ReportIntegrityError("分享金句不能为空")
    if not (0 <= report.accuracy <= 100):
        raise ReportIntegrityError(f"正确率必须在 0~100，实际 {report.accuracy}")


async def generate_report(
    topic: str,
    questions: list,
    answer_records: list,
    score_summary: dict,
    model=None,
) -> ReportOutput:
    """生成复盘报告。model 可注入（测试用 fake），缺省走 DeepSeek。"""
    settings = get_settings()

    if model is None:
        from app.llm.langchain_factory import get_chat_model

        model = get_chat_model(
            temperature=settings.report_temperature,
            top_p=settings.report_top_p,
            timeout=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )

    import json

    prompt = ChatPromptTemplate.from_messages(
        [("system", REPORT_SYSTEM_PROMPT), ("human", REPORT_HUMAN_PROMPT)]
    )
    chain = prompt | model

    messages = {
        "topic": topic,
        "quiz_json": json.dumps(
            [q.model_dump() for q in questions], ensure_ascii=False
        ),
        "answer_records": json.dumps(
            [r.model_dump() for r in answer_records], ensure_ascii=False
        ),
        "score_summary": json.dumps(score_summary, ensure_ascii=False),
    }

    for attempt in range(1, settings.llm_max_attempts + 1):
        try:
            result = await chain.ainvoke(messages)
            content = getattr(result, "content", None)
            if not content or not str(content).strip():
                raise ValueError("LLM 返回内容为空")

            data = extract_json(str(content))
            report = ReportOutput.model_validate(data)
            _validate_report(report)
            return report
        except Exception as exc:  # noqa: BLE001 —— 任何失败都进入重试兜底
            logger.warning(
                "report_generation_attempt_failed",
                attempt=attempt,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    raise ReportGenerationError("报告生成失败，请稍后重试")
