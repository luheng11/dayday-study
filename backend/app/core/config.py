"""闯关学堂 · 后端配置"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DeepSeek（出题/报告大模型）
    deepseek_api_key: str = "sk-xxx"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    # 出题/报告参数（方案设计 4.3）
    quiz_temperature: float = 0.4
    quiz_top_p: float = 0.9
    report_temperature: float = 0.5
    report_top_p: float = 0.9
    llm_timeout_seconds: float = 30.0
    llm_max_tokens: int = 4096
    llm_max_attempts: int = 3  # 1 次主调用 + 2 次重试（出题走异步轮询，可放宽）
    # 报告为同步接口，受小程序 60s 请求超时约束：
    # 单次 20s × 2 次尝试，最坏 40s，保证不会触发前端超时
    llm_report_timeout_seconds: float = 20.0
    llm_report_max_attempts: int = 2

    # Mock 模式：无 DeepSeek Key 时用内置题库演示完整闭环（联调/验收用）
    llm_mock: bool = False

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = True

    # JWT（用户系统）
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 43200  # 30 天

    # 微信小程序（登录）
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    # 开发降级：true 或未配置 AppID/Secret 时，登录接口用固定开发 openid（本地联调）
    wechat_mock_login: bool = True

    # MySQL（用户系统，可选登录：连不上时核心出题/报告仍可用）
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "123456"
    mysql_database: str = "chuangguan_xuetang"
    mysql_charset: str = "utf8mb4"
    mysql_pool_minsize: int = 1
    mysql_pool_maxsize: int = 10
    mysql_auto_init: bool = True

    # 本地文件存储（头像等），生产多实例部署需换对象存储（Phase 10）
    data_dir: str = "./data"

    # Log
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
