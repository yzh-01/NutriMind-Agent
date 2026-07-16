"""
日志配置模块
- 统一日志格式
- 文件处理器：按大小轮转（10MB），保留5个备份
- 控制台处理器：开发环境输出到终端
- 日志级别：DEBUG/INFO/WARNING/ERROR/CRITICAL
"""
import os
import logging
from logging.handlers import RotatingFileHandler

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str = "nutrimind-agent", level: int = logging.INFO) -> logging.Logger:
    """
    配置并返回日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别（默认 INFO）

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 创建格式化器
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 文件处理器 - 按大小轮转（10MB），保留5个备份
    log_file = os.path.join(LOG_DIR, f"{name}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 创建全局日志记录器
logger = setup_logger()


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器实例
    """
    return logging.getLogger(f"visagent.{name}")
