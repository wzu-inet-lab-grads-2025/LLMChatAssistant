"""
客户端 UI 模块 (修复版 v2)

修复内容：
1. 移除导致显示异常的 ANSI 转义序列 [2K]。
2. 清理LLM生成的ANSI颜色码，防止显示乱码。
3. 优化手动边框渲染器，利用 pad=True 实现无痕刷新。
4. 保持弹性缓冲算法，解决网络卡顿。
"""

import asyncio
import re
import logging
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
from rich import box

# 获取客户端logger
logger = logging.getLogger(__name__)
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

# 尝试导入 prompt_toolkit 以支持更好的中文输入处理
# prompt_toolkit 能正确处理中文宽字符，解决删除残留问题
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.patch_stdout import patch_stdout

    HAS_PROMPT_TOOLKIT = True
except ImportError:
    # 如果没有安装，回退到Rich input
    HAS_PROMPT_TOOLKIT = False

# ANSI转义码正则表达式（用于清理LLM生成的颜色码）
ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*m')


def clean_ansi_codes(text: str) -> str:
    """清理文本中的ANSI转义码

    LLM（如智谱AI）可能在生成回复时添加颜色码，
    这些码在Rich Console中无法正确解析，会显示为乱码。
    因此需要在显示前清理它们。

    Args:
        text: 包含ANSI码的文本

    Returns:
        清理后的文本
    """
    return ANSI_ESCAPE_PATTERN.sub('', text)


class ManualBorderRenderer:
    """
    手动边框渲染器

    原理：不使用 Rich 的 Panel 容器，而是手动逐行绘制边框字符。
    优势：完全避免 VS Code 终端下的光标回溯重影问题，同时保持流式输出在边框内。

    核心策略：
    1. 手动绘制上边框
    2. 增量打印内容：使用 \\r 刷新最后一行，已确定的行永久打印
    3. 手动绘制下边框
    """
    def __init__(self, console: Console, title: str, width: int, border_style: str = "green"):
        self.console = console
        self.width = width
        self.title = title
        self.border_style = border_style
        # 内容区域宽度 = 总宽度 - 边框(2) - Padding(2)
        self.content_width = width - 4

        # 记录已永久打印的行数
        self.committed_lines = 0

        # 缓存上一帧的渲染结果
        self.last_render_lines = []

    def print_top(self):
        """打印上边框"""
        # 构造：╭─ TITLE ───────╮
        # 计算中间横线的长度
        # 总宽度(80) = 左边框(2: ╭─) + 空格(1) + 标题 + 空格(1) + 横线 + 右边框(2: ─╮)
        # 所以：横线长度 = width - 2 - 1 - len(title) - 1 - 2 = width - 6 - len(title)
        remaining_len = self.width - 6 - len(self.title)

        # 将整个上边框作为一个完整的字符串渲染（避免换行问题）
        top_border = f"╭─ {self.title} " + "─" * max(0, remaining_len) + "─╮"

        # 创建Text对象并应用样式
        line = Text()
        line.append(top_border, style=self.border_style)

        self.console.print(line)

    def print_bottom(self):
        """打印下边框"""
        # 构造：╰──...──╯
        line = Text("╰" + "─" * (self.width - 2) + "╯", style=self.border_style)
        self.console.print(line)

    def update(self, markdown_text: str):
        """增量刷新内容

        Args:
            markdown_text: Markdown 文本
        """
        # 将 Markdown 渲染为行列表
        md = Markdown(markdown_text)

        # 使用 console.render_lines 获取渲染后的行
        options = self.console.options.update_width(self.content_width)
        render_lines = list(self.console.render_lines(md, options, pad=True, new_lines=False))

        total_lines = len(render_lines)

        # 策略：逐行提交，每次都重新渲染最后一条
        # 记录旧的 committed_lines，避免在循环中修改状态影响后续判断
        old_committed = self.committed_lines

        for line_idx in range(total_lines):
            is_last_line = (line_idx == total_lines - 1)

            # 如果这行已经提交过了，跳过（除非是最后一行需要刷新）
            if line_idx < old_committed and not is_last_line:
                continue

            line_segments = render_lines[line_idx]

            # 决定是否为临时行（最后一行总是临时的，可以覆盖）
            is_temp = is_last_line

            self._print_line(line_segments, is_temp=is_temp)

            # 如果不是最后一行，标记为已提交
            if not is_last_line:
                self.committed_lines = line_idx + 1

    def _print_line(self, segments, is_temp: bool):
        """打印带有左右边框的单行

        Args:
            segments: Rich Segment 列表
            is_temp: 是否为临时行（使用 \\r 刷新）
        """
        # 构造行：│  CONTENT  │

        # 左边框 + Padding
        output = Text("│ ", style=self.border_style)

        # 中间内容
        for seg in segments:
            output.append(Text(seg.text, style=seg.style))

        # 右 Padding + 右边框
        output.append(" │", style=self.border_style)

        if is_temp:
            # 临时行：使用 \r 回到行首
            # 注意：移除所有 \x1b[2K，因为 pad=True 保证了新内容会完全覆盖旧内容
            self.console.print(output, end="\r", crop=False)
        else:
            # 确定行：先 \r 覆盖之前的临时显示，然后默认换行
            self.console.print(output, crop=False)


class ClientUI:
    """客户端 UI (手动增量渲染版)"""

    def __init__(self):
        """初始化 UI"""
        self.console = Console(legacy_windows=False, force_terminal=True)
        self.current_spinner = None

        # Live Display 相关状态
        self.live_display = None
        self.is_live = False

        # 生产者-消费者模式：解耦网络接收和UI渲染
        self._full_content = ""       # 后端发来的完整内容（生产者写入）
        self._displayed_content = ""  # 屏幕上当前已显示的内容（消费者读取）
        self._char_accumulator = 0.0  # 亚字符速度控制累加器（实现平滑速度控制）
        self._render_task = None      # 后台渲染任务（消费者）
        self._stop_render = False     # 停止渲染标志

        # 手动渲染器实例
        self._border_renderer = None

        # Spinner 相关状态
        self.spinner_message = ""
        self._spinner_task = None
        self._stop_spinner = False

        # 初始化 prompt_toolkit PromptSession（如果可用）
        # prompt_toolkit 能正确处理中文宽字符，解决删除残留问题
        if HAS_PROMPT_TOOLKIT:
            self.session = PromptSession()
        else:
            self.session = None

    def _get_safe_width(self):
        """VS Code 专用安全宽度计算"""
        # 减去 4 (左右边框+Padding) 再减去余量防止计算误差
        w = self.console.size.width - 5
        return w if w > 10 else 10

    def show_welcome(self):
        """显示欢迎画面"""
        welcome_text = "智能网络运维助手 v1.0\n\n基于 NPLT 协议的 AI 对话和 RDT 文件传输系统"
        safe_width = self._get_safe_width()
        self.console.print(Panel(
            welcome_text,
            border_style="blue bold",
            box=box.ROUNDED,
            width=safe_width
        ))

    # ========================== Spinner ==========================

    def show_spinner(self, message: str = "正在分析意图"):
        """显示加载动画（使用Rich Live原地更新）

        Args:
            message: 提示消息（不含Spinner符号）
        """
        # 如果已经有spinner在运行，只更新消息
        if self.is_live and self._spinner_task is not None and not self._spinner_task.done():
            self.spinner_message = message
            return

        # 如果已有Live显示或任务，先停止
        if self._spinner_task is not None:
            self._stop_spinner = True
            if not self._spinner_task.done():
                self._spinner_task.cancel()
            self._spinner_task = None

        if self.live_display is not None:
            self.live_display.stop()
            self.live_display = None

        self.is_live = True
        self.spinner_message = message
        self._stop_spinner = False

        # 创建Live上下文（transient=True: 动画结束后自动清除，不留痕迹）
        self.live_display = Live(
            Text(""),
            console=self.console,
            refresh_per_second=8,
            vertical_overflow="visible",
            transient=True  # 自动清除，避免历史记录残留
        )
        self.live_display.start()

        # 启动后台刷新任务
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._spinner_task = asyncio.create_task(self._refresh_spinner())
        except RuntimeError:
            pass

    async def _refresh_spinner(self):
        """后台任务：持续刷新Spinner动画"""
        import time

        while not self._stop_spinner and self.live_display is not None:
            if self.live_display is not None:
                self.live_display.update(self._render_spinner())
            try:
                await asyncio.sleep(0.125)
            except asyncio.CancelledError:
                break

    def _render_spinner(self) -> Text:
        """渲染Spinner（符号在末尾）

        Returns:
            格式化后的Text对象
        """
        spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        import time
        frame_index = int(time.time() * 8) % len(spinner_frames)
        frame = spinner_frames[frame_index]

        content = Text()
        content.append(self.spinner_message, style="cyan")
        content.append(" ")
        content.append(frame, style="yellow")
        content.append(" ")
        content.append(frame, style="yellow")

        return content

    def update_spinner(self, message: str):
        """更新Spinner消息"""
        if self.is_live:
            self.spinner_message = message

    def stop_spinner(self):
        """停止加载动画"""
        self._stop_spinner = True

        if self._spinner_task is not None:
            if not self._spinner_task.done():
                self._spinner_task.cancel()
            self._spinner_task = None

        if self.live_display is not None:
            # 清除内容后停止
            self.live_display.update(Text(""))
            self.live_display.stop()
            self.live_display = None

        self.current_spinner = None
        self.is_live = False

        # 强制刷新终端，确保清除所有显示
        self.console.file.flush()

    def _stop_spinner_without_reset(self):
        """清除 Spinner 显示但不重置 is_live 状态

        用于 start_live_display() 中清除 Spinner 残留，
        但不影响后续的流式输出状态。
        """
        self.stop_spinner()  # 直接调用 stop_spinner，因为 start_live_display 会重置 is_live

    # ========================== 核心：手动流式输出 ==========================

    def start_live_display(self):
        """开始Live显示模式（用于流式输出）

        使用手动增量渲染器，彻底解决 VS Code 终端重影问题。
        """
        # 清理上一轮
        if self._render_task:
            self._stop_live_display_sync()

        # 清除 Spinner 残留（但在重置状态之前，避免重置 is_live）
        self._stop_spinner_without_reset()

        # 重置缓冲区和状态
        self._full_content = ""
        self._displayed_content = ""
        self._char_accumulator = 0.0
        self._stop_render = False
        self.is_live = True

        # 打印换行
        self.console.print()

        # 初始化手动渲染器
        safe_width = self._get_safe_width()
        self._border_renderer = ManualBorderRenderer(
            self.console,
            title="ASSISTANT",
            width=safe_width,
            border_style="green"
        )

        # 打印上边框
        self._border_renderer.print_top()

        # 启动后台渲染任务
        try:
            loop = asyncio.get_event_loop()
            self._render_task = loop.create_task(self._render_loop())
        except RuntimeError:
            self.console.print("[red]错误: 未检测到 asyncio 事件循环，流式输出无法启动[/red]")

    def stream_content(self, content: str, force_update: bool = False):
        """流式更新内容（生产者：接收后端数据）

        Args:
            content: 新收到的文本片段
            force_update: 是否强制更新（保留参数兼容性，当前不使用）
        """
        if self.is_live:
            # 调试日志：记录接收到的content（写入日志文件）
            logger.debug(f"接收到content: 长度={len(content)}字符, 字节={len(content.encode('utf-8'))}bytes")
            logger.debug(f"content前100字符: {repr(content[:100])}")

            # 清理ANSI转义码后再添加（防止LLM生成的颜色码显示为乱码）
            cleaned = clean_ansi_codes(content)

            logger.debug(f"清理ANSI后长度: {len(cleaned)}字符")
            logger.debug(f"当前_full_content长度: {len(self._full_content)} → {len(self._full_content) + len(cleaned)}")

            self._full_content += cleaned

    async def _render_loop(self):
        """消费者：弹性渲染循环（手动增量渲染）

        使用浮点累加器实现亚字符级速度控制。
        配合手动边框渲染器，彻底消除 VS Code 终端重影问题。

        弹性速度策略：
        - backlog > 200: 200 字符/秒（极速追赶）
        - backlog > 50: 80 字符/秒（快速追赶）
        - backlog > 10: 30 字符/秒（正常阅读速度）
        - backlog > 5: 10 字符/秒（慢速）
        - backlog ≤ 5: 5 字符/秒（极慢，掩盖网络卡顿）
        """
        FRAME_INTERVAL = 0.05  # 20fps
        displayed_len = 0

        while not self._stop_render:
            target_len = len(self._full_content)
            backlog = target_len - displayed_len

            if backlog > 0:
                # === 弹性速度控制 ===
                if backlog > 200:
                    speed = 200.0
                elif backlog > 50:
                    speed = 80.0
                elif backlog > 10:
                    speed = 30.0
                elif backlog > 5:
                    speed = 10.0
                else:
                    speed = 5.0

                # 累加应该显示的字符数（浮点运算）
                self._char_accumulator += speed * FRAME_INTERVAL
                step = int(self._char_accumulator)

                if step > 0:
                    # 限制步长不超过积压量
                    step = min(step, backlog)

                    # 更新已显示内容
                    current_text = self._full_content[:displayed_len + step]
                    displayed_len += step
                    self._char_accumulator -= step

                    # === 调用手动渲染器 ===
                    if self._border_renderer:
                        self._border_renderer.update(current_text)

                await asyncio.sleep(FRAME_INTERVAL)
            else:
                # 缓冲区空了，降低轮询频率
                await asyncio.sleep(0.05)

    async def stop_live_display(self):
        """停止Live显示模式（优雅退出）- 手动渲染器版本

        封口：打印下边框。
        """
        # 停止渲染任务
        self._stop_render = True

        if self._render_task is not None:
            try:
                await self._render_task
            except asyncio.CancelledError:
                pass
            self._render_task = None

        # 确保显示完整内容
        if self._border_renderer and self._full_content:
            # 如果缓冲区里还有没显示的，一次性显示完
            if len(self._displayed_content) < len(self._full_content):
                self._border_renderer.update(self._full_content)
            # 换行，移出最后一行临时区
            self.console.print()
            # 打印下边框
            self._border_renderer.print_bottom()

        # 清理状态
        self._border_renderer = None
        self.is_live = False
        self._full_content = ""
        self._displayed_content = ""
        self._char_accumulator = 0.0

    def _stop_live_display_sync(self):
        """同步停止Live显示（用于用户输入前快速停止）

        手动渲染器版本的同步停止。
        """
        # 停止渲染任务
        self._stop_render = True

        # 尽力显示剩余内容
        if self._border_renderer and self._full_content:
            self._border_renderer.update(self._full_content)
            self.console.print()
            self._border_renderer.print_bottom()

        # 清理状态
        self._border_renderer = None
        self.is_live = False
        self._full_content = ""
        self._displayed_content = ""
        self._render_task = None

        # 强制刷新终端，确保清除所有显示
        self.console.file.flush()

    # ========================== 通用输出方法 ==========================

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

        # 清理ANSI转义码（防止LLM生成的颜色码显示为乱码）
        content = clean_ansi_codes(content)

        # 如果内容包含 Markdown 语法，尝试渲染 Markdown
        renderable = content
        if "```" in content or "**" in content or "\n- " in content:
            renderable = Markdown(content)

        # 创建面板（使用安全宽度和圆角边框）
        safe_width = self._get_safe_width()
        panel = Panel(
            renderable,
            title=role.upper(),
            title_align="left",
            border_style=style,
            box=box.ROUNDED,
            width=safe_width
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

    def input(self, prompt: str = "", clear_after_input: bool = False) -> str:
        """获取用户输入

        Args:
            prompt: 提示符
            clear_after_input: 是否在输入后清除输入行（默认False）

        Returns:
            用户输入
        """
        # 确保在输入前停止所有动态显示
        if self.is_live:
            self._stop_live_display_sync()

        # 清除 Spinner 痕迹
        self.stop_spinner()

        # 强制刷新终端，清除所有残留显示
        self.console.file.flush()

        # 如果 prompt_toolkit 可用，使用它来处理输入
        # prompt_toolkit 能正确处理中文宽字符，解决删除残留问题
        if HAS_PROMPT_TOOLKIT and self.session is not None:
            # 使用 Rich 的 console.capture() 将带 Rich 标签的 prompt 转换为 ANSI 代码
            with self.console.capture() as capture:
                self.console.print(prompt, end="")

            ansi_prompt = capture.get()

            # 使用 prompt_toolkit 的 PromptSession 来获取输入
            # patch_stdout() 确保 Rich 的输出（如流式响应）不会干扰 prompt_toolkit 的输入编辑器
            try:
                with patch_stdout():
                    user_input = self.session.prompt(ANSI(ansi_prompt))

                # 如果需要清除输入行
                if clear_after_input:
                    # prompt_toolkit 输入后已经换行，需要清除上一行
                    # 使用 ANSI 转义序列：\033[F 移到上一行开头，\033[K 清除到行尾
                    import sys
                    sys.stdout.write("\033[F\033[K")
                    sys.stdout.flush()
                else:
                    # 打印换行符，隔离输入行和后续显示
                    print()

                return user_input.strip()
            except EOFError:
                return ""
            except KeyboardInterrupt:
                return ""
        else:
            # 回退到使用 Rich 自带的 input 方法
            try:
                user_input = self.console.input(prompt)

                # 如果需要清除输入行
                if clear_after_input:
                    # 使用 ANSI 转义序列清除当前行并回到行首
                    # \r 回到行首，\x1b[2K 清除整行
                    self.console.print("\r\x1b[2K", end="")

                return user_input.strip()
            except EOFError:
                return ""
            except KeyboardInterrupt:
                return ""

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
