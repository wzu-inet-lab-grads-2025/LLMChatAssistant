"""
智谱 AI Provider 实现

使用 zai-sdk 集成智谱 AI API。
遵循章程：真实集成
"""

import os
from typing import List, AsyncIterator
from zai import ZaiClient
from .base import LLMProvider, Message
from .models import (
    DEFAULT_CHAT_MODEL,
    AVAILABLE_MODELS,
    EMBED_MODEL,
    MODEL_CONFIGS
)


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

        try:
            # 使用非流式输出（简化调用）
            response = self.client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            return response.choices[0].message.content

        except Exception as e:
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

        try:
            # 流式输出
            response = self.client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            # 流式响应是同步迭代器
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    # 在异步生成器中 yield
                    yield chunk.choices[0].delta.content

        except Exception as e:
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

        try:
            # embeddings.create 不需要 await（同步调用）
            response = self.client.embeddings.create(
                model=model,
                input=texts
            )

            # 提取向量
            embeddings = [item.embedding for item in response.data]
            return embeddings

        except Exception as e:
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
        self.current_model = model

    def get_available_models(self) -> List[str]:
        """
        获取可用的模型列表

        Returns:
            List[str]: 可用模型列表
        """
        return AVAILABLE_MODELS.copy()
