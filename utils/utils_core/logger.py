import logging
import os
import sys
from typing import Optional
from datetime import datetime
from pathlib import Path


def setup_logging(level: int = logging.INFO,
                  log_file: Optional[str] = None) -> None:
    """Setup logging configuration for the root logger.
    This function should be called once at application startup to configure global logging.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional log file path
    """
    root_logger = logging.getLogger()

    # 清除所有已存在的处理器，防止重复添加
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()  # 关闭处理器以释放资源

    # 确保日志目录存在
    if not log_file:
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = str(log_dir / f'testpilot_{timestamp}.log')
    else:
        # 确保日志文件目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Formatter统一
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File handler（使用线程安全的文件处理）
    try:
        # Windows 上使用追加模式，避免并发写入冲突
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
        file_handler.setLevel(logging.DEBUG)  # 文件日志通常设置为DEBUG，记录所有信息
        file_handler.setFormatter(formatter)
    except Exception as file_handler_error:
        # 如果文件处理器创建失败，记录到控制台并继续
        print(f"警告: 无法创建日志文件处理器: {file_handler_error}")
        file_handler = None

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)  # 控制台日志级别由参数控制
    console_handler.setFormatter(formatter)

    # 设置根日志记录器的级别，确保所有级别的消息都能被捕获并传递给处理器
    root_logger.setLevel(logging.DEBUG)

    # 添加处理器（仅在成功创建时添加）
    if file_handler is not None:
        root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def setup_logger(name: str) -> logging.Logger:
    """Create and configure a logger for a specific module.
    This logger will inherit its handlers from the root logger configured by setup_logging.

    Args:
        name: Logger name

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance for a specific module.
    This is an alias for setup_logger to maintain compatibility.

    Args:
        name: Logger name (default: None for root logger)

    Returns:
        logging.Logger: Configured logger instance
    """
    if name is None:
        return logging.getLogger()
    return logging.getLogger(name)


def _configure_console_utf8() -> None:
    """Windows 控制台默认 GBK，与 UTF-8 日志/IDE 终端混用时易乱码。"""
    if sys.platform != 'win32':
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, OSError, ValueError):
            pass


def init_logging():
    _configure_console_utf8()
    # 从环境变量获取日志级别
    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # 从环境变量获取日志文件路径
    log_file = os.getenv('LOG_FILE', None)

    # 设置日志
    setup_logging(level=log_level, log_file=log_file)

    # 禁用第三方库的日志
    logging.getLogger("chromadb.telemetry.product.posthog").disabled = True
    logging.getLogger("posthog").disabled = True
    logging.getLogger("chromadb.telemetry").disabled = True
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


# Export symbols
__all__ = ['setup_logging', 'setup_logger', 'get_logger', 'init_logging']