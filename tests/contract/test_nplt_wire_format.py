"""
NPLT 协议字节格式测试

验证 NPLT 协议的字节格式与规范文档一致。
遵循章程：真实测试，验证协议规范一致性
"""

import struct

import pytest

from src.protocols.nplt import MessageType, NPLTMessage


class TestNPLTHeaderFormat:
    """NPLT 头部格式测试"""

    def test_header_size(self):
        """测试头部大小为 4 字节"""
        # Type (1) + Seq (2) + Len (1) = 4 bytes
        assert NPLTMessage.HEADER_SIZE == 4

    def test_header_format_string(self):
        """测试头部格式字符串"""
        # >BHB: big-endian uint8, uint16, uint8
        expected_format = ">BHB"
        assert NPLTMessage.HEADER_FORMAT == expected_format

    def test_header_unpacking(self):
        """测试头部解包"""
        # 构造有效头部
        header_bytes = bytes([0x01, 0x00, 0x01, 0x0B])  # CHAT_TEXT, Seq=1, Len=11

        type_val, seq, length = struct.unpack(
            NPLTMessage.HEADER_FORMAT,
            header_bytes
        )

        assert type_val == 0x01
        assert seq == 1
        assert length == 11

    def test_type_field_position(self):
        """测试 Type 字段位置"""
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=b"test"
        )
        encoded = message.encode()

        # Type 应该在第 0 字节
        assert encoded[0] == MessageType.CHAT_TEXT

    def test_seq_field_position(self):
        """测试 Seq 字段位置"""
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0x1234,
            data=b"test"
        )
        encoded = message.encode()

        # Seq 应该在第 1-2 字节（大端序）
        seq_bytes = encoded[1:3]
        unpacked_seq = struct.unpack(">H", seq_bytes)[0]
        assert unpacked_seq == 0x1234

    def test_len_field_position(self):
        """测试 Len 字段位置"""
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=b"test"
        )
        encoded = message.encode()

        # Len 应该在第 3 字节
        assert encoded[3] == 4


class TestNPLTByteOrder:
    """NPLT 字节序测试"""

    def test_seq_big_endian(self):
        """测试 Seq 使用大端序"""
        # Seq = 0x1234 应该编码为 0x12 0x34
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0x1234,
            data=b""
        )
        encoded = message.encode()

        # 验证大端序
        assert encoded[1] == 0x12  # 高字节在前
        assert encoded[2] == 0x34  # 低字节在后

    def test_seq_maximum_value(self):
        """测试 Seq 最大值 (0xFFFF = 65535)"""
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=65535,
            data=b"max seq"
        )
        encoded = message.encode()

        # 验证编码
        assert encoded[1] == 0xFF
        assert encoded[2] == 0xFF

    def test_seq_minimum_value(self):
        """测试 Seq 最小值 (0)"""
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=b"min seq"
        )
        encoded = message.encode()

        # 验证编码
        assert encoded[1] == 0x00
        assert encoded[2] == 0x00


class TestNPLTDataLength:
    """NPLT 数据长度测试"""

    def test_max_data_length(self):
        """测试最大数据长度为 255 字节"""
        assert NPLTMessage.MAX_DATA_LENGTH == 255

    def test_len_field_max_value(self):
        """测试 Len 字段最大值"""
        max_data = b"X" * 255
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=max_data
        )
        encoded = message.encode()

        # Len 字节应该等于 255
        assert encoded[3] == 255

    def test_total_packet_size_max(self):
        """测试最大数据包大小"""
        max_data = b"X" * 255
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=max_data
        )
        encoded = message.encode()

        # 总大小 = Header (4) + Data (255) = 259 bytes
        assert len(encoded) == 259

    def test_total_packet_size_min(self):
        """测试最小数据包大小"""
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=b""
        )
        encoded = message.encode()

        # 总大小 = Header (4) + Data (0) = 4 bytes
        assert len(encoded) == 4


class TestNPLTMessageTypes:
    """NPLT 消息类型测试"""

    def test_chat_text_type_value(self):
        """测试 CHAT_TEXT 类型值"""
        assert MessageType.CHAT_TEXT == 0x01

    def test_agent_thought_type_value(self):
        """测试 AGENT_THOUGHT 类型值"""
        assert MessageType.AGENT_THOUGHT == 0x0A

    def test_download_offer_type_value(self):
        """测试 DOWNLOAD_OFFER 类型值"""
        assert MessageType.DOWNLOAD_OFFER == 0x0C

    def test_type_field_size(self):
        """测试 Type 字段大小为 1 字节"""
        # Type 是 uint8 (1 字节)
        assert isinstance(MessageType.CHAT_TEXT, int)
        assert MessageType.CHAT_TEXT < 256

    def test_all_type_values_unique(self):
        """测试所有类型值唯一"""
        type_values = [
            MessageType.CHAT_TEXT,
            MessageType.AGENT_THOUGHT,
            MessageType.DOWNLOAD_OFFER
        ]

        assert len(type_values) == len(set(type_values))


class TestNPLTMessageValidation:
    """NPLT 消息验证测试"""

    def test_valid_seq_range(self):
        """测试有效 Seq 范围 (0-65535)"""
        # 最小值
        msg1 = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=b""
        )
        assert msg1.validate() is True

        # 最大值
        msg2 = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=65535,
            data=b""
        )
        assert msg2.validate() is True

    def test_data_length_validation(self):
        """测试数据长度验证"""
        # 有效长度
        msg1 = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=b"X" * 255
        )
        assert msg1.validate() is True

    def test_message_validation_in_encode(self):
        """测试编码时验证数据长度"""
        # 编码方法会验证数据长度
        with pytest.raises(ValueError, match="数据长度超过限制"):
            NPLTMessage(
                type=MessageType.CHAT_TEXT,
                seq=0,
                data=b"X" * 256  # 超过限制
            ).encode()
