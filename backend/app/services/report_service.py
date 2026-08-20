"""报告服务：参数校验 → 服务端权威判分 → AI 生成报告 → 本地准确率覆盖"""

import structlog

from app.core.exceptions import BusinessError, ReportGenerationError
from app.llm.report_chain import generate_report
from app.models.report import ReportGenerateRequest, ReportGenerateResponse
from app.services.scoring_service import compute_score_summary

logger = structlog.get_logger()

# 测试注入点：为 None 时走真实 DeepSeek（见 report_chain）
llm_model = None


def _validate_and_rejudge(req: ReportGenerateRequest):
    """校验答题记录与题目一一对应，并按 selected_answers 重判（不信任客户端）。"""
    question_ids = [q.id for q in req.questions]
    if len(question_ids) != len(set(question_ids)):
        raise BusinessError("题目数据存在重复 id")

    record_ids = [r.question_id for r in req.answer_records]
    if len(record_ids) != len(set(record_ids)):
        raise BusinessError("答题记录存在重复题目")

    if set(record_ids) != set(question_ids) or len(record_ids) != len(question_ids):
        raise BusinessError("答题记录与题目数量不一致")

    key_map = {q.id: q for q in req.questions}
    corrected = []
    for record in req.answer_records:
        question = key_map[record.question_id]
        is_correct = set(record.selected_answers) == set(question.answer)
        corrected.append(record.model_copy(update={"is_correct": is_correct}))
    return corrected


async def handle_report_generate(
    req: ReportGenerateRequest,
) -> ReportGenerateResponse:
    corrected_records = _validate_and_rejudge(req)
    score_summary = compute_score_summary(corrected_records)

    try:
        from app.core.config import get_settings

        if llm_model is None and get_settings().llm_mock:
            from app.llm.mock_data import build_mock_report

            report_output = build_mock_report(topic=req.topic, score_summary=score_summary)
        else:
            report_output = await generate_report(
                topic=req.topic,
                questions=req.questions,
                answer_records=corrected_records,
                score_summary=score_summary,
                model=llm_model,
            )
    except ReportGenerationError:
        raise
    except Exception as exc:
        logger.error("report_generation_failed", error=str(exc))
        raise ReportGenerationError("报告生成失败，请稍后重试") from exc

    # 本地统计为权威：覆盖 AI 可能编造的 accuracy
    report_output.accuracy = score_summary["accuracy"]

    return ReportGenerateResponse(**report_output.model_dump())
