"""报告路由（可选鉴权：有登录态时落答题记录/报告并累加 XP）"""

from typing import Optional

from fastapi import APIRouter, Depends

from app.core.auth import get_optional_user
from app.models.common import ApiResponse
from app.models.report import ReportGenerateRequest
from app.services.report_service import handle_report_generate

router = APIRouter(prefix="/report", tags=["report"])


@router.post("/generate", response_model=ApiResponse)
async def report_generate(
    req: ReportGenerateRequest,
    user_id: Optional[int] = Depends(get_optional_user),
):
    """生成复盘报告（准确率以服务端本地判分为准）"""
    result = await handle_report_generate(req, user_id=user_id)
    return ApiResponse.success(data=result.model_dump())
