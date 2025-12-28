"""
命令执行工具模块

提供安全的命令执行功能，仅支持白名单命令。
遵循章程：安全加固，命令黑名单字符过滤
"""

import subprocess
from dataclasses import dataclass
from typing import List

from .base import Tool, ToolExecutionResult


# 白名单命令
WHITELIST_COMMANDS = [
    'ls',
    'cat',
    'grep',
    'head',
    'tail',
    'ps',
    'pwd',
    'whoami',
    'df',
    'free'
]

# 黑名单字符（用于参数验证）
BLACKLIST_CHARS = [';', '&', '|', '>', '<', '`', '$', '(', ')', '\n', '\r']


@dataclass
class CommandTool(Tool):
    """命令执行工具"""

    name: str = "command_executor"
    description: str = "执行安全的系统命令（仅白名单命令）"
    timeout: int = 5

    def validate_args(self, command: str, args: List[str] = None) -> tuple[bool, str]:
        """验证命令和参数

        Args:
            command: 命令名称
            args: 参数列表

        Returns:
            (是否有效, 错误消息)
        """
        # 检查命令是否在白名单中
        if command not in WHITELIST_COMMANDS:
            return False, f"命令不在白名单中: {command}"

        # 检查参数中是否包含黑名单字符
        if args:
            for arg in args:
                for char in BLACKLIST_CHARS:
                    if char in arg:
                        return False, f"参数包含非法字符 '{char}': {arg}"

        return True, ""

    def execute(self, command: str, args: List[str] = None, **kwargs) -> ToolExecutionResult:
        """执行命令

        Args:
            command: 命令名称（如 'ls', 'cat'）
            args: 参数列表（如 ['-la', '/home']）
            **kwargs: 其他参数

        Returns:
            ToolExecutionResult: 执行结果
        """
        # 验证参数
        is_valid, error_msg = self.validate_args(command, args)
        if not is_valid:
            return ToolExecutionResult(
                success=False,
                output="",
                error=error_msg
            )

        # 构建完整命令
        full_command = [command]
        if args:
            full_command.extend(args)

        try:
            # 执行命令
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False
            )

            # 获取输出
            output = result.stdout
            if result.stderr:
                output += f"\n[错误输出]\n{result.stderr}"

            return ToolExecutionResult(
                success=result.returncode == 0,
                output=output.strip(),
                error=None if result.returncode == 0 else f"命令返回码: {result.returncode}"
            )

        except subprocess.TimeoutExpired:
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"命令执行超时（>{self.timeout}秒）"
            )
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"命令执行失败: {str(e)}"
            )

    def get_help(self) -> str:
        """获取帮助信息"""
        return f"""
命令执行工具 - 支持的白名单命令:

{', '.join(WHITELIST_COMMANDS)}

使用示例:
  - ls: ['ls', '-la', '/home']
  - cat: ['cat', 'file.txt']
  - grep: ['grep', 'pattern', 'file.txt']
  - head: ['head', '-n', '10', 'file.txt']
  - tail: ['tail', '-n', '20', 'file.txt']
  - ps: ['ps', 'aux']
  - pwd: ['pwd']
  - whoami: ['whoami']
  - df: ['df', '-h']
  - free: ['free', '-h']

安全限制:
  - 仅支持白名单命令
  - 参数中不允许包含: {', '.join(BLACKLIST_CHARS)}
  - 执行超时: {self.timeout} 秒
"""
