"""
RDT 客户端模块

实现 RDT 可靠文件传输的接收方，支持滑动窗口和 ACK 发送。
遵循章程：真实实现，不允许虚假实现或占位符
"""

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set

from clients.cli.protocols.rdt import ACKPacket, RDTPacket


class RDTClientState(Enum):
    """RDT 客户端状态"""
    IDLE = "idle"
    RECEIVING = "receiving"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RDTClientSession:
    """RDT 客户端会话"""

    download_token: str             # 下载令牌
    filename: str                   # 文件名
    file_size: int                  # 文件大小
    expected_checksum: str          # 预期的文件校验和
    state: RDTClientState           # 接收状态

    # 接收窗口
    window_size: int = 5            # 接收窗口大小
    expected_seq: int = 0           # 期望的序列号
    received_packets: Dict[int, bytes] = field(default_factory=dict)  # 已接收包
    acked_seqs: Set[int] = field(default_factory=set)  # 已确认序列号

    # 统计信息
    total_packets: int = 0          # 总包数
    received_count: int = 0         # 已接收包数
    duplicate_count: int = 0        # 重复包数

    def add_packet(self, seq: int, data: bytes) -> bool:
        """添加数据包

        Args:
            seq: 序列号
            data: 数据

        Returns:
            是否为新包
        """
        if seq in self.received_packets:
            # 重复包
            self.duplicate_count += 1
            return False

        self.received_packets[seq] = data
        self.received_count += 1
        return True

    def get_next_expected_seq(self) -> int:
        """获取下一个期望的序列号"""
        # 找到第一个缺失的序列号
        seq = self.expected_seq
        while seq in self.received_packets:
            seq += 1
        return seq

    def is_complete(self) -> bool:
        """检查接收是否完成"""
        if not self.file_size:
            return False

        # 计算总包数
        total_packets = (self.file_size + RDTPacket.MAX_DATA_LENGTH - 1) // RDTPacket.MAX_DATA_LENGTH

        # 检查是否收到所有包
        return len(self.received_packets) >= total_packets

    def assemble_file(self) -> bytes:
        """组装文件数据

        Returns:
            完整的文件数据

        Raises:
            ValueError: 如果数据不完整
        """
        if not self.is_complete():
            raise ValueError("数据不完整，无法组装文件")

        # 按序列号排序并组装
        sorted_seqs = sorted(self.received_packets.keys())
        chunks = [self.received_packets[seq] for seq in sorted_seqs]

        return b''.join(chunks)

    def verify_checksum(self) -> bool:
        """验证文件校验和

        Returns:
            校验和是否匹配
        """
        try:
            file_data = self.assemble_file()
            computed_checksum = hashlib.md5(file_data).hexdigest()
            return computed_checksum == self.expected_checksum
        except ValueError:
            return False


@dataclass
class RDTClient:
    """RDT 客户端（接收方）"""

    server_host: str = "127.0.0.1"
    server_port: int = 9998  # UDP 端口
    window_size: int = 5

    # 内部状态
    sessions: Dict[str, RDTClientSession] = field(default_factory=dict)
    transport: Optional[asyncio.DatagramTransport] = None
    protocol: Optional[asyncio.DatagramProtocol] = None
    running: bool = False
    server_addr: Optional[tuple] = None

    async def start(self):
        """启动 RDT 客户端"""
        loop = asyncio.get_event_loop()

        # 创建 UDP endpoint
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: RDTClientProtocol(self),
            local_addr=('0.0.0.0', 0)  # 自动分配端口
        )

        self.running = True
        self.server_addr = (self.server_host, self.server_port)

        # 获取分配的端口
        local_port = self.transport.get_extra_info('sockname')[1]
        print(f"[INFO] [RDT] RDT 客户端启动在 0.0.0.0:{local_port}")

    async def stop(self):
        """停止 RDT 客户端"""
        self.running = False

        # 关闭所有会话
        self.sessions.clear()

        # 关闭传输
        if self.transport:
            self.transport.close()

        print("[INFO] [RDT] RDT 客户端已停止")

    def create_session(
        self,
        download_token: str,
        filename: str,
        file_size: int,
        expected_checksum: str
    ) -> RDTClientSession:
        """创建接收会话

        Args:
            download_token: 下载令牌
            filename: 文件名
            file_size: 文件大小
            expected_checksum: 预期的校验和

        Returns:
            RDTClientSession 实例
        """
        session = RDTClientSession(
            download_token=download_token,
            filename=filename,
            file_size=file_size,
            expected_checksum=expected_checksum,
            state=RDTClientState.RECEIVING,
            window_size=self.window_size
        )

        self.sessions[download_token] = session

        # 计算总包数
        total_packets = (file_size + RDTPacket.MAX_DATA_LENGTH - 1) // RDTPacket.MAX_DATA_LENGTH
        session.total_packets = total_packets

        print(f"[INFO] [RDT] 创建接收会话: {filename} ({file_size} 字节, {total_packets} 个包)")

        return session

    async def receive_file(self, download_token: str, timeout: float = 30.0) -> Optional[bytes]:
        """接收文件

        Args:
            download_token: 下载令牌
            timeout: 超时时间（秒）

        Returns:
            文件数据，失败返回 None
        """
        session = self.sessions.get(download_token)
        if not session:
            print(f"[ERROR] [RDT] 会话不存在: {download_token}")
            return None

        session.state = RDTClientState.RECEIVING

        try:
            # 等待接收完成
            start_time = asyncio.get_event_loop().time()

            while not session.is_complete() and session.state != RDTClientState.FAILED:
                # 检查超时
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    print(f"[ERROR] [RDT] 接收超时")
                    session.state = RDTClientState.FAILED
                    return None

                await asyncio.sleep(0.1)

            # 验证校验和
            if not session.verify_checksum():
                print(f"[ERROR] [RDT] 校验和不匹配")
                session.state = RDTClientState.FAILED
                return None

            # 组装文件
            file_data = session.assemble_file()
            session.state = RDTClientState.COMPLETED

            print(f"[INFO] [RDT] 文件接收完成: {session.filename}")
            print(f"[INFO] [RDT] 接收统计: {session.received_count}/{session.total_packets} 包, "
                  f"重复: {session.duplicate_count}")

            return file_data

        except Exception as e:
            print(f"[ERROR] [RDT] 接收文件失败: {e}")
            session.state = RDTClientState.FAILED
            return None

    def handle_packet(self, data: bytes, addr: tuple):
        """处理接收到的数据包

        Args:
            data: 数据包字节流
            addr: 发送方地址
        """
        try:
            # 解码数据包
            packet = RDTPacket.decode(data)

            # 验证数据包
            if not packet.validate():
                print(f"[WARN] [RDT] 无效数据包 (seq={packet.seq})")
                return

            # 查找会话（使用第一个活跃会话）
            session = None
            for s in self.sessions.values():
                if s.state == RDTClientState.RECEIVING:
                    session = s
                    break

            if not session:
                print(f"[WARN] [RDT] 无活跃会话")
                return

            # 添加数据包
            is_new = session.add_packet(packet.seq, packet.data)

            # 发送 ACK（累积确认）
            expected_seq = session.get_next_expected_seq()
            self._send_ack(expected_seq, addr)

            if is_new:
                print(f"[DEBUG] [RDT] 收到包 {packet.seq}/{session.total_packets}, "
                      f"发送 ACK={expected_seq}")

        except Exception as e:
            print(f"[ERROR] [RDT] 处理数据包失败: {e}")

    def _send_ack(self, seq: int, addr: tuple):
        """发送 ACK 包

        Args:
            seq: 确认的序列号
            addr: 目标地址
        """
        if not self.transport:
            raise RuntimeError("RDT 客户端未启动")

        # 创建 ACK 包
        ack = ACKPacket(seq=seq, checksum=0)  # checksum 将在 encode 中计算

        # 编码并发送
        encoded = ack.encode()
        self.transport.sendto(encoded, addr)


class RDTClientProtocol(asyncio.DatagramProtocol):
    """RDT 客户端协议"""

    def __init__(self, client: RDTClient):
        self.client = client

    def connection_made(self, transport):
        """连接建立"""
        self.transport = transport

    def datagram_received(self, data, addr):
        """接收数据报"""
        # 判断是 ACK 包还是数据包
        if len(data) > ACKPacket.HEADER_SIZE:
            # 数据包
            self.client.handle_packet(data, addr)
        else:
            # ACK 包（不应该收到）
            print(f"[WARN] [RDT] 收到 ACK 包（客户端仅接收）")

    def error_received(self, exc):
        """接收错误"""
        print(f"[ERROR] [RDT] 接收错误: {exc}")
