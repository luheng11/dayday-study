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

    # Log
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
