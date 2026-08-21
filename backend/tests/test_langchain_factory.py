"""LangChain 模型工厂测试（TDD：重试与超时参数）"""

from app.llm.langchain_factory import get_chat_model


class TestGetChatModel:
    def test_no_sdk_internal_retries(self):
        """SDK 内部重试关闭（默认 2 次会与我们自己的兜底循环叠加放大耗时）"""
        model = get_chat_model()
        assert model.max_retries == 0

    def test_custom_params(self):
        model = get_chat_model(temperature=0.3, top_p=0.8, timeout=20.0, max_tokens=2048)
        assert model.temperature == 0.3
        assert model.top_p == 0.8
        # langchain-openai 1.x 中 timeout 存于私有字段 request_timeout
        assert model.request_timeout == 20.0
        assert model.max_tokens == 2048

    def test_defaults_from_settings(self):
        from app.core.config import get_settings

        settings = get_settings()
        model = get_chat_model()
        assert model.model_name == settings.deepseek_model
        assert model.openai_api_base == settings.deepseek_base_url
        assert model.openai_api_key.get_secret_value() == settings.deepseek_api_key
