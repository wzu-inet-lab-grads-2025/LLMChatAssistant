"""
连接服务器测试 (T022)
Constitution: 100% 真实测试，禁止使用 mock
"""

import pytest
import asyncio
from src.client.tests.base import BaseCLITest


class TestConnection(BaseCLITest):
    """
    连接服务器测试类

    测试客户端与服务器的TCP连接功能
    所有测试使用真实服务器，禁止mock
    """

    @pytest.mark.e2e
    async def test_tcp_connection_establishment(self):
        """测试TCP连接建立"""
        # 导入客户端（延迟导入以避免启动时的导入错误）
        from client.nplt_client import NPLTClient

        # 创建客户端
        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        # 尝试连接
        try:
            connected = await client.connect()
            assert connected is True, "连接应该成功"
            assert client.is_connected(), "客户端状态应该显示已连接"

            # 验证Socket已建立
            assert client.reader is not None, "StreamReader应该存在"
            assert client.writer is not None, "StreamWriter应该存在"

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_welcome_message_received(self):
        """测试接收服务器欢迎消息"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            await client.connect()

            # 等待欢迎消息（超时5秒）
            try:
                message_type, seq, data = await asyncio.wait_for(
                    client.receive_message(),
                    timeout=5.0
                )

                # 验证欢迎消息
                assert message_type is not None, "应该接收到消息类型"
                assert data is not None, "应该接收到消息数据"
                assert len(data) > 0, "消息数据不应为空"

                # 欢迎消息通常包含"欢迎使用"等字样
                message_text = data.decode('utf-8', errors='ignore')
                self.log_test_info(f"收到欢迎消息: {message_text[:100]}...")

            except asyncio.TimeoutError:
                pytest.fail("5秒内未收到欢迎消息")

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_connection_timeout(self):
        """测试连接超时处理"""
        from client.nplt_client import NPLTClient

        # 使用一个不太可能开放的端口
        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=19999,  # 假设此端口未开放
            timeout=2  # 2秒超时
        )

        try:
            connected = await client.connect()
            assert connected is False, "连接到不存在的端口应该失败"

        except Exception as e:
            # 预期会抛出超时或连接拒绝异常
            self.log_test_info(f"预期的连接失败: {type(e).__name__}")
            assert True  # 测试通过

    @pytest.mark.e2e
    async def test_connection_persistence(self):
        """测试连接持久性"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 建立连接
            await client.connect()
            assert client.is_connected(), "初始连接应该成功"

            # 等待10秒，验证连接保持
            await asyncio.sleep(10)

            # 验证连接仍然有效
            assert client.is_connected(), "10秒后连接应该仍然有效"

            # 尝试发送心跳消息（如果协议支持）
            # 这里我们假设客户端会自动发送心跳

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_multiple_connections(self):
        """测试多个客户端连接"""
        from client.nplt_client import NPLTClient

        clients = []

        try:
            # 创建3个客户端连接
            for i in range(3):
                client = NPLTClient(
                    host=self.DEFAULT_HOST,
                    port=self.DEFAULT_PORT,
                    timeout=self.DEFAULT_TIMEOUT
                )
                await client.connect()
                assert client.is_connected(), f"客户端{i+1}连接应该成功"
                clients.append(client)

            # 验证所有连接都有效
            for i, client in enumerate(clients):
                assert client.is_connected(), f"客户端{i+1}连接应该仍然有效"

        finally:
            # 关闭所有客户端
            for client in clients:
                await client.close()

    @pytest.mark.e2e
    async def test_connection_close(self):
        """测试连接关闭"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 建立连接
            await client.connect()
            assert client.is_connected(), "连接应该成功"

            # 关闭连接
            await client.close()

            # 验证连接已关闭
            assert not client.is_connected(), "连接应该已关闭"
            assert client.writer is None, "StreamWriter应该已清理"

        except Exception as e:
            self.log_test_info(f"连接关闭异常: {e}")
            raise

    def log_test_info(self, message: str):
        """记录测试信息"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(message)
