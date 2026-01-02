"""
RDT 服务器模块

实现 RDT 可靠文件传输的发送方，支持滑动窗口和超时重传。
遵循章程：真实实现，不允许虚假实现或占位符
"""

import asyncio
import hashlib
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from protocols.rdt import ACKPacket, RDTPacket


class RDTState(Enum):
    """RDT 传输状态"""
    IDLE = "idle"
    WAITING_ACK = "waiting_ack"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RDTSession:
    """RDT 传输会话"""

    session_id: str                 # 会话 ID
    filename: str                   # 文件名
    file_size: int                  # 文件大小
    download_token: str             # 下载令牌
    state: RDTState                 # 传输状态
    window_size: int = 5            # 滑动窗口大小
    send_base: int = 0              # 发送基序列号
    next_seq: int = 0               # 下一个序列号
    packets: Dict[int, RDTPacket] = field(default_factory=dict)  # 已发送包
    acked_packets: set = field(default_factory=set)  # 已确认包
    timeout_start: Optional[float] = None  # 超时计时起点
    timeout_duration: float = 0.1   # 超时时间（秒）

    # 文件数据
    file_data: Optional[bytes] = None
    checksum: str = ""              # 文件校验和

    def can_send(self) -> bool:
        """检查是否可以发送新包"""
        return self.next_seq < self.send_base + self.window_size

    def is_complete(self) -> bool:
        """检查传输是否完成"""
        if not self.file_data:
            return False
        total_packets = math.ceil(len(self.file_data) / RDTPacket.MAX_DATA_LENGTH)
        return len(self.acked_packets) >= total_packets

    def start_timeout_timer(self):
        """启动超时计时器（仅对 SendBase 计时）"""
        if self.send_base < self.next_seq:
            self.timeout_start = asyncio.get_event_loop().time()

    def is_timeout(self) -> bool:
        """检查是否超时"""
        if self.timeout_start is None:
            return False
        elapsed = asyncio.get_event_loop().time() - self.timeout_start
        return elapsed >= self.timeout_duration

    def slide_window(self, ack_seq: int):
        """滑动窗口

        Args:
            ack_seq: 确认的序列号
        """
        # 更新已确认包
        for seq in range(self.send_base, ack_seq + 1):
            self.acked_packets.add(seq)

        # 滑动窗口
        if ack_seq >= self.send_base:
            self.send_base = ack_seq + 1

        # 重置超时计时器
        if self.send_base < self.next_seq:
            self.start_timeout_timer()
        else:
            self.timeout_start = None


@dataclass
class RDTServer:
    """RDT 服务器（发送方）"""

    host: str = "0.0.0.0"
    port: int = 9998  # UDP 端口
    window_size: int = 5
    timeout: float = 0.1  # 超时时间（秒）

    # 内部状态
    sessions: Dict[str, RDTSession] = field(default_factory=dict)
    transport: Optional[asyncio.DatagramTransport] = None
    protocol: Optional[asyncio.DatagramProtocol] = None
    running: bool = False

    async def start(self):
        """启动 RDT 服务器"""
        loop = asyncio.get_event_loop()

        # 创建 UDP endpoint
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: RDTServerProtocol(self),
            local_addr=(self.host, self.port)
        )

        self.running = True
        print(f"[INFO] [RDT] RDT 服务器启动在 {self.host}:{self.port}")

    async def stop(self):
        """停止 RDT 服务器"""
        self.running = False

        # 关闭所有会话
        self.sessions.clear()

        # 关闭传输
        if self.transport:
            self.transport.close()

        print("[INFO] [RDT] RDT 服务器已停止")

    def create_session(
        self,
        filename: str,
        file_data: bytes,
        client_addr: Tuple[str, int]
    ) -> str:
        """创建 RDT 传输会话

        Args:
            filename: 文件名
            file_data: 文件数据
            client_addr: 客户端地址

        Returns:
            下载令牌
        """
        # 计算校验和
        checksum = hashlib.md5(file_data).hexdigest()

        # 创建会话
        session_id = str(uuid.uuid4())
        download_token = str(uuid.uuid4())

        session = RDTSession(
            session_id=session_id,
            filename=filename,
            file_size=len(file_data),
            download_token=download_token,
            state=RDTState.WAITING_ACK,
            window_size=self.window_size,
            timeout_duration=self.timeout,
            file_data=file_data,
            checksum=checksum
        )

        self.sessions[download_token] = session

        print(f"[INFO] [RDT] 创建传输会话: {filename} ({len(file_data)} 字节)")

        return download_token

    async def send_file(self, download_token: str, client_addr: Tuple[str, int]) -> bool:
        """发送文件

        Args:
            download_token: 下载令牌
            client_addr: 客户端地址

        Returns:
            是否成功
        """
        session = self.sessions.get(download_token)
        if not session:
            print(f"[ERROR] [RDT] 会话不存在: {download_token}")
            return False

        if not session.file_data:
            print(f"[ERROR] [RDT] 文件数据不存在")
            return False

        session.state = RDTState.SENDING

        try:
            # 分片文件
            data = session.file_data
            chunk_size = RDTPacket.MAX_DATA_LENGTH
            total_chunks = math.ceil(len(data) / chunk_size)

            print(f"[INFO] [RDT] 开始发送文件: {session.filename} ({total_chunks} 个包)")

            # 发送数据包
            while not session.is_complete() and session.state != RDTState.FAILED:
                # 检查超时
                if session.is_timeout():
                    print(f"[WARN] [RDT] 超时，重传包 {session.send_base}")
                    # 重传 SendBase 包
                    if session.send_base in session.packets:
                        packet = session.packets[session.send_base]
                        await self._send_packet(packet, client_addr)
                        session.start_timeout_timer()

                # 发送新包（如果窗口允许）
                while session.can_send() and session.next_seq < total_chunks:
                    # 计算分片
                    start = session.next_seq * chunk_size
                    end = min(start + chunk_size, len(data))
                    chunk = data[start:end]

                    # 创建数据包
                    packet = RDTPacket(
                        seq=session.next_seq,
                        checksum=0,  # 将在 encode 中计算
                        data=chunk
                    )

                    # 编码并发送
                    await self._send_packet(packet, client_addr)

                    # 保存包
                    session.packets[session.next_seq] = packet
                    session.next_seq += 1

                    # 如果是第一个包，启动超时计时器
                    if session.send_base == session.next_seq - 1:
                        session.start_timeout_timer()

                    print(f"[DEBUG] [RDT] 发送包 {packet.seq}/{total_chunks}")

                # 等待 ACK 或超时
                await asyncio.sleep(0.01)

            # 传输完成
            session.state = RDTState.COMPLETED
            print(f"[INFO] [RDT] 文件发送完成: {session.filename}")
            return True

        except Exception as e:
            print(f"[ERROR] [RDT] 发送文件失败: {e}")
            session.state = RDTState.FAILED
            return False

    async def _send_packet(self, packet: RDTPacket, addr: Tuple[str, int]):
        """发送数据包

        Args:
            packet: RDT 数据包
            addr: 目标地址
        """
        if not self.transport:
            raise RuntimeError("RDT 服务器未启动")

        # 编码数据包
        encoded = packet.encode()

        # 发送
        self.transport.sendto(encoded, addr)

    def handle_ack(self, data: bytes, addr: Tuple[str, int]):
        """处理 ACK 包

        Args:
            data: ACK 数据
            addr: 发送方地址
        """
        try:
            # 解码 ACK 包
            ack = ACKPacket.decode(data)

            # 验证 ACK 包
            if not ack.validate():
                print(f"[WARN] [RDT] 无效 ACK 包")
                return

            # 查找会话
            for token, session in self.sessions.items():
                if session.state in [RDTState.SENDING, RDTState.WAITING_ACK]:
                    # 滑动窗口
                    if ack.seq >= session.send_base:
                        old_base = session.send_base
                        session.slide_window(ack.seq)
                        print(f"[DEBUG] [RDT] 收到 ACK={ack.seq}, 窗口滑动: {old_base} -> {session.send_base}")

        except Exception as e:
            print(f"[ERROR] [RDT] 处理 ACK 失败: {e}")


class RDTServerProtocol(asyncio.DatagramProtocol):
    """RDT 服务器协议"""

    def __init__(self, server: RDTServer):
        self.server = server

    def connection_made(self, transport):
        """连接建立"""
        self.transport = transport

    def datagram_received(self, data, addr):
        """接收数据报"""
        # 判断是 ACK 包还是数据包
        if len(data) == ACKPacket.HEADER_SIZE:
            # ACK 包
            self.server.handle_ack(data, addr)
        else:
            # 数据包（不应该收到）
            print(f"[WARN] [RDT] 收到数据包（服务器仅发送）")

    def error_received(self, exc):
        """接收错误"""
        print(f"[ERROR] [RDT] 接收错误: {exc}")
