"""代理环境变量兼容性规整（httpx / langchain-openai）

## 为什么需要这个模块

部分 Windows 代理客户端（Clash 等）会把 IPv6 回环写成**方括号**形式：

    NO_PROXY=localhost,127.0.0.1,::1,[::1]

httpx 的 `URLPattern` 会把 `[::1]` 误当成 `host:port` 解析，抛出
`httpx.InvalidURL: Invalid port: ':1]'`。异常发生在**客户端构造阶段**，
所以任何走 httpx 的调用都会当场失败：

- `user_service.wx_code_to_openid()` 的 `httpx.AsyncClient(...)`
- `langchain_openai.ChatOpenAI(...)`（内部构造 httpx client）
  → 出题链 / 报告链全部不可用

这是纯粹的宿主环境差异，不该要求用户去改机器上的环境变量，因此在**代码层**
做一次幂等规整：把方括号 IPv6 还原成 httpx 认得的裸写法，并清掉空的代理条目。

## 安全性

- 只改写 `NO_PROXY` 条目里的方括号 IPv6；真实代理地址（`HTTP_PROXY` 等）原样保留，
  企业代理场景不受影响。
- 幂等：已规整过的值再次调用不会有任何变化。
- 不存在的变量不会被凭空创建。
"""

import os
import re

import structlog

logger = structlog.get_logger()

# 需要检查的代理相关环境变量（大小写两套：curl 用小写、httpx 两套都读）
PROXY_ENV_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)

# 方括号 IPv6：`[::1]` / `[2001:db8::1]`
_BRACKETED_IPV6 = re.compile(r"^\[([0-9A-Fa-f:.]*:[0-9A-Fa-f:.]*)\]$")


def _normalize_no_proxy(value: str) -> str:
    """`NO_PROXY` 值规整：方括号 IPv6 去括号 + 去空条目 + 去重（保序）。

    去重是因为 `::1,[::1]` 去括号后会变成重复条目；去重不改变匹配语义
    （同一主机重复列出的效果等同于列一次）。
    """
    entries: list[str] = []
    seen: set[str] = set()
    for raw in value.split(","):
        entry = raw.strip()
        if not entry:
            continue
        match = _BRACKETED_IPV6.match(entry)
        if match:
            entry = match.group(1)
        if entry in seen:
            continue
        seen.add(entry)
        entries.append(entry)
    return ",".join(entries)


def sanitize_proxy_env() -> None:
    """规整进程内的代理环境变量，使其对 httpx 可用。幂等，可重复调用。"""
    changed: list[str] = []

    for name in PROXY_ENV_VARS:
        raw = os.environ.get(name)
        if raw is None:
            continue

        # 空值（""/"  "）没有意义，且会让部分 HTTP 库把它解析成空规则，直接删除
        if not raw.strip():
            del os.environ[name]
            changed.append(name)
            continue

        if name.lower() != "no_proxy":
            continue

        normalized = _normalize_no_proxy(raw)
        if normalized != raw:
            if normalized:
                os.environ[name] = normalized
            else:
                del os.environ[name]
            changed.append(name)

    if changed:
        logger.info("proxy_env_sanitized", variables=sorted(set(changed)))
