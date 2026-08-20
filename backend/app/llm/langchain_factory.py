"""LangChain ChatOpenAI 工厂（langchain-openai 1.x）

通过 base_url 直连 DeepSeek 的 OpenAI 兼容接口（官方推荐接入方式）。
"""

from langchain_openai import ChatOpenAI

from app.core.config import get_settings


def get_chat_model(
    temperature: float = 0.4,
    top_p: float | None = None,
    timeout: float | None = None,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """构造指向 DeepSeek 的 ChatOpenAI 实例（不发起任何网络请求）。"""
    settings = get_settings()
    kwargs: dict = {
        "model": settings.deepseek_model,
        "base_url": settings.deepseek_base_url,
        "api_key": settings.deepseek_api_key,
        "temperature": temperature,
        "max_tokens": max_tokens if max_tokens is not None else settings.llm_max_tokens,
        "timeout": timeout if timeout is not None else settings.llm_timeout_seconds,
    }
    if top_p is not None:
        kwargs["top_p"] = top_p
    return ChatOpenAI(**kwargs)
