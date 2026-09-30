"""代理环境变量兼容性测试（TDD）

背景：部分 Windows 代理客户端会把 IPv6 回环写成方括号形式
（`NO_PROXY=localhost,127.0.0.1,::1,[::1]`）。httpx 0.28 / httpx2 2.x 的
`URLPattern` 把 `[::1]` 误当 host:port 解析，抛出
`InvalidURL: Invalid port: ':1]'`，导致**任何** httpx 客户端构造失败
（连带 langchain-openai 的 ChatOpenAI 也无法实例化）。

这里断言 sanitize_proxy_env 能把这类值规整成 httpx 可解析的形式，
从而在不要求用户改机器环境变量的前提下消除该故障。
"""

import os

import httpx

from app.core.proxy_env import sanitize_proxy_env

PROXY_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)

MALFORMED_NO_PROXY = "localhost,127.0.0.1,::1,[::1]"


def _clear_proxy_env(monkeypatch) -> None:
    for name in PROXY_VARS:
        monkeypatch.delenv(name, raising=False)


class TestNormalizeNoProxy:
    def test_bracketed_ipv6_is_unbracketed(self, monkeypatch):
        """[::1] → ::1；去括号后与已有的 ::1 重复，需去重（保序）。"""
        _clear_proxy_env(monkeypatch)
        monkeypatch.setenv("NO_PROXY", MALFORMED_NO_PROXY)

        sanitize_proxy_env()

        assert os.environ["NO_PROXY"] == "localhost,127.0.0.1,::1"

    def test_duplicate_entries_deduped_keeping_order(self, monkeypatch):
        """重复条目去重且保持首次出现顺序（不改变匹配语义）。"""
        _clear_proxy_env(monkeypatch)
        monkeypatch.setenv("NO_PROXY", "b.internal,a.internal,b.internal,a.internal")

        sanitize_proxy_env()

        assert os.environ["NO_PROXY"] == "b.internal,a.internal"

    def test_bracketed_ipv6_only_entry(self, monkeypatch):
        """整串只有一个方括号条目时也不会退化成空串。"""
        _clear_proxy_env(monkeypatch)
        monkeypatch.setenv("no_proxy", "[2001:db8::1]")

        sanitize_proxy_env()

        assert os.environ["no_proxy"] == "2001:db8::1"

    def test_valid_entries_untouched(self, monkeypatch):
        """本来就合法的值不做任何改写（幂等）。"""
        _clear_proxy_env(monkeypatch)
        monkeypatch.setenv("NO_PROXY", "localhost,127.0.0.1,*.internal,::1")

        sanitize_proxy_env()

        assert os.environ["NO_PROXY"] == "localhost,127.0.0.1,*.internal,::1"

    def test_whitespace_and_empty_entries_dropped(self, monkeypatch):
        """空条目 / 多余空格被清理，不改变语义。"""
        _clear_proxy_env(monkeypatch)
        monkeypatch.setenv("NO_PROXY", " localhost , , 127.0.0.1 ")

        sanitize_proxy_env()

        assert os.environ["NO_PROXY"] == "localhost,127.0.0.1"

    def test_empty_no_proxy_is_removed(self, monkeypatch):
        """空白 NO_PROXY 直接删除（空串会让部分 HTTP 库把规则解析成空条目）。"""
        _clear_proxy_env(monkeypatch)
        monkeypatch.setenv("NO_PROXY", "   ")

        sanitize_proxy_env()

        assert "NO_PROXY" not in os.environ


class TestNormalizeProxyVars:
    def test_empty_proxy_vars_are_removed(self, monkeypatch):
        """HTTP_PROXY="" 这类空值没有意义且干扰库的判定，应删除。"""
        _clear_proxy_env(monkeypatch)
        monkeypatch.setenv("HTTP_PROXY", "")
        monkeypatch.setenv("http_proxy", "")
        monkeypatch.setenv("HTTPS_PROXY", "   ")

        sanitize_proxy_env()

        assert "HTTP_PROXY" not in os.environ
        assert "http_proxy" not in os.environ
        assert "HTTPS_PROXY" not in os.environ

    def test_real_proxy_values_preserved(self, monkeypatch):
        """真实代理配置必须原样保留（企业代理场景不能被破坏）。"""
        _clear_proxy_env(monkeypatch)
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:7897")
        monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7897")

        sanitize_proxy_env()

        assert os.environ["HTTP_PROXY"] == "http://127.0.0.1:7897"
        assert os.environ["HTTPS_PROXY"] == "http://127.0.0.1:7897"

    def test_missing_vars_are_not_created(self, monkeypatch):
        """不存在的变量不应被凭空创建。"""
        _clear_proxy_env(monkeypatch)

        sanitize_proxy_env()

        assert all(name not in os.environ for name in PROXY_VARS)


class TestHttpxClientConstruction:
    """回归防线：规整之后 httpx 同步/异步客户端必须能构造出来。"""

    def test_malformed_no_proxy_alone_breaks_httpx(self, monkeypatch):
        """先固化故障现象：未规整时 httpx 确实无法构造（防上游修复后测试失真）。"""
        _clear_proxy_env(monkeypatch)
        monkeypatch.setenv("NO_PROXY", MALFORMED_NO_PROXY)

        import pytest

        with pytest.raises(httpx.InvalidURL):
            httpx.Client()

    def test_sync_client_constructs_after_sanitize(self, monkeypatch):
        _clear_proxy_env(monkeypatch)
        monkeypatch.setenv("NO_PROXY", MALFORMED_NO_PROXY)

        sanitize_proxy_env()
        with httpx.Client() as client:
            assert client is not None

    async def test_async_client_constructs_after_sanitize(self, monkeypatch):
        _clear_proxy_env(monkeypatch)
        monkeypatch.setenv("NO_PROXY", MALFORMED_NO_PROXY)

        sanitize_proxy_env()
        async with httpx.AsyncClient(timeout=10) as client:
            assert client is not None
