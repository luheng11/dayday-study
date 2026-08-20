"""业务异常定义（统一错误码映射见 main.py 异常处理器）"""


class AppError(Exception):
    """业务异常基类"""


class ContentFilterError(AppError):
    """输入内容未通过安全过滤（错误码 4000）"""


class BusinessError(AppError):
    """业务参数错误（错误码 4001）"""


class QuizIntegrityError(AppError):
    """题库结构不完整/不合法（内部校验失败，触发重试或报错）"""


class QuizGenerationError(AppError):
    """题库生成失败（错误码 5001）"""


class ReportGenerationError(AppError):
    """报告生成失败（错误码 5002）"""


class ReportIntegrityError(AppError):
    """报告结构不完整/不合法（内部校验失败，触发重试或报错）"""


class TaskNotFoundError(AppError):
    """异步任务不存在（错误码 4002）"""
