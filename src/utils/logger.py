"""
日志配置模块

提供统一的日志配置功能，支持中文日志。
遵循章程：文档与可追溯性、语言规范
"""

import logging
import os
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_file: str,
    level: str = "INFO",
    log_dir: str = "logs"
) -> logging.Logger:
    """
    设置并返回一个配置好的日志记录器

    Args:
        name: 日志记录器名称
        log_file: 日志文件名
        level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_dir: 日志目录

    Returns:
        配置好的日志记录器
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 文件处理器
    file_handler = logging.FileHandler(
        log_path / log_file,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 日志格式（中文支持）
    # 格式：[时间] [级别] [模块] 消息
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_server_logger(level: str = "INFO") -> logging.Logger:
    """获取服务器日志记录器"""
    return setup_logger("server", "server.log", level)


def get_client_logger(level: str = "INFO") -> logging.Logger:
    """获取客户端日志记录器"""
    return setup_logger("client", "client.log", level)


def get_network_logger(level: str = "DEBUG") -> logging.Logger:
    """获取网络协议日志记录器"""
    return setup_logger("network", "network.log", level)


def get_agent_logger(level: str = "INFO") -> logging.Logger:
    """获取 Agent 日志记录器"""
    return setup_logger("agent", "agent.log", level)
