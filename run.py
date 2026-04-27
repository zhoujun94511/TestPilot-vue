#!/usr/bin/env python3
"""
TestPilot 应用启动文件
支持开发和生产环境的启动配置
支持跨平台运行（Windows、Linux、Mac）
"""

import os
import sys
import threading
import subprocess
from pathlib import Path
from utils.utils_core.logger import init_logging, get_logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
from app import create_app, sync_frontend_env, start_frontend
from utils.utils_core.common_utils import get_local_ip, open_browser
from utils.utils_core.platform_utils import get_platform, get_wsgi_server

def main():
    """主启动函数"""
    # 初始化日志系统
    init_logging()
    logger = get_logger(__name__)

    # 获取环境变量
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5001))

    # 获取本地IP地址
    host = get_local_ip()
    if not host:
        logger.warning("无法获取本地IP，使用0.0.0.0")
        host = '0.0.0.0'
    sync_frontend_env(host, port)
    start_frontend()

    try:
        # 创建Flask应用
        app = create_app()

        logger.info(f"启动TestPilot应用...")
        logger.info(f"平台: {get_platform()}")
        logger.info(f"环境: {'开发' if debug else '生产'}")
        logger.info(f"地址: http://{host}:{port}")

        # 在开发环境下自动打开浏览器
        if debug and host != '0.0.0.0':
            browser_thread = threading.Thread(
                target=open_browser,
                args=(host, port)
            )
            browser_thread.daemon = True
            browser_thread.start()

        # 启动应用
        if debug:
            # 开发环境
            app.run(
                host=host,
                port=port,
                debug=True,
                threaded=True,
                use_reloader=False
            )
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

    except Exception as e:
        logger.error(f"启动应用失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
