"""MySQL 连接池与建表（用户系统，4 张表）

- 启动时自动 CREATE DATABASE + 建表（mysql_auto_init=true）；
- 连不上 MySQL 不阻断应用启动（可选登录：核心出题/报告仍可用）；
- DDL 全部使用 IF NOT EXISTS，重复启动时静默跳过（MySQL 仍会发出「已存在」
  Warning，属于无害噪音，在建表阶段统一屏蔽）；
- **会话时区显式设为本机本地偏移**，见 `mysql_time_zone_init_command`。
"""

import warnings
from contextlib import contextmanager
from datetime import datetime, tzinfo
from typing import Final, Iterator, Optional

import aiomysql
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()

_pool: Optional[aiomysql.Pool] = None


def mysql_time_zone_init_command(tz: Optional[tzinfo] = None) -> str:
    """生成把 MySQL 会话时区设为本机本地偏移的 `init_command`。

    为什么必须显式设置：
        各表的 `created_at` 由 `CURRENT_TIMESTAMP` 填充，取值取决于**服务器会话
        时区**；而应用侧所有时间范围过滤与聚合的"起点"都是 Python 的朴素
        `datetime.now()`（操作系统本地时区）。二者不一致时，"最近 7 天""本周
        闯关""连续打卡"会出现固定偏移，且**静默不报错**。

        此前只靠 MySQL 容器的 `-e TZ=Asia/Shanghai` 兜着；换台机器、或改用
        云数据库（通常为 UTC）就会退化成 8 小时偏移。这里把口径固定在连接层，
        行为不再依赖外部环境变量。

    MySQL 的 `SET time_zone` 只接受 `±HH:MM`（整分钟），因此秒级偏移（某些
    历史时区的 LMT）会显式抛 ValueError，而不是写出一条非法语句。
    """
    if tz is None:
        tz = datetime.now().astimezone().tzinfo
    offset = datetime.now(tz).utcoffset()
    if offset is None:
        raise ValueError(f"无法确定时区偏移：{tz!r}")

    total_seconds = offset.total_seconds()
    if total_seconds % 60 != 0:
        raise ValueError(
            f"时区偏移含秒级部分（{tz!r}），MySQL 的 SET time_zone 不接受：{offset}"
        )

    total_minutes = int(total_seconds // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    return f"SET time_zone='{sign}{total_minutes // 60:02d}:{total_minutes % 60:02d}'"


@contextmanager
def _silence_mysql_ddl_warnings() -> Iterator[None]:
    """DDL 阶段屏蔽 MySQL 的「已存在」警告（IF NOT EXISTS 的正常路径）。"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Warning)
        yield


SCHEMA_STATEMENTS: Final[list[str]] = [    """
    CREATE TABLE IF NOT EXISTS users (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        openid VARCHAR(64) NOT NULL,
        nickname VARCHAR(100) NOT NULL DEFAULT '学习者',
        avatar_url VARCHAR(500) NOT NULL DEFAULT '',
        total_xp INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uk_users_openid (openid)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS quiz_sessions (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        quiz_id VARCHAR(64) NOT NULL,
        user_id BIGINT UNSIGNED NULL,
        title VARCHAR(255) NOT NULL,
        summary TEXT NULL,
        user_input TEXT NULL,
        questions_json JSON NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uk_quiz_sessions_quiz_id (quiz_id),
        KEY idx_quiz_sessions_user_id (user_id),
        KEY idx_quiz_sessions_created_at (created_at),
        CONSTRAINT fk_quiz_sessions_user_id
            FOREIGN KEY (user_id) REFERENCES users (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS answer_records (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        quiz_id VARCHAR(64) NOT NULL,
        user_id BIGINT UNSIGNED NULL,
        records_json JSON NOT NULL,
        total_questions INT NOT NULL,
        correct_count INT NOT NULL,
        accuracy DECIMAL(5, 2) NOT NULL,
        total_duration_ms INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uk_answer_records_quiz_id (quiz_id),
        KEY idx_answer_records_user_id (user_id),
        KEY idx_answer_records_created_at (created_at),
        CONSTRAINT fk_answer_records_user_id
            FOREIGN KEY (user_id) REFERENCES users (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE,
        CONSTRAINT fk_answer_records_quiz_id
            FOREIGN KEY (quiz_id) REFERENCES quiz_sessions (quiz_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS reports (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        quiz_id VARCHAR(64) NOT NULL,
        user_id BIGINT UNSIGNED NULL,
        report_json JSON NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uk_reports_quiz_id (quiz_id),
        KEY idx_reports_user_id (user_id),
        KEY idx_reports_created_at (created_at),
        CONSTRAINT fk_reports_user_id
            FOREIGN KEY (user_id) REFERENCES users (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE,
        CONSTRAINT fk_reports_quiz_id
            FOREIGN KEY (quiz_id) REFERENCES quiz_sessions (quiz_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]


async def init_mysql() -> None:
    """建库（如不存在）+ 建连接池 + 建表。失败抛异常，由调用方决定是否阻断启动。"""
    global _pool

    if _pool is not None:
        return

    settings = get_settings()
    # 会话时区与本机对齐，保证 CURRENT_TIMESTAMP 与 datetime.now() 口径一致
    init_command = mysql_time_zone_init_command()

    bootstrap_conn = await aiomysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        charset=settings.mysql_charset,
        autocommit=True,
        init_command=init_command,
    )
    try:
        with _silence_mysql_ddl_warnings():
            async with bootstrap_conn.cursor() as cursor:
                await cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` "
                    f"CHARACTER SET {settings.mysql_charset} COLLATE utf8mb4_unicode_ci"
                )
    finally:
        bootstrap_conn.close()

    _pool = await aiomysql.create_pool(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        db=settings.mysql_database,
        charset=settings.mysql_charset,
        minsize=settings.mysql_pool_minsize,
        maxsize=settings.mysql_pool_maxsize,
        autocommit=True,
        init_command=init_command,
    )

    with _silence_mysql_ddl_warnings():
        async with _pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for statement in SCHEMA_STATEMENTS:
                    await cursor.execute(statement)

    logger.info("mysql_initialized", database=settings.mysql_database)


def get_mysql_pool() -> Optional[aiomysql.Pool]:
    return _pool


async def close_mysql_pool() -> None:
    global _pool

    if _pool is None:
        return

    _pool.close()
    await _pool.wait_closed()
    _pool = None
    logger.info("mysql_pool_closed")
