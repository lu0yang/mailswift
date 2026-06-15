"""
开发启动器：启动服务 + 自动打开浏览器。

生产环境直接用 app.py 启动即可。
"""

import threading
import webbrowser

import uvicorn


def main():
    host = "127.0.0.1"
    port = 8080

    # 后台启动 FastAPI
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(
            "backend.main:app",
            host=host,
            port=port,
            log_level="info",
        ),
        daemon=True,
    )
    server_thread.start()

    # 自动打开浏览器
    webbrowser.open(f"http://{host}:{port}")
    server_thread.join()


if __name__ == "__main__":
    main()
