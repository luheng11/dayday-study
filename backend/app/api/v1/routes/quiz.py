"""出题路由：同步生成 / 异步生成 / 任务轮询"""

from fastapi import APIRouter

from app.models.common import ApiResponse
from app.models.quiz import QuizGenerateRequest
from app.services.quiz_service import (
    create_quiz_task,
    get_quiz_task_status,
    handle_quiz_generate,
)

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/generate", response_model=ApiResponse)
async def quiz_generate(req: QuizGenerateRequest):
    """同步出题：直接返回题库（调试与纯文本快速出题场景）"""
    result = await handle_quiz_generate(req)
    return ApiResponse.success(data=result.model_dump())


@router.post("/generate/async", response_model=ApiResponse)
async def quiz_generate_async(req: QuizGenerateRequest):
    """异步出题：立即返回 task_id，前端轮询任务状态"""
    result = await create_quiz_task(req)
    return ApiResponse.success(data=result.model_dump())


@router.get("/task/{task_id}", response_model=ApiResponse)
async def quiz_task_status(task_id: str):
    """轮询异步出题任务状态"""
    result = await get_quiz_task_status(task_id)
    return ApiResponse.success(data=result.model_dump())
