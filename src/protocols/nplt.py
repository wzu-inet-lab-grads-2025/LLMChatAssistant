"""
NPLT 协议实现

NPLT (Network Protocol for LLM Transport) 是一个轻量级的二进制应用层协议，
用于在客户端和服务器之间传输实时聊天消息、Agent 思考过程和文件传输提议。

协议格式：
+--------+--------+--------+----------+
| Type   | Seq    | Len    | Data     |
| 1 Byte | 2 Bytes| 1 Byte | <=255 Bytes|
+--------+--------+--------+----------+
"""

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class MessageType(IntEnum):
    """NPLT 消息类型"""
    CHAT_TEXT = 0x01          # 聊天文本
    AGENT_THOUGHT = 0x0A      # Agent 思考过程
    DOWNLOAD_OFFER = 0x0C     # 文件下载提议
    FILE_DATA = 0x0D          # 文件数据（上传/下载）
    FILE_METADATA = 0x0E      # 文件元数据（文件名、大小等）


@dataclass
class NPLTMessage:
    """NPLT 协议消息"""
    type: MessageType
    seq: int
    data: bytes

    MAX_DATA_LENGTH = 255
    HEADER_FORMAT = ">BHB"  # uint8, uint16, uint8 (大端序)
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

        # 编码头部
        header = struct.pack(
            self.HEADER_FORMAT,
            self.type,
            self.seq,
            len(self.data)
        )

        return header + self.data

    @classmethod
    def decode(cls, data: bytes) -> 'NPLTMessage':
        """
        从字节流解码

        Args:
            data: 字节流

        Returns:
            解码后的 NPLTMessage

        Raises:
            ValueError: 如果数据格式错误
        """
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(
                f"数据包太短：{len(data)} < {cls.HEADER_SIZE}"
            )

        # 解码头部
        type_val, seq, length = struct.unpack(
            cls.HEADER_FORMAT,
            data[:cls.HEADER_SIZE]
        )

        # 验证数据长度
        if len(data) < cls.HEADER_SIZE + length:
            raise ValueError(
                f"数据长度不匹配：期望 {length} 字节，实际 {len(data) - cls.HEADER_SIZE} 字节"
            )

        # 提取数据
        payload = data[cls.HEADER_SIZE:cls.HEADER_SIZE + length]

        return cls(
            type=MessageType(type_val),
            seq=seq,
            data=payload
        )

    def validate(self) -> bool:
        """验证消息格式"""
        return (
            0 <= self.seq < 65536 and
            len(self.data) <= self.MAX_DATA_LENGTH
        )

    def __str__(self) -> str:
        """字符串表示（用于调试）"""
        data_str = self.data.decode('utf-8', errors='replace')[:50]
        return f"NPLTMessage(type={self.type.name}, seq={self.seq}, data='{data_str}')"
