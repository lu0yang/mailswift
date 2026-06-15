"""
数据库连接配置。

优先从环境变量读取，未设置时使用默认值。
支持 .env 文件（本地开发用）。
"""

import os
import logging

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

logger = logging.getLogger(__name__)

# ── MySQL 连接参数 ──────────────────────────────────────────

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "mailswift")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?charset=utf8mb4"
)

# 不指定数据库的 URL，用于建库操作
_SERVER_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/"
    f"?charset=utf8mb4"
)


def ensure_database_exists():
    """如果目标数据库不存在则自动创建。"""
    tmp_engine = create_engine(_SERVER_URL, echo=False)
    try:
        with tmp_engine.connect() as conn:
            conn.exec_driver_sql(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        logger.info("数据库 '%s' 已就绪", DB_NAME)
    finally:
        tmp_engine.dispose()
