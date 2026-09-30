"""报告服务：参数校验 → 服务端权威判分 → AI 生成报告 → 本地准确率覆盖 → 登录态落库"""

import structlog

from app.core.exceptions import BusinessError, ReportGenerationError
from app.llm.report_chain import generate_report
from app.models.report import ReportGenerateRequest, ReportGenerateResponse
from app.repositories import quiz_repository, user_repository
from app.services.scoring_service import compute_score_summary, total_xp

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
    user_id: int | None = None,
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

    await _persist_round(req, corrected_records, score_summary, report_output, user_id)

    return ReportGenerateResponse(**report_output.model_dump())


async def _persist_round(
    req: ReportGenerateRequest,
    corrected_records,
    score_summary: dict,
    report_output,
    user_id: int | None,
) -> None:
    """有登录态时落答题记录 + 报告，并按 M1 分值规则累加 XP（10/15/10⭐）。

    答题记录 upsert：重复生成报告（重试）只更新记录、不重复加 XP。
    落库失败绝不影响主流程。
    """
    if user_id is None:
        return
    try:
        inserted = await quiz_repository.save_answer_record(
            quiz_id=req.quiz_id,
            user_id=user_id,
            records_json=[r.model_dump() for r in corrected_records],
            total_questions=score_summary["total"],
            correct_count=score_summary["correct"],
            accuracy=score_summary["accuracy"],
            total_duration_ms=sum(r.duration_ms for r in corrected_records),
        )
        await quiz_repository.save_report(
            quiz_id=req.quiz_id,
            user_id=user_id,
            report_json=report_output.model_dump(),
        )
        if inserted:
            xp = total_xp(corrected_records, {q.id: q.type for q in req.questions})
            await user_repository.add_user_xp(user_id, xp)
    except Exception as exc:  # noqa: BLE001 —— 落库是尽力而为
        logger.error("report_persist_failed", quiz_id=req.quiz_id, error=str(exc))
