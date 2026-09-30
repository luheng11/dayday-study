"""LangChain ChatOpenAI 工厂（langchain-openai 1.x）

通过 base_url 直连 DeepSeek 的 OpenAI 兼容接口（官方推荐接入方式）。
"""

from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.core.proxy_env import sanitize_proxy_env


def get_chat_model(
    temperature: float = 0.4,
    top_p: float | None = None,
    timeout: float | None = None,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """构造指向 DeepSeek 的 ChatOpenAI 实例（不发起任何网络请求）。"""
    settings = get_settings()
    # ChatOpenAI 构造时会内部创建 httpx client，先规整代理环境变量，
    # 避免宿主 NO_PROXY 里的方括号 IPv6（如 [::1]）导致 InvalidURL。
    sanitize_proxy_env()
    kwargs: dict = {
        "model": settings.deepseek_model,
        "base_url": settings.deepseek_base_url,
        "api_key": settings.deepseek_api_key,
        "temperature": temperature,
        "max_tokens": max_tokens if max_tokens is not None else settings.llm_max_tokens,
        "timeout": timeout if timeout is not None else settings.llm_timeout_seconds,
        # 关闭 SDK 内部重试（openai 默认 2 次会与我们自己的兜底循环叠加放大耗时）
        "max_retries": 0,
    }
    if top_p is not None:
        kwargs["top_p"] = top_p
    return ChatOpenAI(**kwargs)
