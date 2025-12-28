"""
客户端 UI 模块

提供基于 Rich 的沉浸式终端界面组件。
遵循章程：真实实现，不允许虚假实现或占位符
"""

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text


class ClientUI:
    """客户端 UI"""

    def __init__(self):
        """初始化 UI"""
        self.console = Console()
        self.current_spinner = None

    def show_welcome(self):
        """显示欢迎画面"""
        welcome_text = """
╭────────────────────────────────────────╮
│     智能网络运维助手 v1.0              │
╰────────────────────────────────────────╯

基于 NPLT 协议的 AI 对话和 RDT 文件传输系统
        """

        self.console.print(Panel(welcome_text, border_style="blue bold"))
        self.console.print()

    def show_spinner(self, message: str = "加载中..."):
        """显示加载动画

        Args:
            message: 提示消息
        """
        self.current_spinner = Spinner("dots", text=message)
        self.console.print(self.current_spinner)

    def stop_spinner(self):
        """停止加载动画"""
        self.current_spinner = None

    def print_message(self, role: str, content: str, style: str = None):
        """打印消息

        Args:
            role: 角色（user/assistant/system）
            content: 消息内容
            style: 样式
        """
        if style is None:
            if role == "user":
                style = "cyan bold"
            elif role == "assistant":
                style = "green"
            else:
                style = "yellow"

        # 创建面板
        panel = Panel(
            content,
            title=role.upper(),
            title_align="left",
            border_style=style
        )

        self.console.print(panel)

    def print_markdown(self, content: str):
        """渲染 Markdown 内容

        Args:
            content: Markdown 文本
        """
        markdown = Markdown(content)
        self.console.print(markdown)

    def print_agent_thought(self, thought: str):
        """打印 Agent 思考过程

        Args:
            thought: 思考内容
        """
        self.console.print(f"[dim]⠙ {thought}[/dim]")

    def print_tool_status(self, tool_name: str, status: str, message: str = ""):
        """打印工具状态

        Args:
            tool_name: 工具名称
            status: 状态（running/success/failed）
            message: 附加消息
        """
        if status == "running":
            icon = "⠙"
            color = "yellow"
        elif status == "success":
            icon = "✓"
            color = "green"
        else:  # failed
            icon = "✗"
            color = "red"

        text = f"[{color}]{icon} [Tool: {tool_name}]"
        if message:
            text += f" {message}"
        text += f"[/{color}]"

        self.console.print(text)

    def create_upload_progress(self, filename: str, total_size: int) -> Progress:
        """创建上传进度条

        Args:
            filename: 文件名
            total_size: 文件总大小

        Returns:
            Progress 实例
        """
        progress = Progress(
            TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            console=self.console,
        )

        task_id = progress.add_task(
            filename,
            filename=filename,
            total=total_size
        )

        return progress, task_id

    def create_download_progress(
        self,
        filename: str,
        total_size: int,
        window_size: int = 5
    ) -> tuple[Progress, int]:
        """创建下载进度条（RDT）

        Args:
            filename: 文件名
            total_size: 文件总大小
            window_size: 窗口大小

        Returns:
            (Progress, task_id)
        """
        progress = Progress(
            TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            "•",
            TextColumn("{task.fields[window]}"),
            console=self.console,
        )

        task_id = progress.add_task(
            filename,
            filename=filename,
            total=total_size,
            window=""
        )

        return progress, task_id

    def update_download_window(self, progress: Progress, task_id: int, window_state: str):
        """更新下载窗口状态

        Args:
            progress: Progress 实例
            task_id: 任务 ID
            window_state: 窗口状态字符串（如 "[0] [1] [2] [3] [4]"）
        """
        progress.update(task_id, window=window_state)

    def print_error(self, message: str):
        """打印错误消息

        Args:
            message: 错误消息
        """
        self.console.print(f"[red bold]错误: {message}[/red bold]")

    def print_warning(self, message: str):
        """打印警告消息

        Args:
            message: 警告消息
        """
        self.console.print(f"[yellow bold]警告: {message}[/yellow bold]")

    def print_info(self, message: str):
        """打印信息消息

        Args:
            message: 信息消息
        """
        self.console.print(f"[blue]{message}[/blue]")

    def print_success(self, message: str):
        """打印成功消息

        Args:
            message: 成功消息
        """
        self.console.print(f"[green bold]✓ {message}[/green bold]")

    def print_separator(self):
        """打印分隔线"""
        self.console.print("─" * 80)

    def print_help(self):
        """打印帮助信息"""
        help_table = Table(title="命令列表", show_header=True, header_style="bold magenta")
        help_table.add_column("命令", style="cyan", width=20)
        help_table.add_column("描述", style="white")

        commands = [
            ("/upload <file>", "上传文件到服务器"),
            ("/model <name>", "切换聊天模型 (glm-4-flash / glm-4.5-flash)"),
            ("/history", "查看对话历史"),
            ("/clear", "清空当前会话历史"),
            ("/quit", "退出客户端"),
            ("/help", "显示此帮助信息"),
        ]

        for cmd, desc in commands:
            help_table.add_row(cmd, desc)

        self.console.print(help_table)

    def confirm(self, message: str) -> bool:
        """确认提示

        Args:
            message: 确认消息

        Returns:
            用户确认结果
        """
        response = self.console.input(f"[yellow]{message} [y/N]: [/yellow]")
        return response.lower() in ['y', 'yes']

    def input(self, prompt: str = "") -> str:
        """获取用户输入

        Args:
            prompt: 提示符

        Returns:
            用户输入
        """
        return self.console.input(prompt).strip()

    def clear(self):
        """清空控制台"""
        self.console.clear()


# 全局 UI 实例
_ui_instance = None


def get_ui() -> ClientUI:
    """获取全局 UI 实例"""
    global _ui_instance
    if _ui_instance is None:
        _ui_instance = ClientUI()
    return _ui_instance
