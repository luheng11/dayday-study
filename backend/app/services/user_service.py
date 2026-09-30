"""用户服务：微信登录（含开发降级）、档案查询与更新、头像持久化"""

import os
import uuid
from datetime import datetime, timedelta

import httpx
import structlog

from app.core.auth import create_token
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, BusinessError
from app.core.levels import get_level_info
from app.core.proxy_env import sanitize_proxy_env
from app.models.user import LoginResponse, UserBrief, UserProfile
from app.repositories import quiz_repository, user_repository

logger = structlog.get_logger()

WX_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"

# 头像上传限制
AVATAR_MAX_BYTES = 2 * 1024 * 1024  # 2MB
AVATAR_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
_AVATAR_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


async def wx_code_to_openid(code: str) -> str:
    """code → openid。

    - 开发降级（wechat_mock_login=true 或未配置凭据）：code 以 dev_ 开头时直接作为
      openid（便于本地模拟多用户），否则返回固定 dev_openid_default（wx code 每次不同，
      固定 openid 保证开发期每次登录都是同一用户）。
    - 配置真实凭据后：调用微信 jscode2session。
    """
    settings = get_settings()

    if not settings.wechat_app_id or not settings.wechat_app_secret:
        if settings.wechat_mock_login:
            # 开发降级：code 以 dev_ 开头时直接作为 openid（便于本地模拟多用户），
            # 否则返回固定 dev_openid_default（wx code 每次不同，固定 openid 保证
            # 开发期每次登录都是同一用户）。
            return code if code.startswith("dev_") else "dev_openid_default"
        raise AuthenticationError("微信登录未配置")

    try:
        # httpx 构造阶段就会读取 NO_PROXY，宿主的方括号 IPv6（[::1]）会让其抛
        # InvalidURL，因此调用前先做一次规整。
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                WX_CODE2SESSION_URL,
                params={
                    "appid": settings.wechat_app_id,
                    "secret": settings.wechat_app_secret,
                    "js_code": code,
                    "grant_type": "authorization_code",
                },
            )
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("wx_login_request_failed", error=str(exc))
        raise AuthenticationError("微信登录服务暂时不可用，请稍后重试") from exc
    except ValueError as exc:
        logger.error("wx_login_invalid_response", error=str(exc))
        raise AuthenticationError("微信登录失败，请重试") from exc

    if "openid" not in data:
        logger.warning(
            "wx_login_failed",
            errcode=data.get("errcode"),
            errmsg=data.get("errmsg"),
        )
        raise AuthenticationError("微信登录失败，请重试")

    return data["openid"]


async def handle_login(code: str) -> LoginResponse:
    """微信静默登录：code → openid → 查/建用户 → 签发 JWT。"""
    openid = await wx_code_to_openid(code)

    user = await user_repository.find_user_by_openid(openid)
    if user is None:
        user = await user_repository.create_user(openid)

    token = create_token(user_id=user["id"], openid=openid)

    return LoginResponse(
        token=token,
        user=UserBrief(
            id=user["id"],
            nickname=user["nickname"],
            avatar_url=user["avatar_url"],
            total_xp=user["total_xp"],
        ),
    )


def _week_start() -> datetime:
    """本周一 00:00（自然周口径，与原型「本周闯关」一致）。"""
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


async def get_profile(user_id: int) -> UserProfile:
    """用户档案：基础信息 + 累计统计 + 本周统计 + 连续学习 + 等级。"""
    user = await user_repository.get_user_by_id(user_id)
    if user is None:
        raise AuthenticationError("用户不存在")

    all_stats = await quiz_repository.get_user_answer_stats(user_id)
    week_stats = await quiz_repository.get_user_answer_stats(user_id, since=_week_start())
    dates = await quiz_repository.get_user_answer_dates(user_id)

    from app.services.history_service import compute_streak

    return UserProfile(
        id=user["id"],
        nickname=user["nickname"],
        avatar_url=user["avatar_url"],
        total_xp=user["total_xp"],
        quiz_count=all_stats["quiz_count"],
        correct_count=all_stats["correct_count"],
        average_accuracy=all_stats["average_accuracy"],
        week_quiz_count=week_stats["quiz_count"],
        streak_days=compute_streak(dates),
        level=get_level_info(user["total_xp"]),
    )


async def update_profile(user_id: int, nickname: str | None, avatar_url: str | None) -> None:
    """更新昵称/头像：昵称去空格后非空校验。"""
    if nickname is not None:
        nickname = nickname.strip()
        if not nickname:
            raise BusinessError("昵称不能为空")
    if nickname is None and avatar_url is None:
        return
    await user_repository.update_user_profile(user_id, nickname, avatar_url)


async def save_avatar(user_id: int, content: bytes, content_type: str) -> str:
    """保存头像文件到本地存储，返回相对 URL（/static/avatars/xxx）。

    - 校验类型（仅图片）与大小（≤2MB）；
    - 文件名按用户隔离，避免覆盖。
    """
    if content_type not in AVATAR_ALLOWED_TYPES:
        raise BusinessError("仅支持 png/jpg/webp/gif 图片头像")
    if len(content) > AVATAR_MAX_BYTES:
        raise BusinessError("头像图片不能超过 2MB")

    settings = get_settings()
    avatar_dir = os.path.join(settings.data_dir, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)

    filename = f"user_{user_id}_{uuid.uuid4().hex[:12]}{_AVATAR_EXT[content_type]}"
    with open(os.path.join(avatar_dir, filename), "wb") as f:
        f.write(content)

    return f"/static/avatars/{filename}"
