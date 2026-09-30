"""E2E 脚本共用的服务地址解析

默认仍指向本地 8000 端口，但允许用环境变量覆盖，方便：
- 8000 被别的进程占用时换端口跑（E2E_PORT=8001）
- 指向远端/云托管环境做冒烟

用法：
    from _e2e_base import API_BASE, ROOT_BASE
"""

import os

PORT = os.environ.get("E2E_PORT", "8000")
HOST = os.environ.get("E2E_HOST", "127.0.0.1")

_scheme = os.environ.get("E2E_SCHEME", "http")
ROOT_BASE = os.environ.get("E2E_BASE", f"{_scheme}://{HOST}:{PORT}")
API_BASE = f"{ROOT_BASE.rstrip('/')}/api/v1"
