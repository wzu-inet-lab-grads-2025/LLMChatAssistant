"""
RDT 协议编解码测试

测试 RDT 协议的数据包和 ACK 包编解码功能。
遵循章程：真实测试，不允许 mock
"""

import pytest

from shared.protocols.rdt import ACKPacket, RDTPacket


class TestRDTPacketEncoding:
    """RDT 数据包编码测试"""

    def test_encode_packet(self):
        """测试编码数据包"""
        packet = RDTPacket(
            seq=1,
            checksum=0,  # 将在 encode 中计算
            data=b"Hello"
        )

        encoded = packet.encode()

        # 验证编码结果
        assert len(encoded) == 4 + 5  # Header (4) + Data (5)
        assert encoded[0] == 0x00  # Seq high byte
        assert encoded[1] == 0x01  # Seq low byte

    def test_encode_max_data_length(self):
        """测试编码最大长度数据"""
        max_data = b"X" * 1024
        packet = RDTPacket(
            seq=0,
            checksum=0,
            data=max_data
        )

        encoded = packet.encode()

        assert len(encoded) == 4 + 1024

    def test_encode_empty_data(self):
        """测试编码空数据"""
        packet = RDTPacket(
            seq=0,
            checksum=0,
            data=b""
        )

        encoded = packet.encode()

        assert len(encoded) == 4  # Only header

    def test_encode_exceeds_max_length(self):
        """测试编码超过最大长度的数据"""
        with pytest.raises(ValueError, match="数据长度超过限制"):
            RDTPacket(
                seq=0,
                checksum=0,
                data=b"X" * 1025
            ).encode()

    def test_checksum_calculation(self):
        """测试校验和计算"""
        packet = RDTPacket(
            seq=1,
            checksum=0,
            data=b"Test data"
        )

        encoded = packet.encode()

        # 校验和应该在偏移 2-3 的位置
        checksum = (encoded[2] << 8) | encoded[3]
        assert checksum != 0  # 应该被计算


class TestRDTPacketDecoding:
    """RDT 数据包解码测试"""

    def test_decode_packet(self):
        """测试解码数据包"""
        # 创建一个包并编码
        original = RDTPacket(
            seq=5,
            checksum=0,
            data=b"TestData"
        )
        encoded = original.encode()

        # 解码
        decoded = RDTPacket.decode(encoded)

        assert decoded.seq == 5
        assert decoded.data == b"TestData"
        # 注意：checksum 会被重新计算

    def test_decode_max_size(self):
        """测试解码最大尺寸数据包"""
        original = RDTPacket(
            seq=0,
            checksum=0,
            data=b"X" * 1024
        )
        encoded = original.encode()

        decoded = RDTPacket.decode(encoded)

        assert len(decoded.data) == 1024

    def test_decode_too_short(self):
        """测试解码过短的数据包"""
        with pytest.raises(ValueError, match="数据包太短"):
            RDTPacket.decode(bytes([0x00, 0x01]))  # Only 2 bytes

    def test_decode_exceeds_max_length(self):
        """测试解码超过最大长度的数据"""
        # 构造一个声明长度超过限制的数据包
        invalid_packet = bytes([
            0x00, 0x01,  # Seq: 1
            0x00, 0x00,  # Checksum
        ]) + b"X" * 1025  # Too much data

        with pytest.raises(ValueError, match="数据长度超过限制"):
            RDTPacket.decode(invalid_packet)


class TestRDTPacketValidation:
    """RDT 数据包验证测试"""

    def test_validate_valid_packet(self):
        """测试验证有效数据包"""
        packet = RDTPacket(
            seq=10,
            checksum=0,
            data=b"Valid data"
        )

        # 编码会计算校验和
        encoded = packet.encode()
        decoded = RDTPacket.decode(encoded)

        # 验证应该通过
        assert decoded.validate() is True

    def test_validate_invalid_checksum(self):
        """测试验证无效校验和"""
        packet = RDTPacket(
            seq=1,
            checksum=0xFFFF,  # 错误的校验和
            data=b"Test"
        )

        # 手动构造包以使用错误的校验和
        import struct
        header = struct.pack(
            RDTPacket.HEADER_FORMAT,
            1,          # Seq
            0xFFFF      # 错误的 Checksum
        )
        encoded = header + b"Test"

        decoded = RDTPacket.decode(encoded)

        # 验证应该失败
        assert decoded.validate() is False


class TestACKPacket:
    """ACK 包测试"""

    def test_encode_ack(self):
        """测试编码 ACK 包"""
        ack = ACKPacket(
            seq=5,
            checksum=0
        )

        encoded = ack.encode()

        assert len(encoded) == 4  # Fixed size
        assert encoded[0] == 0x00  # Seq high byte
        assert encoded[1] == 0x05  # Seq low byte

    def test_decode_ack(self):
        """测试解码 ACK 包"""
        original = ACKPacket(seq=10, checksum=0)
        encoded = original.encode()

        decoded = ACKPacket.decode(encoded)

        assert decoded.seq == 10

    def test_ack_checksum(self):
        """测试 ACK 包校验和计算"""
        ack = ACKPacket(seq=1, checksum=0)
        encoded = ack.encode()

        # 校验和应该被计算
        checksum = (encoded[2] << 8) | encoded[3]
        assert checksum != 0

    def test_validate_valid_ack(self):
        """测试验证有效 ACK 包"""
        ack = ACKPacket(seq=5, checksum=0)
        encoded = ack.encode()
        decoded = ACKPacket.decode(encoded)

        assert decoded.validate() is True

    def test_validate_invalid_ack(self):
        """测试验证无效 ACK 包"""
        # 手动构造错误的 ACK
        import struct
        invalid_ack = struct.pack(
            ACKPacket.HEADER_FORMAT,
            5,          # Seq
            0xFFFF      # 错误的 Checksum
        )

        decoded = ACKPacket.decode(invalid_ack)

        assert decoded.validate() is False


class TestRDTRoundTrip:
    """RDT 往返测试"""

    def test_round_trip_data_packet(self):
        """测试数据包往返"""
        original = RDTPacket(
            seq=42,
            checksum=0,
            data=b"Round trip test data"
        )

        encoded = original.encode()
        decoded = RDTPacket.decode(encoded)

        assert decoded.seq == original.seq
        assert decoded.data == original.data
        assert decoded.validate() is True

    def test_round_trip_ack(self):
        """测试 ACK 包往返"""
        original = ACKPacket(seq=100, checksum=0)

        encoded = original.encode()
        decoded = ACKPacket.decode(encoded)

        assert decoded.seq == original.seq
        assert decoded.validate() is True

    def test_round_trip_max_size(self):
        """测试最大尺寸数据包往返"""
        original = RDTPacket(
            seq=999,
            checksum=0,
            data=b"X" * 1024
        )

        encoded = original.encode()
        decoded = RDTPacket.decode(encoded)

        assert len(decoded.data) == 1024
        assert decoded.validate() is True

    def test_round_trip_empty_data(self):
        """测试空数据往返"""
        original = RDTPacket(seq=0, checksum=0, data=b"")

        encoded = original.encode()
        decoded = RDTPacket.decode(encoded)

        assert len(decoded.data) == 0
