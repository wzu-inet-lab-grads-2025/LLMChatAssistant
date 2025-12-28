"""
NPLT 客户端模块

实现 NPLT 协议的客户端处理、连接管理和自动重连。
遵循章程：真实实现，不允许虚假实现或占位符
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from ..protocols.nplt import MessageType, NPLTMessage
from ..utils.logger import get_client_logger
from .ui import ClientUI


@dataclass
class NPLTClient:
    """NPLT 客户端"""

    host: str = "127.0.0.1"
    port: int = 9999
    max_retries: int = 3
    heartbeat_interval: int = 90

    # 内部状态
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    connected: bool = False
    send_seq: int = 0
    recv_seq: int = 0
    retry_count: int = 0

    # UI
    ui: ClientUI = None

    # 消息处理器
    message_handler: Optional[Callable] = None

    # 日志记录器（在 __post_init__ 中初始化）
    logger = None

    def __post_init__(self):
        """初始化"""
        if self.ui is None:
            self.ui = ClientUI()
        self.logger = get_client_logger()

    async def connect(self) -> bool:
        """连接到服务器

        Returns:
            是否连接成功
        """
        self.retry_count = 0
        self.logger.info(f"开始连接到服务器 {self.host}:{self.port}")

        while self.retry_count < self.max_retries:
            try:
                self.ui.print_info(f"连接到服务器 {self.host}:{self.port} (尝试 {self.retry_count + 1}/{self.max_retries})...")

                # 建立连接
                self.reader, self.writer = await asyncio.open_connection(
                    self.host,
                    self.port
                )

                self.connected = True
                self.logger.info("连接成功")
                self.ui.print_success(f"连接成功")
                return True

            except Exception as e:
                self.retry_count += 1
                self.logger.warning(f"连接失败 (尝试 {self.retry_count}/{self.max_retries}): {e}")
                self.ui.print_error(f"连接失败: {e}")

                if self.retry_count < self.max_retries:
                    self.ui.print_info(f"等待 2 秒后重试...")
                    await asyncio.sleep(2)
                else:
                    self.logger.error(f"达到最大重试次数 ({self.max_retries})，放弃连接")
                    self.ui.print_error(f"达到最大重试次数 ({self.max_retries})，放弃连接")
                    return False

        return False

    async def disconnect(self):
        """断开连接"""
        self.logger.info("断开连接")
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                self.logger.warning(f"关闭连接时出错: {e}")

        self.connected = False
        self.ui.print_info("已断开连接")

    async def send_message(self, message_type: MessageType, data: bytes) -> bool:
        """发送消息

        Args:
            message_type: 消息类型
            data: 消息数据

        Returns:
            是否发送成功
        """
        if not self.connected or not self.writer:
            self.ui.print_error("未连接到服务器")
            return False

        try:
            # 创建消息
            message = NPLTMessage(
                type=message_type,
                seq=self.send_seq,
                data=data
            )

            # 编码并发送
            encoded = message.encode()
            self.writer.write(encoded)
            await self.writer.drain()

            # 更新序列号
            self.send_seq = (self.send_seq + 1) % 65536

            return True

        except Exception as e:
            self.ui.print_error(f"发送消息失败: {e}")
            self.connected = False
            return False

    async def receive_message(self) -> Optional[NPLTMessage]:
        """接收消息

        Returns:
            接收到的消息或 None
        """
        if not self.connected or not self.reader:
            return None

        try:
            # 读取消息头部
            header = await asyncio.wait_for(
                self.reader.readexactly(NPLTMessage.HEADER_SIZE),
                timeout=self.heartbeat_interval + 10
            )

            # 解码头部获取数据长度
            type_val, seq, length = NPLTMessage.decode_header(header)

            # 读取数据部分
            if length > 0:
                data = await asyncio.wait_for(
                    self.reader.readexactly(length),
                    timeout=5.0
                )
            else:
                data = b""

            # 组装完整消息
            full_message = header + data

            # 解码消息
            message = NPLTMessage.decode(full_message)

            # 验证消息
            if not message.validate():
                self.ui.print_warning(f"收到无效消息")
                return None

            # 更新接收序列号
            self.recv_seq = (message.seq + 1) % 65536

            return message

        except asyncio.TimeoutError:
            # 超时，检查是否应该发送心跳
            await self.send_heartbeat()
            return None

        except Exception as e:
            self.ui.print_error(f"接收消息失败: {e}")
            self.connected = False
            return None

    async def send_heartbeat(self):
        """发送心跳"""
        await self.send_message(
            MessageType.CHAT_TEXT,
            b"HEARTBEAT"
        )

    async def start_message_loop(self):
        """启动消息接收循环"""
        while self.connected:
            try:
                message = await self.receive_message()

                if message is None:
                    continue

                # 处理消息
                await self._process_message(message)

            except Exception as e:
                self.ui.print_error(f"消息循环错误: {e}")
                break

    async def _process_message(self, message: NPLTMessage):
        """处理消息

        Args:
            message: NPLT 消息
        """
        try:
            if message.type == MessageType.CHAT_TEXT:
                # 聊天文本消息
                text = message.data.decode('utf-8', errors='ignore')

                # 忽略心跳
                if text == "HEARTBEAT":
                    return

                # 显示消息
                self.ui.print_message("assistant", text)

                # 调用消息处理器
                if self.message_handler:
                    await self.message_handler(message)

            elif message.type == MessageType.AGENT_THOUGHT:
                # Agent 思考过程
                text = message.data.decode('utf-8', errors='ignore')
                self.logger.debug(f"收到 Agent 思考: {text[:50]}...")
                self.ui.print_agent_thought(text)

            elif message.type == MessageType.DOWNLOAD_OFFER:
                # 下载提议
                self.ui.print_info("服务器提议下载文件")
                # TODO: 实现下载逻辑

            else:
                self.ui.print_warning(f"未知消息类型: {message.type}")

        except Exception as e:
            self.ui.print_error(f"处理消息失败: {e}")

    async def send_chat(self, text: str) -> bool:
        """发送聊天消息

        Args:
            text: 聊天文本

        Returns:
            是否发送成功
        """
        return await self.send_message(
            MessageType.CHAT_TEXT,
            text.encode('utf-8')
        )

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected and self.writer is not None


# 添加 decode_header 方法到 NPLTMessage
def _decode_header_helper():
    """为 NPLTMessage 添加 decode_header 辅助方法"""
    import struct

    def decode_header(cls, data: bytes):
        """解码头部获取 Type, Seq, Len"""
        type_val, seq, length = struct.unpack(
            cls.HEADER_FORMAT,
            data[:cls.HEADER_SIZE]
        )
        return type_val, seq, length

    NPLTMessage.decode_header = classmethod(decode_header)


_decode_header_helper()
