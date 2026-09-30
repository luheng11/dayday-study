"""JWT 鉴权：签发、解析、必选/可选鉴权依赖"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import structlog
from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

logger = structlog.get_logger()

ALGORITHM = "HS256"


def create_token(user_id: int, openid: str) -> str:
    """签发 JWT，载荷含 user_id / openid / exp。"""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"user_id": user_id, "openid": openid, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """解析 JWT，失败抛 AuthenticationError（4010）。"""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("登录已过期，请重新登录") from None
    except jwt.InvalidTokenError:
        raise AuthenticationError("无效的登录凭证") from None


def _extract_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def get_current_user(request: Request) -> int:
    """必选鉴权：返回 user_id；未登录/无效时抛 AuthenticationError。"""
    token = _extract_token(request)
    if not token:
        raise AuthenticationError("请先登录")
    payload = decode_token(token)
    return payload["user_id"]


async def get_optional_user(request: Request) -> Optional[int]:
    """可选鉴权：返回 user_id 或 None（不抛异常，未登录照常体验核心流程）。"""
    token = _extract_token(request)
    if not token:
        return None
    try:
        payload = decode_token(token)
        return payload["user_id"]
    except AuthenticationError:
        return None
