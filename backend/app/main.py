"""FastAPI 应用入口：路由注册 + 统一异常处理 + structlog 日志"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import health, quiz, report
from app.core.config import get_settings
from app.core.exceptions import (
    BusinessError,
    ContentFilterError,
    QuizGenerationError,
    ReportGenerationError,
    TaskNotFoundError,
)
from app.models.common import ApiResponse

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("app_starting", host=settings.app_host, port=settings.app_port)
    yield
    logger.info("app_shutting_down")


app = FastAPI(
    title="闯关学堂 · AI 知识闯关学习（K12）",
    description="输入想学的知识 → AI 出题 → 闯关答题 → AI 复盘报告（M1 核心闭环）",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS（开发与 H5 调试）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(health.router, prefix="/api/v1")
app.include_router(quiz.router, prefix="/api/v1")
app.include_router(report.router, prefix="/api/v1")


# ---- 统一异常处理（错误码分段：400x 业务 / 401x 鉴权 / 500x 服务端） ----


@app.exception_handler(ContentFilterError)
async def content_filter_handler(request: Request, exc: ContentFilterError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4000, message=str(exc)).model_dump(),
    )


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4001, message=str(exc)).model_dump(),
    )


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(request: Request, exc: TaskNotFoundError):
    return JSONResponse(
        status_code=404,
        content=ApiResponse.error(code=4002, message=str(exc)).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """把 FastAPI 默认 422 转成统一响应（code 4001，不暴露内部结构）。"""
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    message = f"参数错误：{first.get('msg', '请求参数不合法')}"
    if field:
        message = f"参数错误（{field}）：{first.get('msg', '请求参数不合法')}"
    logger.warning("request_validation_failed", field=field, error=str(message))
    return JSONResponse(
        status_code=422,
        content=ApiResponse.error(code=4001, message=message).model_dump(),
    )


@app.exception_handler(QuizGenerationError)
async def quiz_error_handler(request: Request, exc: QuizGenerationError):
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(code=5001, message=str(exc)).model_dump(),
    )


@app.exception_handler(ReportGenerationError)
async def report_error_handler(request: Request, exc: ReportGenerationError):
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(code=5002, message=str(exc)).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """兜底：不暴露堆栈，记录完整日志。"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(code=5000, message="服务器内部错误，请稍后重试").model_dump(),
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
