"""
智谱 AI Provider 实现

使用 zai-sdk 集成智谱 AI API。
遵循章程：真实集成
"""

import os
import logging
import time
from typing import List, AsyncIterator
from zai import ZaiClient
from .base import LLMProvider, Message
from .models import (
    DEFAULT_CHAT_MODEL,
    AVAILABLE_MODELS,
    EMBED_MODEL,
    MODEL_CONFIGS
)
from shared.utils.logger import (
    get_llm_logger,
    log_llm_request,
    log_llm_response,
    log_llm_stream_start,
    log_llm_stream_chunk,
    log_llm_stream_end,
    log_llm_error,
    log_embedding_request,
    log_embedding_response
)

logger = logging.getLogger(__name__)
llm_logger = get_llm_logger()


class ZhipuProvider(LLMProvider):
    """
    智谱 AI Provider 实现

    提供聊天和嵌入功能，支持模型切换。
    """

    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化智谱 Provider

        Args:
            api_key: 智谱 API key（如果为 None，从环境变量读取）
            model: 默认聊天模型（如果为 None，使用 DEFAULT_CHAT_MODEL）
        """
        self.api_key = api_key or os.getenv('ZHIPU_API_KEY', '')
        if not self.api_key:
            raise ValueError("ZHIPU_API_KEY 未配置")

        self.client = ZaiClient(api_key=self.api_key)
        self.current_model = model or DEFAULT_CHAT_MODEL

        if self.current_model not in AVAILABLE_MODELS:
            raise ValueError(
                f"不支持的模型：{self.current_model}，"
                f"可用模型：{AVAILABLE_MODELS}"
            )

    async def chat(
        self,
        messages: List[Message],
        model: str = None,
        stream: bool = False,
        **kwargs
    ) -> str:
        """
        聊天接口

        Args:
            messages: 消息列表
            model: 模型名称（如果为 None，使用 current_model）
            stream: 是否流式输出（默认 False）
            **kwargs: 其他参数

        Returns:
            str: 完整的响应文本

        Raises:
            Exception: API 调用失败
        """
        model = model or self.current_model
        model_config = MODEL_CONFIGS.get(model, {})
        temperature = kwargs.get('temperature', model_config.get('temperature', 0.7))
        max_tokens = kwargs.get('max_tokens', model_config.get('max_tokens', 2000))

        # 转换消息格式
        api_messages = [msg.to_dict() for msg in messages]

        # 记录请求
        log_llm_request(llm_logger, model, messages, temperature=temperature, max_tokens=max_tokens)

        start_time = time.time()

        try:
            # 使用非流式输出（简化调用）
            response = self.client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            content = response.choices[0].message.content

            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000

            # 记录响应
            log_llm_response(llm_logger, model, content, duration_ms)

            return content

        except Exception as e:
            # 记录错误
            log_llm_error(
                llm_logger,
                e,
                context={
                    'model': model,
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'message_count': len(messages)
                }
            )
            raise Exception(f"智谱 API 调用失败：{str(e)}")

    async def chat_stream(
        self,
        messages: List[Message],
        model: str = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        聊天接口（流式输出）

        Args:
            messages: 消息列表
            model: 模型名称（如果为 None，使用 current_model）
            **kwargs: 其他参数

        Yields:
            str: 流式输出的文本片段

        Raises:
            Exception: API 调用失败
        """
        model = model or self.current_model
        model_config = MODEL_CONFIGS.get(model, {})
        temperature = kwargs.get('temperature', model_config.get('temperature', 0.7))
        max_tokens = kwargs.get('max_tokens', model_config.get('max_tokens', 2000))

        # 转换消息格式
        api_messages = [msg.to_dict() for msg in messages]

        # 记录请求
        log_llm_request(llm_logger, model, messages, temperature=temperature, max_tokens=max_tokens)

        start_time = time.time()
        total_chars = 0

        try:
            # 流式输出
            response = self.client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            # 记录流式开始
            log_llm_stream_start(llm_logger, model)

            # 流式响应是同步迭代器
            finish_reason = None
            for chunk in response:
                if chunk.choices:
                    choice = chunk.choices[0]
                    # 检查finish_reason
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason

                    if choice.delta.content:
                        content = choice.delta.content
                        total_chars += len(content)

                        # 记录数据块（DEBUG级别，可能导致日志过多）
                        log_llm_stream_chunk(llm_logger, len(content), total_chars)

                        # 在异步生成器中 yield
                        yield content

            # 计算总耗时
            duration_ms = (time.time() - start_time) * 1000

            # 记录流式结束
            log_llm_stream_end(llm_logger, model, total_chars, duration_ms, finish_reason or "unknown")

        except Exception as e:
            # 记录错误
            log_llm_error(
                llm_logger,
                e,
                context={
                    'model': model,
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'message_count': len(messages)
                }
            )
            raise Exception(f"智谱 API 调用失败：{str(e)}")

    async def embed(self, texts: List[str], model: str = None) -> List[List[float]]:
        """
        向量嵌入接口

        Args:
            texts: 待嵌入的文本列表
            model: 嵌入模型名称（如果为 None，使用 EMBED_MODEL）

        Returns:
            List[List[float]]: 嵌入向量列表

        Raises:
            Exception: API 调用失败
        """
        model = model or EMBED_MODEL

        # 记录请求
        log_embedding_request(llm_logger, model, texts)

        start_time = time.time()

        try:
            # embeddings.create 不需要 await（同步调用）
            response = self.client.embeddings.create(
                model=model,
                input=texts
            )

            # 提取向量
            embeddings = [item.embedding for item in response.data]

            # 计算耗时和维度
            duration_ms = (time.time() - start_time) * 1000
            embedding_dim = len(embeddings[0]) if embeddings else 0

            # 记录响应
            log_embedding_response(llm_logger, embedding_dim, duration_ms)

            return embeddings

        except Exception as e:
            # 记录错误
            log_llm_error(
                llm_logger,
                e,
                context={
                    'model': model,
                    'text_count': len(texts)
                }
            )
            raise Exception(f"智谱 Embedding API 调用失败：{str(e)}")

    def validate_api_key(self) -> bool:
        """
        验证 API key 有效性

        通过尝试调用简单 API 来验证

        Returns:
            bool: API key 是否有效
        """
        try:
            # 尝试调用嵌入 API（轻量级验证）
            import asyncio
            asyncio.run(self.embed(["测试"], EMBED_MODEL))
            return True
        except Exception:
            return False

    def set_model(self, model: str) -> None:
        """
        设置当前使用的模型

        Args:
            model: 模型名称

        Raises:
            ValueError: 如果模型不在可用列表中
        """
        if model not in AVAILABLE_MODELS:
            raise ValueError(
                f"不支持的模型：{model}，"
                f"可用模型：{AVAILABLE_MODELS}"
            )

        old_model = self.current_model
        self.current_model = model

        # 记录模型切换
        llm_logger.info(f"模型切换")
        llm_logger.info(f"  从: {old_model}")
        llm_logger.info(f"  到: {model}")

    def get_available_models(self) -> List[str]:
        """
        获取可用的模型列表

        Returns:
            List[str]: 可用模型列表
        """
        return AVAILABLE_MODELS.copy()
