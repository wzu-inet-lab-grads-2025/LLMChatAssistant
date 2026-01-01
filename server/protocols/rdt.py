# RDT Protocol - Server Copy
PROTOCOL_VERSION = "1.0"

"""
RDT 协议实现

RDT (Reliable Data Transfer) 是一个基于滑动窗口的可靠数据传输协议，
运行在 UDP 之上，用于在不可靠的网络上传输文件。

协议格式：
+--------+--------+----------+
| Seq    | Check  | Data     |
| 2 Bytes| 2 Bytes| <=1024 Bytes|
+--------+--------+----------+
"""

import struct
import zlib
from dataclasses import dataclass
from typing import Optional


def crc16(data: bytes) -> int:
    """
    计算 CRC16 校验和

    Args:
        data: 待计算的数据

    Returns:
        CRC16 校验和
    """
    # 使用 zlib 的 crc32 模拟 CRC16（取低 16 位）
    return zlib.crc32(data) & 0xFFFF


@dataclass
class RDTPacket:
    """RDT 数据包"""
    seq: int
    checksum: int
    data: bytes

    MAX_DATA_LENGTH = 1024
    HEADER_FORMAT = ">HH"  # uint16, uint16 (大端序)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def encode(self) -> bytes:
        """
        编码为字节流

        Returns:
            编码后的字节流

        Raises:
            ValueError: 如果数据长度超过限制
        """
        if len(self.data) > self.MAX_DATA_LENGTH:
            raise ValueError(
                f"数据长度超过限制：{len(self.data)} > {self.MAX_DATA_LENGTH}"
            )

        # 计算校验和（包含 seq 和 data）
        data_to_checksum = struct.pack(">H", self.seq) + self.data
        computed_checksum = crc16(data_to_checksum)

        # 编码头部
        header = struct.pack(
            self.HEADER_FORMAT,
            self.seq,
            computed_checksum
        )

        return header + self.data

    @classmethod
    def decode(cls, data: bytes) -> 'RDTPacket':
        """
        从字节流解码

        Args:
            data: 字节流

        Returns:
            解码后的 RDTPacket

        Raises:
            ValueError: 如果数据格式错误
        """
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(
                f"数据包太短：{len(data)} < {cls.HEADER_SIZE}"
            )

        # 解码头部
        seq, checksum = struct.unpack(
            cls.HEADER_FORMAT,
            data[:cls.HEADER_SIZE]
        )

        # 提取数据
        payload = data[cls.HEADER_SIZE:]

        if len(payload) > cls.MAX_DATA_LENGTH:
            raise ValueError(
                f"数据长度超过限制：{len(payload)} > {cls.MAX_DATA_LENGTH}"
            )

        return cls(
            seq=seq,
            checksum=checksum,
            data=payload
        )

    def validate(self) -> bool:
        """
        验证数据包校验和

        Returns:
            校验和是否有效
        """
        # 计算校验和
        data_to_checksum = struct.pack(">H", self.seq) + self.data
        computed_checksum = crc16(data_to_checksum)

        return self.checksum == computed_checksum

    def __str__(self) -> str:
        """字符串表示（用于调试）"""
        return f"RDTPacket(seq={self.seq}, checksum={self.checksum:04x}, data_len={len(self.data)})"


@dataclass
class ACKPacket:
    """ACK 确认包"""
    seq: int  # 确认的序列号（表示已收到此序列号及之前的所有包）
    checksum: int

    HEADER_FORMAT = ">HH"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def encode(self) -> bytes:
        """编码为字节流"""
        # 计算 ACK 包的校验和
        data_to_checksum = struct.pack(">H", self.seq)
        computed_checksum = crc16(data_to_checksum)

        return struct.pack(
            self.HEADER_FORMAT,
            self.seq,
            computed_checksum
        )

    @classmethod
    def decode(cls, data: bytes) -> 'ACKPacket':
        """从字节流解码"""
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(
                f"ACK 包太短：{len(data)} < {cls.HEADER_SIZE}"
            )

        seq, checksum = struct.unpack(
            cls.HEADER_FORMAT,
            data[:cls.HEADER_SIZE]
        )

        return cls(seq=seq, checksum=checksum)

    def validate(self) -> bool:
        """验证 ACK 包校验和"""
        data_to_checksum = struct.pack(">H", self.seq)
        computed_checksum = crc16(data_to_checksum)
        return self.checksum == computed_checksum

    def __str__(self) -> str:
        """字符串表示（用于调试）"""
        return f"ACKPacket(seq={self.seq}, checksum={self.checksum:04x})"
