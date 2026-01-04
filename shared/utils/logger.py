"""
日志配置模块

提供统一的日志配置功能，支持中文日志。
遵循章程：文档与可追溯性、语言规范
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def setup_logger(
    name: str,
    log_file: str,
    level: str = "INFO",
    log_dir: str = "logs"
) -> logging.Logger:
    """
    设置并返回一个配置好的日志记录器

    注意：此函数只创建文件处理器，不添加控制台处理器，
    避免日志输出破坏 CLI UI 的显示。

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

    # 日志格式（中文支持）
    # 格式：[时间] [级别] [模块] 消息
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)

    # 只添加文件处理器，不添加控制台处理器
    # 这样日志只会写入文件，不会破坏 CLI UI 显示
    logger.addHandler(file_handler)

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


def get_llm_logger(level: str = "INFO") -> logging.Logger:
    """获取 LLM 日志记录器"""
    return setup_logger("llm", "llm.log", level)


def get_ui_logger(level: str = "INFO") -> logging.Logger:
    """获取 UI 交互日志记录器"""
    return setup_logger("client.ui", "ui.log", level)


def get_rdt_logger(level: str = "INFO") -> logging.Logger:
    """获取 RDT 协议日志记录器"""
    return setup_logger("rdt", "rdt.log", level)


# ============================================================================
# LLM 日志工具函数
# ============================================================================

def _format_message_summary(messages: List[Any], max_length: int = 100) -> str:
    """
    格式化消息列表为摘要

    Args:
        messages: 消息列表
        max_length: 每条消息最大长度

    Returns:
        格式化的摘要字符串
    """
    if not messages:
        return "[]"

    summary_lines = []
    for msg in messages:
        # 提取 role 和 content
        role = getattr(msg, 'role', 'unknown')
        content = getattr(msg, 'content', '')

        # 截断内容
        content_short = content[:max_length] + "..." if len(content) > max_length else content
        summary_lines.append(f"  - {role}: {content_short}")

    return "\n".join(summary_lines) if summary_lines else "[]"


def log_llm_request(
    logger: logging.Logger,
    model: str,
    messages: List[Any],
    **kwargs
) -> None:
    """
    记录 LLM 请求

    Args:
        logger: 日志记录器
        model: 模型名称
        messages: 消息列表
        **kwargs: 其他参数（temperature, max_tokens 等）
    """
    logger.info("LLM 请求开始")
    logger.info(f"  模型: {model}")

    # 记录关键参数
    if 'temperature' in kwargs:
        logger.info(f"  Temperature: {kwargs['temperature']}")
    if 'max_tokens' in kwargs:
        logger.info(f"  Max Tokens: {kwargs['max_tokens']}")

    # 记录消息摘要
    logger.info(f"  消息数: {len(messages)}")
    logger.info(f"  消息摘要:\n{_format_message_summary(messages)}")


def log_llm_response(
    logger: logging.Logger,
    model: str,
    response: str,
    duration_ms: float,
    **metadata
) -> None:
    """
    记录 LLM 响应

    Args:
        logger: 日志记录器
        model: 模型名称
        response: 响应内容
        duration_ms: 调用耗时（毫秒）
        **metadata: 其他元数据（token 使用情况等）
    """
    logger.info("LLM 响应接收")
    logger.info(f"  模型: {model}")
    logger.info(f"  耗时: {duration_ms:.0f}ms")
    logger.info(f"  响应长度: {len(response)} 字符")

    # 记录响应摘要
    response_summary = response[:200] + "..." if len(response) > 200 else response
    logger.info(f"  响应摘要: {response_summary}")

    # 记录元数据（token 使用情况等）
    if metadata:
        if 'prompt_tokens' in metadata and 'completion_tokens' in metadata:
            total_tokens = metadata['prompt_tokens'] + metadata['completion_tokens']
            logger.info(f"  Token 使用: prompt_tokens={metadata['prompt_tokens']}, "
                       f"completion_tokens={metadata['completion_tokens']}, total={total_tokens}")


def log_llm_stream_start(logger: logging.Logger, model: str) -> None:
    """
    记录流式输出开始

    Args:
        logger: 日志记录器
        model: 模型名称
    """
    logger.info("流式输出开始")
    logger.info(f"  模型: {model}")


def log_llm_stream_chunk(
    logger: logging.Logger,
    chunk_size: int,
    accumulated_chars: int
) -> None:
    """
    记录流式输出数据块

    Args:
        logger: 日志记录器
        chunk_size: 数据块大小
        accumulated_chars: 累计字符数
    """
    logger.debug(f"流式数据块")
    logger.debug(f"  块大小: {chunk_size} 字符")
    logger.debug(f"  累计: {accumulated_chars} 字符")


def log_llm_stream_end(
    logger: logging.Logger,
    model: str,
    total_chars: int,
    duration_ms: float,
    finish_reason: str
) -> None:
    """
    记录流式输出结束

    Args:
        logger: 日志记录器
        model: 模型名称
        total_chars: 总字符数
        duration_ms: 总耗时（毫秒）
        finish_reason: 完成原因
    """
    logger.info("流式输出结束")
    logger.info(f"  模型: {model}")
    logger.info(f"  总字符数: {total_chars}")
    logger.info(f"  总耗时: {duration_ms:.0f}ms")
    if duration_ms > 0:
        speed = (total_chars / duration_ms) * 1000  # 字符/秒
        logger.info(f"  平均速度: {speed:.0f} 字符/秒")
    logger.info(f"  完成原因: {finish_reason}")


def log_llm_error(
    logger: logging.Logger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    记录 LLM API 错误

    Args:
        logger: 日志记录器
        error: 异常对象
        context: 错误上下文（模型、参数等）
    """
    logger.error("LLM API 调用失败")
    logger.error(f"  异常类型: {type(error).__name__}")
    logger.error(f"  错误消息: {str(error)}")

    # 记录上下文
    if context:
        context_parts = []
        for key, value in context.items():
            if key == 'messages':
                context_parts.append(f"message_count={len(value)}")
            elif key == 'temperature':
                context_parts.append(f"{key}={value}")
            elif key == 'max_tokens':
                context_parts.append(f"{key}={value}")
            else:
                context_parts.append(f"{key}={value}")

        if context_parts:
            logger.error(f"  请求参数: {', '.join(context_parts)}")

    # 记录堆栈信息（仅非预期错误）
    if not isinstance(error, (ConnectionError, TimeoutError)):
        import traceback
        logger.error(f"  堆栈: {traceback.format_exc()}")


def log_embedding_request(
    logger: logging.Logger,
    model: str,
    texts: List[str]
) -> None:
    """
    记录 Embedding 请求

    Args:
        logger: 日志记录器
        model: 模型名称
        texts: 待嵌入的文本列表
    """
    text_lengths = [len(text) for text in texts]
    logger.info("Embedding 请求")
    logger.info(f"  模型: {model}")
    logger.info(f"  文本数: {len(texts)}")
    if text_lengths:
        logger.info(f"  长度范围: 最小={min(text_lengths)}, 最大={max(text_lengths)}, "
                   f"平均={sum(text_lengths) // len(text_lengths)}")


def log_embedding_response(
    logger: logging.Logger,
    embedding_dim: int,
    duration_ms: float
) -> None:
    """
    记录 Embedding 响应

    Args:
        logger: 日志记录器
        embedding_dim: 向量维度
        duration_ms: 调用耗时（毫秒）
    """
    logger.info(f"  向量维度: {embedding_dim}")
    logger.info(f"  耗时: {duration_ms:.0f}ms")
