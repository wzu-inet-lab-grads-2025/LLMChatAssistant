# NPLT Protocol - Client Copy
PROTOCOL_VERSION = "1.0"

"""
NPLT 协议实现

NPLT (Network Protocol for LLM Transport) 是一个轻量级的二进制应用层协议，
用于在客户端和服务器之间传输实时聊天消息、Agent 思考过程和文件传输提议。

协议格式（v2）：
+--------+--------+--------+----------+
| Type   | Seq    | Len    | Data     |
| 1 Byte | 2 Bytes| 2 Bytes| <=64KB   |
+--------+--------+--------+----------+

注：v1 协议使用 1 字节长度字段（最大 255 字节），v2 扩展为 2 字节（最大 65535 字节）
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
    MODEL_SWITCH = 0x0F       # 模型切换请求
    HISTORY_REQUEST = 0x10    # 历史记录请求
    CLEAR_REQUEST = 0x11      # 清空会话请求
    SESSION_LIST = 0x14       # 会话列表请求
    SESSION_SWITCH = 0x15     # 切换会话
    SESSION_NEW = 0x16        # 创建新会话
    SESSION_DELETE = 0x17     # 删除会话


@dataclass
class NPLTMessage:
    """NPLT 协议消息"""
    type: MessageType
    seq: int
    data: bytes

    MAX_DATA_LENGTH = 65535  # uint16 最大值
    HEADER_FORMAT = ">BHH"  # uint8, uint16, uint16 (大端序)
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
