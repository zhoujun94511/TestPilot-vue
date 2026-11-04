#!/usr/bin/env python3
"""
TestPilot 应用启动文件
支持开发和生产环境的启动配置
支持跨平台运行（Windows、Linux、Mac）
"""

import os
import sys
import socket
import threading
import subprocess
import time
from pathlib import Path
from utils.utils_core.logger import init_logging, get_logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
from app import (
    FRONTEND_DEV_PORT,
    create_app,
    register_shutdown_handlers,
    sync_frontend_env,
    start_frontend,
    stop_frontend,
)
from utils.utils_core.common_utils import get_local_ip, open_browser
from utils.utils_core.platform_utils import get_platform, get_wsgi_server


def _wait_for_tcp(host: str, port: int, timeout: float = 120.0) -> bool:
    """开发联调：等 Flask 开始监听后再起 Vite，避免代理 ECONNREFUSED。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def main():
    """主启动函数"""
    # 初始化日志系统
    init_logging()
    logger = get_logger(__name__)

    # 获取环境变量
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5001))

    lan_ip = get_local_ip()
    if debug:
        # 开发：Flask 监听所有接口，Vite 代理固定走 loopback（与 sync_frontend_env 一致）
        bind_host = '0.0.0.0'
        sync_frontend_env(bind_host, port, proxy_host='127.0.0.1')
        host = lan_ip or '127.0.0.1'
    else:
        host = lan_ip
        if not host:
            logger.warning("无法获取本地IP，使用0.0.0.0")
            host = '0.0.0.0'
        bind_host = host
        sync_frontend_env(host, port)
    register_shutdown_handlers()

    try:
        # 先完成 create_app（含 LLM/向量库等），再启 Vite，避免 5173 代理时 5001 尚未监听
        app = create_app()

        logger.info(f"启动TestPilot应用...")
        logger.info(f"平台: {get_platform()}")
        logger.info(f"环境: {'开发' if debug else '生产'}")
        ui_host = host if host != '0.0.0.0' else '127.0.0.1'
        logger.info(f"后端 API: http://127.0.0.1:{port} (bind {bind_host}:{port})")
        logger.info(
            "界面入口: http://%s:%s （Vite 热更新；改 frontend/src 后保存即生效）",
            ui_host,
            FRONTEND_DEV_PORT,
        )
        logger.info(
            "若使用 http://%s:%s 打开页面，看到的是 frontend/dist 构建结果，需 npm run build 后才会更新",
            host,
            port,
        )
        if not debug:
            logger.info("当前为非 DEBUG 模式，浏览器不会自动打开；日常开发请访问 Vite 端口")

        # 启动应用
        if debug:
            def _run_dev_server() -> None:
                app.run(
                    host=bind_host,
                    port=port,
                    debug=True,
                    threaded=True,
                    use_reloader=False,
                )

            server_thread = threading.Thread(target=_run_dev_server, daemon=True)
            server_thread.start()
            if not _wait_for_tcp("127.0.0.1", port):
                logger.error("Flask 未在 %ss 内监听 127.0.0.1:%s", 120, port)
                stop_frontend()
                sys.exit(1)

            start_frontend()

            # 开发环境打开 Vite，而非 Flask（Flask 仅提供 /api 与 dist 回退）
            if host != "0.0.0.0":
                browser_thread = threading.Thread(
                    target=open_browser,
                    args=(ui_host, FRONTEND_DEV_PORT),
                )
                browser_thread.daemon = True
                browser_thread.start()

            server_thread.join()
        else:
            # 生产环境使用平台特定的WSGI服务器
            wsgi_server = get_wsgi_server()
            logger.info(f"生产环境WSGI服务器: {wsgi_server}")

            if wsgi_server == "waitress":
                # Windows平台使用Waitress
                waitress_available = False
                try:
                    from waitress import serve
                    waitress_available = True
                except ImportError:
                    serve = None  # 定义为None以满足linter要求

                if waitress_available:
                    logger.info("使用Waitress服务器 (Windows)")
                    serve(
                        app,
                        host=host,
                        port=port,
                        threads=int(os.getenv('WORKERS', 4)),
                        channel_timeout=30,
                        cleanup_interval=30,
                        asyncore_use_poll=True
                    )
                else:
                    logger.warning("Waitress未安装，使用Flask内置服务器")
                    logger.info("提示: 运行 'pip install waitress' 安装Waitress")
                    app.run(
                        host=host,
                        port=port,
                        debug=False,
                        threaded=True
                    )
            else:
                # Linux/Mac平台使用Gunicorn
                gunicorn_available = subprocess.call(
                    [sys.executable, '-m', 'gunicorn', '--version'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                ) == 0

                if gunicorn_available:
                    logger.info("使用Gunicorn服务器 (Linux/Mac)")

                    # Gunicorn配置
                    # noinspection SpellCheckingInspection
                    gunicorn_config = {
                        'bind': f'{host}:{port}',
                        'workers': os.getenv('WORKERS', 4),
                        'worker_class': 'eventlet',
                        'worker_connections': 1000,
                        'timeout': 30,
                        'keepalive': 2,
                        'max_requests': 1000,
                        'max_requests_jitter': 100,
                        'preload_app': True,
                        'accesslog': 'logs/access.log',
                        'errorlog': 'logs/error.log',  # Gunicorn官方配置项名称
                        'loglevel': 'info'
                    }

                    # 设置环境变量给Gunicorn
                    for key, value in gunicorn_config.items():
                        os.environ[f'GUNICORN_{key.upper()}'] = str(value)

                    # 启动Gunicorn
                    sys.argv = ['gunicorn', 'app:create_app()']
                    os.execvp('gunicorn', sys.argv)
                else:
                    logger.warning("Gunicorn未安装，使用Flask内置服务器")
                    logger.info("提示: 运行 'pip install gunicorn' 安装Gunicorn")
                    app.run(
                        host=host,
                        port=port,
                        debug=False,
                        threaded=True
                    )

    except KeyboardInterrupt:
        logger.info("已取消启动")
        stop_frontend()
        sys.exit(0)
    except Exception as e:
        logger.error(f"启动应用失败: {str(e)}")
        stop_frontend()
        sys.exit(1)
    finally:
        stop_frontend()


if __name__ == '__main__':
    main()
