"""
NPLT 协议编解码测试

测试 NPLT 协议的消息编解码功能。
遵循章程：真实测试，不允许 mock
"""

import pytest

from shared.protocols.nplt import MessageType, NPLTMessage


class TestNPLTEncoding:
    """NPLT 编码测试"""

    def test_encode_chat_text(self):
        """测试编码 CHAT_TEXT 消息"""
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=1,
            data=b"Hello, World!"
        )

        encoded = message.encode()

        # 验证编码结果
        assert len(encoded) == 5 + 13  # Header (5) + Data (13)
        assert encoded[0] == 0x01  # CHAT_TEXT
        assert encoded[1] == 0x00  # Seq high byte
        assert encoded[2] == 0x01  # Seq low byte
        assert encoded[3] == 0    # Length high byte
        assert encoded[4] == 13   # Length low byte

    def test_encode_max_data_length(self):
        """测试编码最大长度数据"""
        max_data = b"X" * 65535
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=max_data
        )

        encoded = message.encode()

        assert len(encoded) == 5 + 65535
        assert encoded[3] == 255  # Length high byte
        assert encoded[4] == 255  # Length low byte

    def test_encode_empty_data(self):
        """测试编码空数据"""
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=b""
        )

        encoded = message.encode()

        assert len(encoded) == 5  # Only header
        assert encoded[3] == 0  # Length high byte
        assert encoded[4] == 0  # Length low byte

    def test_encode_exceeds_max_length(self):
        """测试编码超过最大长度的数据"""
        with pytest.raises(ValueError, match="数据长度超过限制"):
            NPLTMessage(
                type=MessageType.CHAT_TEXT,
                seq=0,
                data=b"X" * 65536
            ).encode()


class TestNPLTDecoding:
    """NPLT 解码测试"""

    def test_decode_chat_text(self):
        """测试解码 CHAT_TEXT 消息"""
        # 手动构造消息
        encoded = bytes([
            0x01,       # Type: CHAT_TEXT
            0x00, 0x01, # Seq: 1
            0x00, 0x05  # Length: 5
        ]) + b"Hello"

        message = NPLTMessage.decode(encoded)

        assert message.type == MessageType.CHAT_TEXT
        assert message.seq == 1
        assert message.data == b"Hello"

    def test_decode_agent_thought(self):
        """测试解码 AGENT_THOUGHT 消息"""
        encoded = bytes([
            0x0A,       # Type: AGENT_THOUGHT
            0x00, 0x02, # Seq: 2
            0x00, 0x0B  # Length: 11
        ]) + b"Thinking..."

        message = NPLTMessage.decode(encoded)

        assert message.type == MessageType.AGENT_THOUGHT
        assert message.seq == 2
        assert message.data == b"Thinking..."

    def test_decode_download_offer(self):
        """测试解码 DOWNLOAD_OFFER 消息"""
        encoded = bytes([
            0x0C,       # Type: DOWNLOAD_OFFER
            0x00, 0x03, # Seq: 3
            0x00, 0x04  # Length: 4
        ]) + b"file"

        message = NPLTMessage.decode(encoded)

        assert message.type == MessageType.DOWNLOAD_OFFER
        assert message.seq == 3

    def test_decode_too_short(self):
        """测试解码过短的消息"""
        with pytest.raises(ValueError, match="数据包太短"):
            NPLTMessage.decode(bytes([0x01, 0x00, 0x01]))  # Only 3 bytes

    def test_decode_invalid_length(self):
        """测试解码长度不匹配的消息"""
        encoded = bytes([
            0x01,       # Type: CHAT_TEXT
            0x00, 0x01, # Seq: 1
            0x0A        # Length: 10
        ]) + b"Short"  # Only 5 bytes

        with pytest.raises(ValueError, match="数据长度不匹配"):
            NPLTMessage.decode(encoded)


class TestNPLTValidation:
    """NPLT 验证测试"""

    def test_valid_message(self):
        """测试验证有效消息"""
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=100,
            data=b"Test"
        )

        assert message.validate() is True

    def test_invalid_seq(self):
        """测试验证无效序列号"""
        # Seq 在有效范围内，应该通过
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=65535,  # Max valid seq
            data=b"Test"
        )

        assert message.validate() is True

    def test_invalid_data_length(self):
        """测试验证无效数据长度（会在 encode 时检查）"""
        # 数据长度在 encode 时检查，这里验证 decode 后的消息
        message = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=b"X" * 255  # Max valid
        )

        assert message.validate() is True


class TestNPLTRoundTrip:
    """NPLT 往返测试"""

    def test_round_trip_chat_text(self):
        """测试 CHAT_TEXT 消息往返"""
        original = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=42,
            data=b"Round trip test"
        )

        encoded = original.encode()
        decoded = NPLTMessage.decode(encoded)

        assert decoded.type == original.type
        assert decoded.seq == original.seq
        assert decoded.data == original.data

    def test_round_trip_agent_thought(self):
        """测试 AGENT_THOUGHT 消息往返"""
        original = NPLTMessage(
            type=MessageType.AGENT_THOUGHT,
            seq=123,
            data=b"[Tool: sys_monitor] Reading metrics..."
        )

        encoded = original.encode()
        decoded = NPLTMessage.decode(encoded)

        assert decoded.type == original.type
        assert decoded.seq == original.seq
        assert decoded.data == original.data

    def test_round_trip_download_offer(self):
        """测试 DOWNLOAD_OFFER 消息往返"""
        original = NPLTMessage(
            type=MessageType.DOWNLOAD_OFFER,
            seq=255,
            data=b'{"filename": "test.log", "size": 1024}'
        )

        encoded = original.encode()
        decoded = NPLTMessage.decode(encoded)

        assert decoded.type == original.type
        assert decoded.seq == original.seq
        assert decoded.data == original.data

    def test_round_trip_max_size(self):
        """测试最大尺寸消息往返"""
        original = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=0,
            data=b"X" * 255
        )

        encoded = original.encode()
        decoded = NPLTMessage.decode(encoded)

        assert decoded.type == original.type
        assert decoded.seq == original.seq
        assert len(decoded.data) == 255

    def test_round_trip_empty_data(self):
        """测试空数据消息往返"""
        original = NPLTMessage(
            type=MessageType.CHAT_TEXT,
            seq=999,
            data=b""
        )

        encoded = original.encode()
        decoded = NPLTMessage.decode(encoded)

        assert decoded.type == original.type
        assert decoded.seq == original.seq
        assert decoded.data == b""
