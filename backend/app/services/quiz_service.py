"""出题服务：内容安全 → AI 出题 → 组装响应；异步任务模式"""

import asyncio
import uuid

import structlog

from app.core.exceptions import (
    ContentFilterError,
    QuizGenerationError,
    TaskNotFoundError,
)
from app.llm.mock_data import build_mock_quiz
from app.llm.quiz_chain import generate_quiz
from app.models.quiz import (
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizTaskCreateResponse,
    QuizTaskStatusResponse,
)
from app.core.security import check_content
from app.services.task_store import task_store

logger = structlog.get_logger()

# 测试注入点：为 None 时走真实 DeepSeek（见 quiz_chain）
llm_model = None


def _new_quiz_id() -> str:
    return f"quiz_{uuid.uuid4().hex[:12]}"


def _new_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


async def _run_generation(req: QuizGenerateRequest) -> QuizGenerateResponse:
    """核心生成流程（同步/异步共用）"""
    from app.core.config import get_settings

    if llm_model is None and get_settings().llm_mock:
        # Mock 模式：无 Key 联调/演示用内置题库
        quiz_output = build_mock_quiz(
            user_input=req.user_input,
            question_count=req.question_count,
            difficulty=req.difficulty,
        )
    else:
        quiz_output = await generate_quiz(
            user_input=req.user_input,
            question_count=req.question_count,
            difficulty=req.difficulty,
            model=llm_model,
        )
    return QuizGenerateResponse(
        quiz_id=_new_quiz_id(),
        title=quiz_output.title,
        summary=quiz_output.summary,
        questions=quiz_output.questions,
    )


async def handle_quiz_generate(req: QuizGenerateRequest) -> QuizGenerateResponse:
    """同步出题：直接返回题库"""
    if not check_content(req.user_input):
        raise ContentFilterError("输入内容包含不当内容，请修改后重试")

    try:
        return await _run_generation(req)
    except QuizGenerationError:
        raise
    except Exception as exc:
        logger.error("quiz_generation_failed", error=str(exc))
        raise QuizGenerationError("题库生成失败，请稍后重试") from exc


async def create_quiz_task(req: QuizGenerateRequest) -> QuizTaskCreateResponse:
    """异步出题：立即返回 task_id，后台执行"""
    if not check_content(req.user_input):
        raise ContentFilterError("输入内容包含不当内容，请修改后重试")

    task_id = _new_task_id()
    await task_store.create(task_id)
    asyncio.create_task(_run_quiz_task(task_id, req))
    return QuizTaskCreateResponse(task_id=task_id)


async def _run_quiz_task(task_id: str, req: QuizGenerateRequest) -> None:
    await task_store.set_status(task_id, "running")
    logger.info("quiz_task_started", task_id=task_id)
    try:
        result = await _run_generation(req)
        await task_store.complete(task_id, result.model_dump())
        logger.info("quiz_task_completed", task_id=task_id, quiz_id=result.quiz_id)
    except Exception as exc:  # noqa: BLE001 —— 任务失败统一落 failed 状态
        message = "题库生成失败，请稍后重试"
        logger.error("quiz_task_failed", task_id=task_id, error=str(exc))
        await task_store.fail(task_id, message)


async def get_quiz_task_status(task_id: str) -> QuizTaskStatusResponse:
    """轮询任务状态"""
    entry = await task_store.get(task_id)
    if entry is None:
        raise TaskNotFoundError("任务不存在或已过期")

    result = None
    if entry.status == "completed" and entry.result is not None:
        result = QuizGenerateResponse.model_validate(entry.result)

    return QuizTaskStatusResponse(
        task_id=task_id,
        status=entry.status,
        result=result,
        error_message=entry.error_message,
    )
