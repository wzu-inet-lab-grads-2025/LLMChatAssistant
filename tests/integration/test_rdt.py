"""
RDT 文件传输集成测试

测试 RDT 可靠文件传输功能，包括滑动窗口、超时重传等。
遵循章程：真实测试，不允许 mock
"""

import asyncio
import os
import tempfile
import shutil
import hashlib

import pytest
import pytest_asyncio

from src.protocols.rdt import ACKPacket, RDTPacket
from src.server.rdt_server import RDTServer, RDTSession
from src.client.rdt_client import RDTClient, RDTClientSession


@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="跳过 CI 环境中的网络测试"
)
class TestRDTFileTransfer:
    """RDT 文件传输集成测试"""

    @pytest_asyncio.fixture
    async def server_client_pair(self):
        """创建服务器和客户端对"""
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()

        # 创建服务器和客户端
        server = RDTServer(host="127.0.0.1", port=9998, window_size=5, timeout=0.1)
        client = RDTClient(server_host="127.0.0.1", server_port=9998, window_size=5)

        # 启动
        await server.start()
        await client.start()

        yield server, client, temp_dir

        # 清理
        await server.stop()
        await client.stop()
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_send_small_file(self, server_client_pair):
        """测试发送小文件"""
        server, client, temp_dir = server_client_pair

        # 创建测试文件
        test_data = b"Hello, World! This is a test file."
        filename = "test_small.txt"
        token = server.create_session(
            filename=filename,
            file_data=test_data,
            client_addr=("127.0.0.1", 12345)
        )

        # 客户端创建会话
        checksum = hashlib.md5(test_data).hexdigest()
        client.create_session(
            download_token=token,
            filename=filename,
            file_size=len(test_data),
            expected_checksum=checksum
        )

        # 发送文件（异步）
        send_task = asyncio.create_task(
            server.send_file(token, ("127.0.0.1", client.transport.get_extra_info('sockname')[1]))
        )

        # 接收文件
        received_data = await client.receive_file(token, timeout=10.0)

        # 等待发送完成
        await send_task

        # 验证
        assert received_data is not None
        assert received_data == test_data

    @pytest.mark.asyncio
    async def test_send_large_file(self, server_client_pair):
        """测试发送大文件（多个数据包）"""
        server, client, temp_dir = server_client_pair

        # 创建较大的测试文件（约 50KB，50 个数据包）
        test_data = b"X" * (50 * 1024)
        filename = "test_large.txt"
        token = server.create_session(
            filename=filename,
            file_data=test_data,
            client_addr=("127.0.0.1", 12345)
        )

        # 客户端创建会话
        checksum = hashlib.md5(test_data).hexdigest()
        client.create_session(
            download_token=token,
            filename=filename,
            file_size=len(test_data),
            expected_checksum=checksum
        )

        # 发送和接收文件
        send_task = asyncio.create_task(
            server.send_file(token, ("127.0.0.1", client.transport.get_extra_info('sockname')[1]))
        )
        received_data = await client.receive_file(token, timeout=30.0)
        await send_task

        # 验证
        assert received_data is not None
        assert received_data == test_data

    @pytest.mark.asyncio
    async def test_file_integrity_verification(self, server_client_pair):
        """测试文件完整性验证"""
        server, client, temp_dir = server_client_pair

        # 创建测试文件
        test_data = b"File integrity test data with checksum verification."
        filename = "test_integrity.txt"
        token = server.create_session(
            filename=filename,
            file_data=test_data,
            client_addr=("127.0.0.1", 12345)
        )

        # 获取正确的校验和
        correct_checksum = hashlib.md5(test_data).hexdigest()

        # 客户端创建会话（使用错误的校验和）
        client.create_session(
            download_token=token,
            filename=filename,
            file_size=len(test_data),
            expected_checksum="wrong_checksum_12345"
        )

        # 发送文件
        send_task = asyncio.create_task(
            server.send_file(token, ("127.0.0.1", client.transport.get_extra_info('sockname')[1]))
        )
        received_data = await client.receive_file(token, timeout=10.0)
        await send_task

        # 应该返回 None（校验和不匹配）
        assert received_data is None

    @pytest.mark.asyncio
    async def test_sliding_window_mechanism(self, server_client_pair):
        """测试滑动窗口机制"""
        server, client, temp_dir = server_client_pair

        # 创建文件（需要多个数据包）
        test_data = b"A" * (10 * 1024)  # 约 10KB
        filename = "test_window.txt"
        token = server.create_session(
            filename=filename,
            file_data=test_data,
            client_addr=("127.0.0.1", 12345)
        )

        # 获取会话
        session = server.sessions.get(token)
        assert session is not None
        assert session.window_size == 5

        # 客户端创建会话
        checksum = hashlib.md5(test_data).hexdigest()
        client.create_session(
            download_token=token,
            filename=filename,
            file_size=len(test_data),
            expected_checksum=checksum
        )

        # 发送和接收文件
        send_task = asyncio.create_task(
            server.send_file(token, ("127.0.0.1", client.transport.get_extra_info('sockname')[1]))
        )
        received_data = await client.receive_file(token, timeout=20.0)
        await send_task

        # 验证
        assert received_data is not None
        assert received_data == test_data

    @pytest.mark.asyncio
    async def test_packet_reordering(self, server_client_pair):
        """测试乱序数据包处理"""
        server, client, temp_dir = server_client_pair

        # 创建测试文件
        test_data = b"Packet reordering test."
        filename = "test_reorder.txt"

        # 手动创建会话并测试乱序接收
        token = server.create_session(
            filename=filename,
            file_data=test_data,
            client_addr=("127.0.0.1", 12345)
        )

        checksum = hashlib.md5(test_data).hexdigest()
        client_session = client.create_session(
            download_token=token,
            filename=filename,
            file_size=len(test_data),
            expected_checksum=checksum
        )

        # 手动发送数据包（模拟乱序）
        server_session = server.sessions.get(token)

        # 分片文件
        chunks = []
        chunk_size = RDTPacket.MAX_DATA_LENGTH
        for i in range(0, len(test_data), chunk_size):
            chunks.append((i // chunk_size, test_data[i:i + chunk_size]))

        # 乱序发送
        client_addr = ("127.0.0.1", client.transport.get_extra_info('sockname')[1])

        # 先发送后面的包
        for seq, chunk in reversed(chunks[:3]):
            packet = RDTPacket(seq=seq, checksum=0, data=chunk)
            await server._send_packet(packet, client_addr)
            await asyncio.sleep(0.01)

        # 再发送前面的包
        for seq, chunk in chunks:
            packet = RDTPacket(seq=seq, checksum=0, data=chunk)
            await server._send_packet(packet, client_addr)
            await asyncio.sleep(0.01)

        # 等待接收完成
        received_data = await client.receive_file(token, timeout=5.0)

        # 验证
        assert received_data is not None
        assert received_data == test_data


@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="跳过 CI 环境中的网络测试"
)
class TestRDTClientSession:
    """RDT 客户端会话测试"""

    def test_create_session(self):
        """测试创建会话"""
        session = RDTClientSession(
            download_token="test-token",
            filename="test.txt",
            file_size=1024,
            expected_checksum="abc123",
            state="receiving"
        )

        # 手动计算 total_packets（因为不是通过 create_session 创建）
        import math
        session.total_packets = math.ceil(session.file_size / RDTPacket.MAX_DATA_LENGTH)

        assert session.download_token == "test-token"
        assert session.filename == "test.txt"
        assert session.file_size == 1024
        assert session.total_packets == 1  # 1024 字节 = 1 个包

    def test_add_packet(self):
        """测试添加数据包"""
        session = RDTClientSession(
            download_token="test-token",
            filename="test.txt",
            file_size=2048,
            expected_checksum="abc123",
            state="receiving"
        )

        # 添加新包
        is_new = session.add_packet(0, b"data1")
        assert is_new is True
        assert session.received_count == 1

        # 添加重复包
        is_new = session.add_packet(0, b"data1")
        assert is_new is False
        assert session.received_count == 1  # 不增加
        assert session.duplicate_count == 1

    def test_assemble_file(self):
        """测试组装文件"""
        session = RDTClientSession(
            download_token="test-token",
            filename="test.txt",
            file_size=10,
            expected_checksum="abc123",
            state="receiving"
        )

        # 添加数据包
        session.add_packet(0, b"Hello")
        session.add_packet(1, b"World")

        # 组装文件
        file_data = session.assemble_file()
        assert file_data == b"HelloWorld"

    def test_verify_checksum(self):
        """测试校验和验证"""
        import hashlib

        test_data = b"Checksum verification test"
        checksum = hashlib.md5(test_data).hexdigest()

        session = RDTClientSession(
            download_token="test-token",
            filename="test.txt",
            file_size=len(test_data),
            expected_checksum=checksum,
            state="receiving"
        )

        # 添加数据包
        chunk_size = RDTPacket.MAX_DATA_LENGTH
        for i in range(0, len(test_data), chunk_size):
            session.add_packet(i // chunk_size, test_data[i:i + chunk_size])

        # 验证校验和
        assert session.verify_checksum() is True
