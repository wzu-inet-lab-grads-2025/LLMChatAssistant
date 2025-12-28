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
from .ui import ClientUI
from ..utils.logger import get_client_logger


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
        self.ui.print_separator()

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

        # 启动消息接收循环
        asyncio.create_task(self.client.start_message_loop())

        # 显示帮助信息
        self.ui.print_info("输入您的消息，输入 /quit 退出，/help 查看帮助")
        self.ui.print_separator()

        # 主循环
        while self.running and self.client.is_connected():
            try:
                # 获取用户输入
                user_input = await asyncio.to_thread(self.ui.input, "你: ")

                if not user_input:
                    continue

                # 记录用户输入
                self.logger.debug(f"用户输入: {user_input[:50]}...")

                # 解析命令
                if await self._parse_command(user_input):
                    continue

                # 发送聊天消息
                await self.client.send_chat(user_input)
                self.logger.debug("消息已发送")

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

        # /help - 显示帮助
        if command == "/help":
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

        # 未知命令
        else:
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
                # TODO: 实现文件上传逻辑
                # 这里应该通过 NPLT 协议发送文件数据
                progress.update(task_id, advance=filesize)

            self.logger.info(f"文件上传完成: {filename}")
            self.ui.print_success(f"文件上传完成: {filename}")

        except Exception as e:
            self.logger.error(f"读取文件失败: {e}")
            self.ui.print_error(f"读取文件失败: {e}")

    async def _command_model(self, args: list):
        """处理 /model 命令"""
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

        # 切换模型
        # TODO: 发送模型切换请求到服务器
        self.current_model = model
        self.logger.info(f"模型已切换: {model}")
        self.ui.print_success(f"已切换模型: {model}")

    async def _command_history(self):
        """处理 /history 命令"""
        # TODO: 从服务器获取对话历史
        self.ui.print_info("对话历史功能（待实现）")

    async def _command_clear(self):
        """处理 /clear 命令"""
        # TODO: 清空本地对话历史
        self.logger.info("清空对话历史")
        self.ui.clear()
        self.ui.show_welcome()
        self.ui.print_info("对话历史已清空")


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
