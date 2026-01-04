"""
命令执行工具模块

提供安全的命令执行功能，仅支持白名单命令和路径白名单。
遵循章程：安全加固，命令黑名单字符过滤 + 路径白名单
"""

import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

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

# 需要路径验证的命令
PATH_VALIDATION_COMMANDS = ['cat', 'head', 'tail', 'grep', 'ls']


@dataclass
class CommandTool(Tool):
    """命令执行工具"""

    name: str = "command_executor"
    description: str = """执行安全的系统命令（白名单命令）

可用命令：
- cat <文件>: 查看文件内容（如：cat config.yaml）
- head <文件>: 查看文件前几行（如：head -20 config.yaml）
- tail <文件>: 查看文件后几行（如：tail -20 config.yaml）
- grep <模式> <文件>: 在文件中搜索文本（如：grep "port" config.yaml）
- ls [目录]: 列出目录内容（如：ls storage/uploads/）
- ps: 查看进程列表
- pwd: 显示当前工作目录
- whoami: 显示当前用户
- df: 查看磁盘使用情况
- free: 查看内存使用情况

适用场景：
- 用户想"查看"、"读取"、"显示"文件内容 → 使用 cat/head/tail
- 用户想"搜索"、"查找"文件中的文本 → 使用 grep
- 用户想"列出"、"浏览"目录 → 使用 ls

注意：命令必须在白名单中，路径必须通过白名单验证"""
    timeout: int = 5
    path_validator: Optional[object] = field(default=None)
    max_output_size: int = 102400  # 100KB

    def validate_args(self, command: str, args: List[str] = None) -> tuple[bool, str]:
        """验证命令和参数

        Args:
            command: 命令名称
            args: 参数列表

        Returns:
            (是否有效, 错误消息)
        """
        # 1. 检查命令是否在白名单中
        if command not in WHITELIST_COMMANDS:
            return False, f"命令不在白名单中: {command}"

        # 2. 检查参数中是否包含黑名单字符
        if args:
            for arg in args:
                for char in BLACKLIST_CHARS:
                    if char in arg:
                        return False, f"参数包含非法字符 '{char}': {arg}"

        # 3. 路径白名单验证（针对需要路径验证的命令）
        if command in PATH_VALIDATION_COMMANDS and self.path_validator:
            if args:
                # grep命令特殊处理：grep [options] pattern file
                # 只有最后一个参数（文件）需要路径验证，pattern不需要
                if command == 'grep':
                    # 找到非选项参数（不以-开头）
                    non_option_args = [arg for arg in args if not arg.startswith('-')]

                    # grep至少需要2个参数：pattern和file
                    if len(non_option_args) >= 2:
                        # 只验证最后一个参数（文件路径）
                        file_path = non_option_args[-1]
                        allowed, msg = self.path_validator.is_allowed(file_path)
                        if not allowed:
                            return False, msg
                    elif len(non_option_args) == 1:
                        # 只有1个参数，可能是从stdin读取，需要验证
                        file_path = non_option_args[0]
                        # 检查是否是实际存在的文件
                        import os
                        if os.path.exists(file_path):
                            allowed, msg = self.path_validator.is_allowed(file_path)
                            if not allowed:
                                return False, msg
                else:
                    # 其他命令（cat, head, tail, ls）：分别处理
                    if command in ['head', 'tail']:
                        # head/tail命令特殊处理：[-n num] file
                        # -n的参数是数字，不是路径
                        for i, arg in enumerate(args):
                            # 跳过选项参数
                            if arg.startswith('-'):
                                # 如果是-n，下一个参数是数字，跳过
                                if arg == '-n' and i + 1 < len(args):
                                    continue
                                continue

                            # 最后一个参数通常是文件路径
                            if i == len(args) - 1:
                                allowed, msg = self.path_validator.is_allowed(arg)
                                if not allowed:
                                    return False, msg
                            # 其他参数（如数字）不需要验证

                    elif command == 'ls':
                        # ls：所有非选项参数都验证
                        for arg in args:
                            if arg.startswith('-'):
                                continue
                            allowed, msg = self.path_validator.is_allowed(arg)
                            if not allowed:
                                return False, msg

                    elif command == 'cat':
                        # cat：所有非选项参数都验证
                        for arg in args:
                            if arg.startswith('-'):
                                continue
                            allowed, msg = self.path_validator.is_allowed(arg)
                            if not allowed:
                                return False, msg

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

            # 限制输出大小
            if len(output) > self.max_output_size:
                output = output[:self.max_output_size] + f"\n... (输出已截断，共 {len(result.stdout)} 字节)"

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
