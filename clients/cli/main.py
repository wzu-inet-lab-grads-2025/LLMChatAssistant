"""
客户端主模块

实现客户端主循环、命令解析和用户交互。
遵循章程：真实实现，不允许虚假实现或占位符
"""

import asyncio
import os
import sys
from typing import Optional

from .nplt_client import NPLTClient
from .rdt_client import RDTClient
from .ui import ClientUI
from shared.utils.logger import get_client_logger


class ClientMain:
    """客户端主程序"""

    def __init__(self, host: str = "127.0.0.1", port: int = 9999):
        """初始化客户端

        Args:
            host: 服务器地址
            port: 服务器端口
        """
        self.host = host
        self.port = port
        self.ui = ClientUI()
        self.client: Optional[NPLTClient] = None
        self.rdt_client: Optional[RDTClient] = None
        self.running = False
        self.logger = get_client_logger()

        # 当前模型
        self.current_model = "glm-4-flash"

    async def start(self):
        """启动客户端"""
        self.logger.info("客户端启动中...")
        self.logger.info(f"服务器地址: {self.host}:{self.port}")

        # 显示欢迎画面
        self.ui.show_welcome()

        # 创建客户端
        self.client = NPLTClient(
            host=self.host,
            port=self.port,
            ui=self.ui
        )

        # 连接到服务器
        if not await self.client.connect():
            self.logger.error("无法连接到服务器")
            self.ui.print_error("无法连接到服务器，退出")
            return

        self.logger.info("已连接到服务器")
        self.running = True

        # 初始化 RDT 客户端
        self.rdt_client = RDTClient(
            server_host=self.host,
            server_port=9998,
            window_size=5
        )
        await self.rdt_client.start()

        # 向服务器注册客户端 UDP 端口（用于 RDT 文件下载）
        udp_port = self.rdt_client.get_local_port()
        await self._register_udp_port(udp_port)

        # 注册下载处理器
        self.client.download_handler = self._handle_download_offer

        # 启动消息接收循环
        asyncio.create_task(self.client.start_message_loop())

        # 等待服务器的欢迎消息（第一个消息）
        # 这样可以确保欢迎消息显示后再显示"User>"提示符
        await self.client.response_event.wait()
        self.client.response_event.clear()

        # 主循环
        while self.running and self.client.is_connected():
            try:
                # 获取用户输入（清除输入行以避免重复显示）
                user_input = await asyncio.to_thread(self.ui.input, "User> ", clear_after_input=True)

                if not user_input:
                    continue

                # 记录用户输入
                self.logger.debug(f"用户输入: {user_input[:50]}...")

                # 解析命令
                if await self._parse_command(user_input):
                    continue

                # 显示用户消息（用Panel格式，会自动清除输入行）
                self.ui.print_message("user", user_input)

                # 发送聊天消息
                await self.client.send_chat(user_input)

                # 显示Spinner
                self.ui.show_spinner("[Agent] 正在分析意图")

                self.logger.debug("消息已发送，等待响应...")

                # 等待响应完成（通过Event通知）
                await self.client.response_event.wait()
                self.client.response_event.clear()

            except KeyboardInterrupt:
                self.logger.info("收到中断信号")
                self.ui.print_info("\n收到中断信号，正在退出...")
                break
            except Exception as e:
                self.logger.error(f"主循环错误: {e}")
                self.ui.print_error(f"错误: {e}")
                break

        # 清理
        await self.stop()

    async def stop(self):
        """停止客户端"""
        self.logger.info("客户端停止中...")
        self.running = False

        # 停止 RDT 客户端
        if self.rdt_client:
            await self.rdt_client.stop()

        if self.client:
            await self.client.disconnect()

        self.ui.print_info("再见！")
        self.logger.info("客户端已停止")

    async def _parse_command(self, user_input: str) -> bool:
        """解析命令

        Args:
            user_input: 用户输入

        Returns:
            是否为命令（已处理）
        """
        if not user_input.startswith('/'):
            return False

        parts = user_input.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        self.logger.info(f"执行命令: {command} 参数: {args}")

        # /help - 显示帮助
        if command == "/help":
            self.logger.debug("显示帮助信息")
            self.ui.print_help()
            return True

        # /quit - 退出
        elif command == "/quit":
            self.logger.info("用户请求退出")
            self.running = False
            return True

        # /upload <file> - 上传文件
        elif command == "/upload":
            await self._command_upload(args)
            return True

        # /model <name> - 切换模型
        elif command == "/model":
            await self._command_model(args)
            return True

        # /history - 查看历史
        elif command == "/history":
            await self._command_history()
            return True

        # /clear - 清空历史
        elif command == "/clear":
            await self._command_clear()
            return True

        # /sessions - 会话列表
        elif command == "/sessions":
            await self._command_sessions()
            return True

        # /switch <session_id> - 切换会话
        elif command == "/switch":
            await self._command_switch(args)
            return True

        # /new - 创建新会话
        elif command == "/new":
            await self._command_new()
            return True

        # /delete <session_id> - 删除会话
        elif command == "/delete":
            await self._command_delete(args)
            return True

        # 未知命令
        else:
            self.logger.warning(f"未知命令: {command}")
            self.ui.print_warning(f"未知命令: {command}，输入 /help 查看帮助")
            return True

    async def _command_upload(self, args: list):
        """处理 /upload 命令"""
        if not args:
            self.ui.print_error("用法: /upload <文件路径>")
            return

        filepath = args[0]
        self.logger.info(f"上传文件请求: {filepath}")

        # 检查文件是否存在
        if not os.path.exists(filepath):
            self.logger.error(f"文件不存在: {filepath}")
            self.ui.print_error(f"文件不存在: {filepath}")
            return

        # 获取文件信息
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)

        # 检查文件大小（10MB 限制）
        max_size = 10 * 1024 * 1024
        if filesize > max_size:
            self.logger.error(f"文件大小超过限制: {filesize} > {max_size}")
            self.ui.print_error(f"文件大小超过限制 ({filesize} > {max_size} 字节)")
            return

        self.logger.info(f"上传文件: {filename} ({filesize} 字节)")
        self.ui.print_info(f"上传文件: {filename} ({filesize} 字节)")

        # 读取文件内容
        try:
            with open(filepath, 'rb') as f:
                file_data = f.read()

            # 创建进度条
            progress, task_id = self.ui.create_upload_progress(filename, filesize)

            with progress:
                # 发送文件元数据
                await self.client.send_file_metadata(filename, filesize)

                # 分块发送文件数据
                await self.client.send_file_data(file_data, progress, task_id)

            self.logger.info(f"文件上传完成: {filename}")
            self.ui.print_success(f"文件上传完成: {filename}")

        except Exception as e:
            self.logger.error(f"上传文件失败: {e}")
            self.ui.print_error(f"上传文件失败: {e}")

    async def _command_model(self, args: list):
        """处理 /model 命令

        遵循规范边界情况: 当服务器返回切换失败时，客户端不应更新本地模型状态
        """
        if not args:
            self.logger.info(f"当前模型: {self.current_model}")
            self.ui.print_info(f"当前模型: {self.current_model}")
            self.ui.print_info("可用模型: glm-4-flash, glm-4.5-flash")
            return

        model = args[0]

        # 验证模型名称
        available_models = ["glm-4-flash", "glm-4.5-flash"]
        if model not in available_models:
            self.logger.warning(f"无效的模型: {model}")
            self.ui.print_error(f"无效的模型: {model}")
            self.ui.print_info(f"可用模型: {', '.join(available_models)}")
            return

        # 发送模型切换请求到服务器
        import json
        from shared.protocols.nplt import MessageType

        model_data = json.dumps({"model": model})
        success = await self.client.send_message(
            MessageType.MODEL_SWITCH,
            model_data.encode('utf-8')
        )

        if not success:
            self.logger.error(f"发送模型切换请求失败: {model}")
            self.ui.print_error(f"发送模型切换请求失败")
            return

        # 等待服务器响应并验证 (遵循 FR-020: 服务器验证模型切换成功)
        # 注意：服务器的响应会通过消息接收循环异步到达
        # 这里只记录请求已发送，实际状态更新将在收到服务器确认后处理
        self.logger.info(f"模型切换请求已发送: {model}，等待服务器确认")
        self.ui.print_info(f"模型切换请求已发送，等待服务器确认...")

        # TODO: 未来可以添加临时状态标记，等待服务器确认消息
        # 当前的实现是：服务器通过 CHAT_TEXT 消息发送确认或错误
        # 客户端会在 UI 中显示服务器响应，但 current_model 的更新需要手动处理

    async def _command_history(self):
        """处理 /history 命令"""
        from shared.protocols.nplt import MessageType

        # 发送历史记录请求到服务器
        success = await self.client.send_message(
            MessageType.HISTORY_REQUEST,
            b""
        )

        if not success:
            self.logger.error("发送历史记录请求失败")
            self.ui.print_error("获取历史记录失败")

    async def _command_clear(self):
        """处理 /clear 命令"""
        from shared.protocols.nplt import MessageType

        # 发送清空请求到服务器
        success = await self.client.send_message(
            MessageType.CLEAR_REQUEST,
            b""
        )

        if success:
            self.logger.info("清空对话历史请求已发送")
            self.ui.clear()
            self.ui.show_welcome()
            self.ui.print_info("对话历史已清空")
        else:
            self.logger.error("发送清空请求失败")
            self.ui.print_error("清空对话历史失败")

    async def _command_sessions(self):
        """处理 /sessions 命令"""
        from shared.protocols.nplt import MessageType

        # 发送会话列表请求到服务器
        success = await self.client.send_message(
            MessageType.SESSION_LIST,
            b""
        )

        if not success:
            self.logger.error("发送会话列表请求失败")
            self.ui.print_error("获取会话列表失败")

    async def _command_switch(self, args: list):
        """处理 /switch 命令"""
        if not args:
            self.ui.print_error("用法: /switch <会话ID>")
            return

        session_id = args[0]
        self.logger.info(f"切换会话请求: {session_id}")

        from shared.protocols.nplt import MessageType
        import json

        # 发送切换会话请求到服务器
        switch_data = json.dumps({"session_id": session_id})
        success = await self.client.send_message(
            MessageType.SESSION_SWITCH,
            switch_data.encode('utf-8')
        )

        if not success:
            self.logger.error(f"发送切换会话请求失败: {session_id}")
            self.ui.print_error("切换会话失败")

    async def _command_new(self):
        """处理 /new 命令"""
        self.logger.info("创建新会话请求")

        from shared.protocols.nplt import MessageType

        # 发送创建新会话请求到服务器
        success = await self.client.send_message(
            MessageType.SESSION_NEW,
            b""
        )

        if not success:
            self.logger.error("发送创建新会话请求失败")
            self.ui.print_error("创建新会话失败")

    async def _command_delete(self, args: list):
        """处理 /delete 命令"""
        if not args:
            self.ui.print_error("用法: /delete <会话ID>")
            return

        session_id = args[0]
        self.logger.info(f"删除会话请求: {session_id}")

        # 二次确认
        confirm = await asyncio.to_thread(
            self.ui.input,
            f"确认删除会话 {session_id}? (y/n): "
        )

        if confirm.lower() != 'y':
            self.ui.print_warning("删除已取消")
            return

        from shared.protocols.nplt import MessageType
        import json

        # 发送删除会话请求到服务器
        delete_data = json.dumps({"session_id": session_id})
        success = await self.client.send_message(
            MessageType.SESSION_DELETE,
            delete_data.encode('utf-8')
        )

        if not success:
            self.logger.error(f"发送删除会话请求失败: {session_id}")
            self.ui.print_error("删除会话失败")

    async def _register_udp_port(self, udp_port: int):
        """向服务器注册客户端 UDP 端口（用于 RDT 文件传输）

        Args:
            udp_port: 客户端 UDP 端口号
        """
        try:
            import json
            from shared.protocols.nplt import MessageType

            # 构造 UDP 端口注册消息
            port_data = json.dumps({"udp_port": udp_port})
            success = await self.client.send_message(
                MessageType.CLIENT_UDP_PORT,
                port_data.encode('utf-8')
            )

            if success:
                self.logger.info(f"已向服务器注册 UDP 端口: {udp_port}")
            else:
                self.logger.warning(f"发送 UDP 端口注册消息失败: {udp_port}")

        except Exception as e:
            self.logger.error(f"注册 UDP 端口失败: {e}")

    async def _handle_download_offer(self, offer_data: dict):
        """处理下载提议

        Args:
            offer_data: 下载提议数据
        """
        try:
            filename = offer_data.get("filename", "unknown")
            filesize = offer_data.get("size", 0)
            checksum = offer_data.get("checksum", "")
            download_token = offer_data.get("download_token", "")
            server_host = offer_data.get("server_host", self.host)
            server_port = offer_data.get("server_port", 9998)

            # 格式化文件大小
            size_str = self._format_filesize(filesize)

            # 显示下载信息（自动接受）
            self.ui.print_separator()
            self.ui.print_info(f"📥 开始接收文件: {filename}")
            self.ui.print_info(f"文件大小: {size_str}")
            self.ui.print_info(f"MD5 校验和: {checksum}")
            self.ui.print_separator()

            # 自动开始下载（无需用户确认）
            self.logger.info(f"自动接收下载: {filename}")

            # 开始下载
            await self._download_file(
                filename=filename,
                filesize=filesize,
                checksum=checksum,
                download_token=download_token,
                server_host=server_host,
                server_port=server_port
            )

        except Exception as e:
            self.logger.error(f"处理下载提议失败: {e}")
            self.ui.print_error(f"下载失败: {e}")

    async def _download_file(
        self,
        filename: str,
        filesize: int,
        checksum: str,
        download_token: str,
        server_host: str,
        server_port: int
    ):
        """下载文件

        Args:
            filename: 文件名
            filesize: 文件大小
            checksum: 校验和
            download_token: 下载令牌
            server_host: 服务器地址
            server_port: 服务器端口
        """
        try:
            import time
            from datetime import datetime

            self.logger.info(f"开始下载: {filename}")
            self.ui.print_info(f"正在下载: {filename}...")

            # 创建接收会话
            session = self.rdt_client.create_session(
                download_token=download_token,
                filename=filename,
                file_size=filesize,
                expected_checksum=checksum
            )

            # 创建进度条
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=self.ui.console
            )

            with progress:
                task_id = progress.add_task(
                    f"下载 {filename}",
                    total=filesize
                )

                # 启动进度更新任务
                start_time = time.time()

                async def update_progress():
                    while session.state.value == "receiving":
                        received = sum(len(data) for data in session.received_packets.values())
                        progress.update(task_id, completed=received)
                        await asyncio.sleep(0.1)

                progress_task = asyncio.create_task(update_progress())

                # 接收文件
                file_data = await self.rdt_client.receive_file(download_token)

                # 取消进度更新任务
                progress_task.cancel()
                progress.update(task_id, completed=filesize)

            if file_data is None:
                self.ui.print_error("文件下载失败")
                return

            # 验证文件完整性
            import hashlib
            computed_checksum = hashlib.md5(file_data).hexdigest()
            if computed_checksum != checksum:
                self.ui.print_error("文件校验和不匹配，文件可能损坏")
                return

            # 保存文件
            save_path = os.path.join("downloads", filename)
            os.makedirs("downloads", exist_ok=True)

            with open(save_path, 'wb') as f:
                f.write(file_data)

            # 计算统计信息
            elapsed = time.time() - start_time
            speed = filesize / elapsed if elapsed > 0 else 0

            self.ui.print_success(f"文件下载完成: {filename}")
            self.ui.print_info(f"保存位置: {save_path}")
            self.ui.print_info(f"耗时: {elapsed:.2f} 秒")
            self.ui.print_info(f"平均速度: {self._format_filesize(speed)}/s")
            self.ui.print_info(f"接收统计: {session.received_count}/{session.total_packets} 包, "
                             f"重复: {session.duplicate_count}")

            self.logger.info(f"文件下载完成: {filename} -> {save_path}")

        except Exception as e:
            self.logger.error(f"下载文件失败: {e}")
            self.ui.print_error(f"下载失败: {e}")

    def _format_filesize(self, size: int) -> str:
        """格式化文件大小

        Args:
            size: 文件大小（字节）

        Returns:
            格式化后的字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


async def main():
    """主函数"""
    # 从环境变量或命令行参数获取服务器地址
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("SERVER_PORT", "9999"))

    # 创建并启动客户端
    client = ClientMain(host, port)
    await client.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n退出")
        sys.exit(0)
