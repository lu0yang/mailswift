"""
MailSwift - Web application entry point.

启动 FastAPI 服务（含前端静态文件服务）。
可通过环境变量 API_HOST / API_PORT 配置监听地址。
"""

import os
import sys
import logging
from pathlib import Path

import uvicorn

from backend.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 路径解析（兼容 PyInstaller 打包）
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8080"))


def main():
    logger.info("MailSwift 服务启动中...")

    # 初始化数据库（自动建库 + 建表 + 迁移）
    init_db()
    logger.info("数据库初始化完成")

    # 启动 HTTP 服务（FastAPI 内置前端静态文件服务）
    logger.info("监听: http://%s:%s", API_HOST, API_PORT)
    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
