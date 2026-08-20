"""报告路由"""

from fastapi import APIRouter

from app.models.common import ApiResponse
from app.models.report import ReportGenerateRequest
from app.services.report_service import handle_report_generate

router = APIRouter(prefix="/report", tags=["report"])


@router.post("/generate", response_model=ApiResponse)
async def report_generate(req: ReportGenerateRequest):
    """生成复盘报告（准确率以服务端本地判分为准）"""
    result = await handle_report_generate(req)
    return ApiResponse.success(data=result.model_dump())
