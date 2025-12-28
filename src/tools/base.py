"""
工具基类模块

定义所有工具的抽象接口。
遵循章程：真实实现，不允许虚假实现或占位符
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolExecutionResult:
    """工具执行结果"""
    success: bool           # 是否成功
    output: str             # 输出内容
    error: str | None = None  # 错误信息
    duration: float = 0     # 执行时长

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration": self.duration
        }


class Tool(ABC):
    """工具基类"""

    name: str = "base_tool"
    description: str = "工具基类"
    timeout: int = 5  # 默认超时时间（秒）

    @abstractmethod
    def execute(self, **kwargs) -> ToolExecutionResult:
        """执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            ToolExecutionResult: 执行结果
        """
        pass

    def validate_args(self, **kwargs) -> tuple[bool, str]:
        """验证参数

        Args:
            **kwargs: 工具参数

        Returns:
            (是否有效, 错误消息)
        """
        return True, ""

    def _execute_with_timeout(self, func, *args, **kwargs) -> ToolExecutionResult:
        """带超时的执行工具

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            ToolExecutionResult: 执行结果
        """
        start_time = time.time()

        try:
            # 执行工具
            result = func(*args, **kwargs)

            duration = time.time() - start_time

            # 检查超时
            if duration > self.timeout:
                return ToolExecutionResult(
                    success=False,
                    output="",
                    error=f"工具执行超时（{duration:.2f}s > {self.timeout}s）",
                    duration=duration
                )

            return ToolExecutionResult(
                success=True,
                output=str(result),
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"工具执行失败: {str(e)}",
                duration=duration
            )
