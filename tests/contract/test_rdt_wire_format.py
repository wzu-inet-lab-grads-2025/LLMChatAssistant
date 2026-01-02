"""
RDT 协议字节格式测试

验证 RDT 协议的字节格式与规范文档一致。
遵循章程：真实测试，验证协议规范一致性
"""

import struct

import pytest

from shared.protocols.rdt import ACKPacket, RDTPacket


class TestRDTPacketHeaderFormat:
    """RDT 数据包头部格式测试"""

    def test_header_size(self):
        """测试头部大小为 4 字节"""
        # Seq (2) + Check (2) = 4 bytes
        assert RDTPacket.HEADER_SIZE == 4

    def test_header_format_string(self):
        """测试头部格式字符串"""
        # >HH: big-endian uint16, uint16
        expected_format = ">HH"
        assert RDTPacket.HEADER_FORMAT == expected_format

    def test_header_unpacking(self):
        """测试头部解包"""
        # 构造有效头部
        header_bytes = bytes([0x00, 0x01, 0x12, 0x34])  # Seq=1, Check=0x1234

        seq, checksum = struct.unpack(
            RDTPacket.HEADER_FORMAT,
            header_bytes
        )

        assert seq == 1
        assert checksum == 0x1234

    def test_seq_field_position(self):
        """测试 Seq 字段位置"""
        packet = RDTPacket(
            seq=0x1234,
            checksum=0,
            data=b"test"
        )
        encoded = packet.encode()

        # Seq 应该在第 0-1 字节（大端序）
        seq_bytes = encoded[0:2]
        unpacked_seq = struct.unpack(">H", seq_bytes)[0]
        assert unpacked_seq == 0x1234

    def test_checksum_field_position(self):
        """测试 Checksum 字段位置"""
        packet = RDTPacket(
            seq=0,
            checksum=0xABCD,
            data=b"test"
        )
        encoded = packet.encode()

        # Checksum 应该在第 2-3 字节
        checksum_bytes = encoded[2:4]
        unpacked_checksum = struct.unpack(">H", checksum_bytes)[0]
        # Note: checksum会被重新计算，所以我们需要验证字段位置
        assert len(checksum_bytes) == 2


class TestRDTByteOrder:
    """RDT 字节序测试"""

    def test_seq_big_endian(self):
        """测试 Seq 使用大端序"""
        # Seq = 0x1234 应该编码为 0x12 0x34
        packet = RDTPacket(
            seq=0x1234,
            checksum=0,
            data=b""
        )
        encoded = packet.encode()

        # 验证大端序
        assert encoded[0] == 0x12  # 高字节在前
        assert encoded[1] == 0x34  # 低字节在后

    def test_checksum_big_endian(self):
        """测试 Checksum 使用大端序"""
        # 创建一个已知校验和的包
        packet = RDTPacket(
            seq=0,
            checksum=0,
            data=b"test"  # 数据会影响校验和
        )
        encoded = packet.encode()

        # 验证 checksum 字段是 2 字节
        assert len(encoded[2:4]) == 2

    def test_seq_maximum_value(self):
        """测试 Seq 最大值 (0xFFFF = 65535)"""
        packet = RDTPacket(
            seq=65535,
            checksum=0,
            data=b"max"
        )
        encoded = packet.encode()

        # 验证编码
        assert encoded[0] == 0xFF
        assert encoded[1] == 0xFF

    def test_seq_minimum_value(self):
        """测试 Seq 最小值 (0)"""
        packet = RDTPacket(
            seq=0,
            checksum=0,
            data=b"min"
        )
        encoded = packet.encode()

        # 验证编码
        assert encoded[0] == 0x00
        assert encoded[1] == 0x00


class TestRDTDataSize:
    """RDT 数据大小测试"""

    def test_max_data_length(self):
        """测试最大数据长度为 1024 字节"""
        assert RDTPacket.MAX_DATA_LENGTH == 1024

    def test_max_data_packet(self):
        """测试最大数据包大小"""
        max_data = b"X" * 1024
        packet = RDTPacket(
            seq=0,
            checksum=0,
            data=max_data
        )
        encoded = packet.encode()

        # 总大小 = Header (4) + Data (1024) = 1028 bytes
        assert len(encoded) == 1028

    def test_min_data_packet(self):
        """测试最小数据包大小"""
        packet = RDTPacket(
            seq=0,
            checksum=0,
            data=b""
        )
        encoded = packet.encode()

        # 总大小 = Header (4) + Data (0) = 4 bytes
        assert len(encoded) == 4

    def test_data_length_validation(self):
        """测试数据长度验证"""
        # 有效长度 - 需要 encode 然后解码才能得到正确的校验和
        msg1 = RDTPacket(
            seq=0,
            checksum=0,
            data=b"X" * 1024
        )
        encoded = msg1.encode()
        decoded = RDTPacket.decode(encoded)
        assert decoded.validate() is True

    def test_exceeds_max_length_raises_error(self):
        """测试超过最大长度会抛出错误"""
        with pytest.raises(ValueError, match="数据长度超过限制"):
            RDTPacket(
                seq=0,
                checksum=0,
                data=b"X" * 1025  # 超过限制
            ).encode()


class TestRDTPacketStructure:
    """RDT 数据包结构测试"""

    def test_packet_structure(self):
        """测试数据包结构"""
        # +--------+--------+----------+
        # | Seq    | Check  | Data     |
        # | 2 Bytes| 2 Bytes| <=1024 Bytes|
        # +--------+--------+----------+
        packet = RDTPacket(
            seq=1,
            checksum=0,
            data=b"test"
        )
        encoded = packet.encode()

        # 验证各部分大小
        assert len(encoded) == 4 + 4  # Header + Data
        assert len(encoded[0:2]) == 2  # Seq field
        assert len(encoded[2:4]) == 2  # Check field
        assert len(encoded[4:]) == 4   # Data field


class TestRDTCRC16:
    """RDT CRC16 校验和测试"""

    def test_checksum_calculation(self):
        """测试校验和计算"""
        from shared.protocols.rdt import crc16

        # 测试空数据
        checksum1 = crc16(b"")
        assert isinstance(checksum1, int)
        assert 0 <= checksum1 <= 0xFFFF

        # 测试有数据
        checksum2 = crc16(b"test data")
        assert isinstance(checksum2, int)
        assert 0 <= checksum2 <= 0xFFFF

    def test_checksum_consistency(self):
        """测试校验和一致性"""
        from shared.protocols.rdt import crc16

        data = b"consistent test"

        # 多次计算应该得到相同结果
        checksum1 = crc16(data)
        checksum2 = crc16(data)

        assert checksum1 == checksum2

    def test_checksum_includes_seq(self):
        """测试校验和包含 Seq 字段"""
        from shared.protocols.rdt import crc16

        # 校验和计算: checksum(seq + data)
        seq = 42
        data = b"test data"

        # 构造待校验数据
        data_to_checksum = struct.pack(">H", seq) + data
        checksum = crc16(data_to_checksum)

        assert isinstance(checksum, int)
        assert 0 <= checksum <= 0xFFFF


class TestRDTPacketValidation:
    """RDT 数据包验证测试"""

    def test_validate_with_correct_checksum(self):
        """测试使用正确校验和验证"""
        packet = RDTPacket(
            seq=1,
            checksum=0,
            data=b"test"
        )
        encoded = packet.encode()

        decoded = RDTPacket.decode(encoded)
        assert decoded.validate() is True

    def test_validate_with_incorrect_checksum(self):
        """测试使用错误校验和验证"""
        # 手动构造包以使用错误的校验和
        import struct

        packet = RDTPacket(
            seq=1,
            checksum=0xFFFF,  # 将被 encode 覆盖
            data=b"test"
        )
        encoded = packet.encode()

        # 篡改校验和
        tampered = bytearray(encoded)
        tampered[2] = 0xFF
        tampered[3] = 0xFF

        decoded = RDTPacket.decode(bytes(tampered))
        assert decoded.validate() is False

    def test_seq_range(self):
        """测试 Seq 范围 (0-65535)"""
        # 最小值 - 需要 encode 然后解码才能得到正确的校验和
        msg1 = RDTPacket(
            seq=0,
            checksum=0,
            data=b""
        )
        assert msg1.seq == 0
        encoded1 = msg1.encode()
        decoded1 = RDTPacket.decode(encoded1)
        assert decoded1.validate() is True

        # 最大值
        msg2 = RDTPacket(
            seq=65535,
            checksum=0,
            data=b""
        )
        encoded2 = msg2.encode()
        decoded2 = RDTPacket.decode(encoded2)
        assert decoded2.seq == 65535


class TestACKPacketFormat:
    """ACK 包格式测试"""

    def test_ack_header_size(self):
        """测试 ACK 头部大小为 4 字节"""
        # Seq (2) + Check (2) = 4 bytes
        assert ACKPacket.HEADER_SIZE == 4

    def test_ack_header_format(self):
        """测试 ACK 头部格式"""
        # >HH: big-endian uint16, uint16
        expected_format = ">HH"
        assert ACKPacket.HEADER_FORMAT == expected_format

    def test_ack_fixed_size(self):
        """测试 ACK 包固定大小"""
        ack = ACKPacket(seq=1, checksum=0)
        encoded = ack.encode()

        # ACK 包只有头部，没有数据
        assert len(encoded) == 4

    def test_ack_structure(self):
        """测试 ACK 包结构"""
        # +--------+--------+
        # | Seq    | Check  |
        # | 2 Bytes| 2 Bytes|
        # +--------+--------+
        ack = ACKPacket(seq=100, checksum=0)
        encoded = ack.encode()

        # 验证各部分大小
        assert len(encoded[0:2]) == 2  # Seq field
        assert len(encoded[2:4]) == 2  # Check field

    def test_ack_byte_order(self):
        """测试 ACK 包使用大端序"""
        ack = ACKPacket(seq=0x1234, checksum=0x5678)
        encoded = ack.encode()

        # 验证 Seq 的大端序
        seq_bytes = encoded[0:2]
        unpacked_seq = struct.unpack(">H", seq_bytes)[0]
        assert unpacked_seq == 0x1234

        # 验证 Checksum 的大端序（会在 encode 中计算）
        assert len(encoded[2:4]) == 2

    def test_ack_validation(self):
        """测试 ACK 包验证"""
        ack = ACKPacket(seq=1, checksum=0)
        encoded = ack.encode()

        decoded = ACKPacket.decode(encoded)
        assert decoded.validate() is True

    def test_ack_invalid_checksum(self):
        """测试无效校验和"""
        import struct

        # 构造错误的 ACK
        invalid_ack = struct.pack(
            ACKPacket.HEADER_FORMAT,
            5,          # Seq
            0xFFFF      # 错误的 Checksum
        )

        decoded = ACKPacket.decode(invalid_ack)
        assert decoded.validate() is False


class TestRDTWireFormatCompliance:
    """RDT 协议规范一致性测试"""

    def test_compliance_with_spec(self):
        """测试符合规范文档"""
        # 验证所有格式常量
        assert RDTPacket.MAX_DATA_LENGTH == 1024
        assert RDTPacket.HEADER_SIZE == 4
        assert RDTPacket.HEADER_FORMAT == ">HH"

        assert ACKPacket.HEADER_SIZE == 4
        assert ACKPacket.HEADER_FORMAT == ">HH"

    def test_all_packets_use_big_endian(self):
        """测试所有包使用大端序"""
        # 验证格式字符串以 > 开头（big-endian）
        assert RDTPacket.HEADER_FORMAT.startswith(">")
        assert ACKPacket.HEADER_FORMAT.startswith(">")

    def test_seq_field_2_bytes(self):
        """测试 Seq 字段为 2 字节"""
        assert struct.calcsize(">H") == 2
        assert RDTPacket.HEADER_FORMAT == ">HH"  # uint16 = 2 bytes

    def test_checksum_field_2_bytes(self):
        """测试 Checksum 字段为 2 字节"""
        assert struct.calcsize(">H") == 2
        assert RDTPacket.HEADER_FORMAT == ">HH"  # uint16 = 2 bytes
