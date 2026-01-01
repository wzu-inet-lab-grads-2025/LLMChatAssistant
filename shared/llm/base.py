"""
LLM Provider 抽象接口

定义统一的 LLM Provider 接口，支持多个提供商实现。
遵循章程：LLM Provider 扩展
"""

from abc import ABC, abstractmethod
from typing import List


class Message:
    """聊天消息"""
    def __init__(self, role: str, content: str):
        """
        Args:
            role: 角色（user, assistant, system）
            content: 消息内容
        """
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {"role": self.role, "content": self.content}


class LLMProvider(ABC):
    """
    LLM Provider 抽象接口

    所有 LLM Provider 必须实现此接口，确保可替换性和扩展性。
    """

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        model: str,
        stream: bool = False,
        **kwargs
    ) -> str:
        """
        聊天接口

        Args:
            messages: 消息列表
            model: 模型名称
            stream: 是否流式输出（默认 False）
            **kwargs: 其他参数（temperature, max_tokens 等）

        Returns:
            str: 完整的响应文本

        Raises:
            Exception: API 调用失败
        """
        pass

    @abstractmethod
    async def embed(self, texts: List[str], model: str) -> List[List[float]]:
        """
        向量嵌入接口

        Args:
            texts: 待嵌入的文本列表
            model: 嵌入模型名称

        Returns:
            List[List[float]]: 嵌入向量列表

        Raises:
            Exception: API 调用失败
        """
        pass

    @abstractmethod
    def validate_api_key(self) -> bool:
        """
        验证 API key 有效性

        Returns:
            bool: API key 是否有效
        """
        pass

    @abstractmethod
    def set_model(self, model: str) -> None:
        """
        设置当前使用的模型

        Args:
            model: 模型名称
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        获取可用的模型列表

        Returns:
            List[str]: 可用模型列表
        """
        pass
