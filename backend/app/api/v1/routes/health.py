"""健康检查路由"""

from fastapi import APIRouter

from app.models.common import ApiResponse

router = APIRouter(prefix="/health", tags=["health"])

SERVICE_NAME = "闯关学堂"
VERSION = "0.1.0"


@router.get("", response_model=ApiResponse)
async def health_check():
    return ApiResponse.success(
        data={"status": "ok", "service": SERVICE_NAME, "version": VERSION}
    )
