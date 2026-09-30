"""用户路由：登录 / 档案 / 历史 / 统计 / 头像上传"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile

from app.core.auth import get_current_user
from app.models.common import ApiResponse
from app.models.user import LoginRequest, UpdateProfileRequest
from app.services import history_service, user_service

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/login", response_model=ApiResponse)
async def login(req: LoginRequest):
    result = await user_service.handle_login(req.code)
    return ApiResponse.success(data=result.model_dump())


@router.get("/profile", response_model=ApiResponse)
async def get_profile(user_id: int = Depends(get_current_user)):
    result = await user_service.get_profile(user_id)
    return ApiResponse.success(data=result.model_dump())


@router.put("/profile", response_model=ApiResponse)
async def update_profile(
    req: UpdateProfileRequest,
    user_id: int = Depends(get_current_user),
):
    await user_service.update_profile(user_id, req.nickname, req.avatar_url)
    return ApiResponse.success()


@router.get("/quizzes", response_model=ApiResponse)
async def get_quiz_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    range: Literal["all", "week", "month"] = Query("all"),
    only_completed: bool = Query(False),
    user_id: int = Depends(get_current_user),
):
    result = await history_service.get_quiz_history(
        user_id, page=page, page_size=page_size, range=range, only_completed=only_completed
    )
    return ApiResponse.success(data=result.model_dump())


@router.get("/stats", response_model=ApiResponse)
async def get_stats(user_id: int = Depends(get_current_user)):
    result = await history_service.get_user_stats(user_id)
    return ApiResponse.success(data=result.model_dump())


@router.post("/avatar", response_model=ApiResponse)
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user),
):
    """上传头像（微信 chooseAvatar 临时文件 → 本地持久化），返回可访问 URL"""
    content = await file.read()
    relative_url = await user_service.save_avatar(user_id, content, file.content_type or "")
    avatar_url = str(request.base_url).rstrip("/") + relative_url
    await user_service.update_profile(user_id, None, avatar_url)
    return ApiResponse.success(data={"avatar_url": avatar_url})


@router.get("/quizzes/{quiz_id}", response_model=ApiResponse)
async def get_quiz_detail(
    quiz_id: str,
    user_id: int = Depends(get_current_user),
):
    result = await history_service.get_quiz_detail(quiz_id, user_id)
    if result is None:
        return ApiResponse.error(code=4004, message="闯关记录不存在")
    return ApiResponse.success(data=result.model_dump())
