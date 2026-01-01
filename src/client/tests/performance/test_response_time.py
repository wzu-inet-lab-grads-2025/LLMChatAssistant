"""
响应时间性能测试
Constitution: 100% 真实测试，禁止使用 mock

测试范围:
- 连接建立时间（目标 < 2秒）
- 聊天首字响应时间（目标 < 500ms）
- 文件传输速度（目标 > 10MB/s）
"""

import pytest
import asyncio
import time
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import BaseCLITest
from src.client.tests.fixtures.test_data import DataFileGenerator


class TestResponseTime(BaseCLITest):
    """
    响应时间性能测试类

    测试系统在各种操作下的响应时间性能
    所有测试使用真实服务器和真实API，禁止mock
    """

    @pytest.mark.performance
    async def test_connection_establishment_time(self):
        """测试连接建立时间（目标 < 2秒）"""
        from client.nplt_client import NPLTClient

        # 使用 time.perf_counter() 精确测量
        start_time = time.perf_counter()

        # 创建并连接客户端
        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            connected = await client.connect()

            # 记录连接完成时间
            connection_time = time.perf_counter() - start_time

            # 验证连接成功
            assert connected is True, "连接应该成功"

            # 记录性能数据
            self.log_test_info(f"连接建立时间: {connection_time:.3f} 秒")
            self.log_test_info(f"连接目标: < 2.0 秒")

            # 断言性能目标
            assert connection_time < 2.0, \
                f"连接建立时间 {connection_time:.3f}s 超过目标 2.0s"

            self.log_test_info("✓ 连接建立时间符合性能要求")

        finally:
            await client.close()

    @pytest.mark.performance
    async def test_chat_first_response_time(self):
        """测试聊天首字响应时间（目标 < 500ms）"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 先建立连接
            await client.connect()
            self.log_test_info("连接已建立")

            # 准备测试消息
            test_message = "你好"

            # 记录发送时间（使用 perf_counter 精确测量）
            send_time = time.perf_counter()

            # 发送聊天消息
            await client.send_chat_message(test_message)

            # 等待首字响应
            first_chunk_time = None
            timeout = 5.0  # 5秒超时

            async def wait_for_first_response():
                nonlocal first_chunk_time
                try:
                    async for chunk in client.receive_stream():
                        if first_chunk_time is None:
                            first_chunk_time = time.perf_counter()
                            break
                except Exception as e:
                    self.log_test_info(f"接收响应异常: {e}")

            # 等待首字响应（带超时）
            try:
                await asyncio.wait_for(wait_for_first_response(), timeout=timeout)
            except asyncio.TimeoutError:
                pytest.fail(f"{timeout}秒内未收到响应")

            # 计算首字响应时间
            if first_chunk_time:
                first_response_time = first_chunk_time - send_time

                # 记录性能数据
                self.log_test_info(f"首字响应时间: {first_response_time * 1000:.2f} ms")
                self.log_test_info(f"响应目标: < 500 ms")

                # 断言性能目标（500ms = 0.5s）
                assert first_response_time < 0.5, \
                    f"首字响应时间 {first_response_time * 1000:.2f}ms 超过目标 500ms"

                self.log_test_info("✓ 首字响应时间符合性能要求")

            # 等待完整响应（确保不阻塞后续测试）
            await asyncio.sleep(1)

        finally:
            await client.close()

    @pytest.mark.performance
    async def test_file_transfer_speed_small(self):
        """测试小文件传输速度（目标 > 10MB/s）"""
        from client.nplt_client import NPLTClient
        from storage.files import UploadedFile

        # 创建测试文件（约 1MB）
        test_gen = TestDataGenerator()
        test_file = test_gen.create_text_file(
            "speed_test_1mb.txt",
            "文件传输速度测试数据。\n",
            size_kb=1024  # 1MB
        )

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 建立连接
            await client.connect()

            # 获取文件大小
            file_size_mb = test_file.stat().st_size / (1024 * 1024)
            self.log_test_info(f"测试文件大小: {file_size_mb:.2f} MB")

            # 记录上传开始时间
            upload_start = time.perf_counter()

            # 上传文件
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 记录上传完成时间
            upload_time = time.perf_counter() - upload_start

            # 计算传输速度
            transfer_speed = file_size_mb / upload_time if upload_time > 0 else 0

            # 记录性能数据
            self.log_test_info(f"文件上传时间: {upload_time:.3f} 秒")
            self.log_test_info(f"传输速度: {transfer_speed:.2f} MB/s")
            self.log_test_info(f"速度目标: > 10 MB/s")

            # 断言性能目标
            assert transfer_speed > 10.0, \
                f"传输速度 {transfer_speed:.2f} MB/s 低于目标 10 MB/s"

            self.log_test_info("✓ 文件传输速度符合性能要求")

            # 验证文件完整性
            assert uploaded_file.storage_path, "存储路径应该存在"
            storage_path = Path(uploaded_file.storage_path)
            assert storage_path.exists(), "文件应该存在于存储路径"

        finally:
            # 清理
            test_gen.cleanup()
            if 'uploaded_file' in locals():
                uploaded_file.delete()
            await client.close()

    @pytest.mark.performance
    async def test_file_transfer_speed_medium(self):
        """测试中等文件传输速度（目标 > 10MB/s）"""
        from client.nplt_client import NPLTClient
        from storage.files import UploadedFile

        # 创建测试文件（约 5MB）
        test_gen = TestDataGenerator()
        test_file = test_gen.create_text_file(
            "speed_test_5mb.txt",
            "中等文件传输速度测试数据。\n",
            size_kb=5120  # 5MB
        )

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 建立连接
            await client.connect()

            # 获取文件大小
            file_size_mb = test_file.stat().st_size / (1024 * 1024)
            self.log_test_info(f"测试文件大小: {file_size_mb:.2f} MB")

            # 记录上传开始时间
            upload_start = time.perf_counter()

            # 上传文件
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 记录上传完成时间
            upload_time = time.perf_counter() - upload_start

            # 计算传输速度
            transfer_speed = file_size_mb / upload_time if upload_time > 0 else 0

            # 记录性能数据
            self.log_test_info(f"文件上传时间: {upload_time:.3f} 秒")
            self.log_test_info(f"传输速度: {transfer_speed:.2f} MB/s")
            self.log_test_info(f"速度目标: > 10 MB/s")

            # 断言性能目标
            assert transfer_speed > 10.0, \
                f"传输速度 {transfer_speed:.2f} MB/s 低于目标 10 MB/s"

            self.log_test_info("✓ 中等文件传输速度符合性能要求")

        finally:
            # 清理
            test_gen.cleanup()
            if 'uploaded_file' in locals():
                uploaded_file.delete()
            await client.close()

    @pytest.mark.performance
    async def test_multiple_connections_performance(self):
        """测试多次连接的平均响应时间"""
        from client.nplt_client import NPLTClient

        connection_times = []
        num_connections = 5

        self.log_test_info(f"测试 {num_connections} 次连接的平均响应时间")

        for i in range(num_connections):
            client = NPLTClient(
                host=self.DEFAULT_HOST,
                port=self.DEFAULT_PORT,
                timeout=self.DEFAULT_TIMEOUT
            )

            try:
                # 精确测量连接时间
                start_time = time.perf_counter()
                await client.connect()
                connection_time = time.perf_counter() - start_time

                connection_times.append(connection_time)
                self.log_test_info(f"  第 {i+1} 次连接: {connection_time:.3f} 秒")

                # 短暂等待避免过快的连接
                await asyncio.sleep(0.5)

            finally:
                await client.close()

        # 计算平均连接时间
        avg_connection_time = sum(connection_times) / len(connection_times)

        # 记录性能数据
        self.log_test_info(f"平均连接时间: {avg_connection_time:.3f} 秒")
        self.log_test_info(f"连接时间范围: {min(connection_times):.3f}s - {max(connection_times):.3f}s")

        # 断言平均性能目标
        assert avg_connection_time < 2.0, \
            f"平均连接时间 {avg_connection_time:.3f}s 超过目标 2.0s"

        self.log_test_info("✓ 平均连接时间符合性能要求")

    @pytest.mark.performance
    async def test_concurrent_requests_performance(self):
        """测试并发请求的响应性能"""
        from client.nplt_client import NPLTClient

        num_clients = 3
        clients = []

        # 创建多个客户端
        for i in range(num_clients):
            client = NPLTClient(
                host=self.DEFAULT_HOST,
                port=self.DEFAULT_PORT,
                timeout=self.DEFAULT_TIMEOUT
            )
            clients.append(client)

        try:
            # 并发连接所有客户端
            connect_start = time.perf_counter()

            connect_tasks = [client.connect() for client in clients]
            results = await asyncio.gather(*connect_tasks, return_exceptions=True)

            total_connect_time = time.perf_counter() - connect_start

            # 验证所有连接成功
            successful_connections = sum(1 for r in results if r is True)
            self.log_test_info(f"成功连接: {successful_connections}/{num_clients}")
            self.log_test_info(f"总连接时间: {total_connect_time:.3f} 秒")

            assert successful_connections == num_clients, \
                f"只有 {successful_connections}/{num_clients} 个客户端连接成功"

            # 并发发送消息
            message_start = time.perf_counter()

            async def send_and_receive(client, message):
                try:
                    await client.send_chat_message(message)
                    # 简单等待响应
                    await asyncio.sleep(0.5)
                    return True
                except Exception as e:
                    self.log_test_info(f"客户端消息发送失败: {e}")
                    return False

            tasks = [
                send_and_receive(client, f"并发测试消息 {i+1}")
                for i, client in enumerate(clients)
            ]
            message_results = await asyncio.gather(*tasks)

            total_message_time = time.perf_counter() - message_start

            # 记录性能数据
            successful_messages = sum(1 for r in message_results if r is True)
            self.log_test_info(f"成功发送消息: {successful_messages}/{num_clients}")
            self.log_test_info(f"总消息时间: {total_message_time:.3f} 秒")
            self.log_test_info(f"平均消息时间: {total_message_time/num_clients:.3f} 秒")

            assert successful_messages == num_clients, \
                f"只有 {successful_messages}/{num_clients} 个消息发送成功"

        finally:
            # 关闭所有客户端
            for client in clients:
                if client.is_connected():
                    await client.close()

    def log_test_info(self, message: str):
        """记录测试信息"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[性能测试] {message}")
        print(f"  [INFO] {message}")
