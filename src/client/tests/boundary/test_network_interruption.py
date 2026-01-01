"""
网络中断场景测试
Constitution: 100% 真实测试，禁止使用 mock

测试范围:
- 网络不稳定模拟
- 重连机制验证
- 服务器重启恢复
- 连接中断后的状态恢复
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
from fixtures.test_data import TestDataGenerator


class TestNetworkInterruption(BaseCLITest):
    """
    网络中断场景测试类

    测试系统在网络不稳定和中断情况下的行为
    所有测试使用真实服务器和真实网络，禁止mock
    """

    @pytest.mark.boundary
    async def test_connection_interrupt_during_idle(self):
        """测试空闲时连接中断"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT,
            max_retries=3
        )

        try:
            # 建立连接
            connected = await client.connect()
            assert connected is True, "初始连接应该成功"
            self.log_test_info("✓ 初始连接成功")

            # 等待一段时间进入空闲状态
            await asyncio.sleep(2)

            # 模拟网络中断：强制关闭连接
            self.log_test_info("模拟网络中断（关闭socket）")
            if client.writer:
                client.writer.close()
                await client.writer.wait_closed()
                client.connected = False

            # 验证连接已断开
            assert not client.is_connected(), "连接应该显示为已断开"
            self.log_test_info("✓ 连接已断开")

            # 尝试发送消息（应该失败或触发重连）
            try:
                await client.send_chat_message("测试消息")
                self.log_test_info("消息发送成功（可能触发了重连）")
            except Exception as e:
                self.log_test_info(f"预期的发送失败: {type(e).__name__}")

        finally:
            await client.close()

    @pytest.mark.boundary
    async def test_reconnection_mechanism(self):
        """测试重连机制"""
        from client.nplt_client import NPLTClient

        # 创建具有重试能力的客户端
        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT,
            max_retries=3
        )

        try:
            # 第一次连接
            connected = await client.connect()
            assert connected is True, "首次连接应该成功"
            self.log_test_info("✓ 首次连接成功")

            # 记录初始连接信息
            initial_reader = client.reader
            initial_writer = client.writer

            # 手动断开连接
            self.log_test_info("手动断开连接")
            await client.close()
            assert not client.is_connected(), "连接应该已断开"

            # 等待短暂时间
            await asyncio.sleep(1)

            # 尝试重新连接
            self.log_test_info("尝试重新连接...")
            reconnected = await client.connect()

            # 验证重连结果
            if reconnected:
                self.log_test_info("✓ 重连成功")
                assert client.is_connected(), "客户端状态应该显示已连接"
                assert client.reader is not None, "应该有新的StreamReader"
                assert client.writer is not None, "应该有新的StreamWriter"
            else:
                self.log_test_info("✗ 重连失败（服务器可能不可用）")

        finally:
            if client.is_connected():
                await client.close()

    @pytest.mark.boundary
    async def test_connection_instability_simulation(self):
        """测试连接不稳定性模拟"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 建立连接
            await client.connect()
            self.log_test_info("✓ 连接建立")

            # 模拟不稳定的连接：多次断开和重连
            reconnect_cycles = 3

            for cycle in range(reconnect_cycles):
                self.log_test_info(f"\n--- 重连循环 {cycle + 1}/{reconnect_cycles} ---")

                # 发送测试消息
                try:
                    await client.send_chat_message(f"测试消息 {cycle + 1}")
                    self.log_test_info(f"  消息 {cycle + 1} 发送成功")
                except Exception as e:
                    self.log_test_info(f"  消息 {cycle + 1} 发送失败: {e}")

                # 短暂等待
                await asyncio.sleep(1)

                # 模拟网络波动：短暂中断
                if client.writer:
                    try:
                        client.writer.close()
                        await client.writer.wait_closed()
                    except:
                        pass

                client.connected = False
                self.log_test_info(f"  模拟中断 {cycle + 1}")

                # 等待后重连
                await asyncio.sleep(2)

                # 尝试重连
                reconnected = await client.connect()
                if reconnected:
                    self.log_test_info(f"  ✓ 重连成功（循环 {cycle + 1}）")
                else:
                    self.log_test_info(f"  ✗ 重连失败（循环 {cycle + 1}）")
                    break

        finally:
            await client.close()

    @pytest.mark.boundary
    async def test_message_during_connection_loss(self):
        """测试连接丢失期间的消息处理"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 建立连接
            await client.connect()
            self.log_test_info("✓ 连接建立")

            # 发送第一条消息（应该成功）
            try:
                await client.send_chat_message("连接正常时的消息")
                self.log_test_info("✓ 第一条消息发送成功")
            except Exception as e:
                self.log_test_info(f"第一条消息发送失败: {e}")

            # 短暂等待
            await asyncio.sleep(1)

            # 断开连接
            self.log_test_info("断开连接")
            if client.writer:
                client.writer.close()
                await client.writer.wait_closed()
            client.connected = False

            # 尝试在断开状态下发送消息（应该失败）
            self.log_test_info("尝试在断开状态下发送消息...")
            try:
                await client.send_chat_message("断开连接后的消息")
                self.log_test_info("  消息发送成功（意外）")
            except Exception as e:
                self.log_test_info(f"  ✓ 预期的发送失败: {type(e).__name__}")

            # 重连后再次发送
            self.log_test_info("重连后发送消息...")
            reconnected = await client.connect()
            if reconnected:
                try:
                    await client.send_chat_message("重连后的消息")
                    self.log_test_info("  ✓ 重连后消息发送成功")
                except Exception as e:
                    self.log_test_info(f"  重连后消息发送失败: {e}")

        finally:
            await client.close()

    @pytest.mark.boundary
    async def test_multiple_clients_with_interruption(self):
        """测试多客户端场景下的连接中断"""
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
            # 连接所有客户端
            self.log_test_info(f"连接 {num_clients} 个客户端...")
            for i, client in enumerate(clients):
                connected = await client.connect()
                assert connected is True, f"客户端 {i+1} 连接应该成功"
                self.log_test_info(f"  ✓ 客户端 {i+1} 已连接")

            # 中断部分客户端的连接
            interrupt_count = 2
            self.log_test_info(f"\n中断前 {interrupt_count} 个客户端的连接...")
            for i in range(interrupt_count):
                if clients[i].writer:
                    clients[i].writer.close()
                    await clients[i].writer.wait_closed()
                clients[i].connected = False
                self.log_test_info(f"  ✓ 客户端 {i+1} 连接已中断")

            # 短暂等待
            await asyncio.sleep(1)

            # 尝试恢复所有客户端的连接
            self.log_test_info("\n尝试恢复所有客户端连接...")
            for i, client in enumerate(clients):
                if not client.is_connected():
                    reconnected = await client.connect()
                    if reconnected:
                        self.log_test_info(f"  ✓ 客户端 {i+1} 重连成功")
                    else:
                        self.log_test_info(f"  ✗ 客户端 {i+1} 重连失败")

            # 验证所有客户端最终状态
            self.log_test_info("\n验证客户端最终状态...")
            connected_count = sum(1 for c in clients if c.is_connected())
            self.log_test_info(f"已连接客户端数: {connected_count}/{num_clients}")

        finally:
            # 关闭所有客户端
            for i, client in enumerate(clients):
                if client.is_connected():
                    await client.close()
                    self.log_test_info(f"✓ 客户端 {i+1} 已关闭")

    @pytest.mark.boundary
    async def test_long_connection_with_interruptions(self):
        """测试长连接中的多次中断"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 建立连接
            await client.connect()
            self.log_test_info("✓ 长连接建立")

            # 模拟长时间连接中的多次中断
            test_duration = 15  # 总测试时间（秒）
            interval = 5  # 中断间隔（秒）

            start_time = time.time()
            interrupt_count = 0

            while time.time() - start_time < test_duration:
                # 发送消息
                try:
                    await client.send_chat_message(
                        f"长连接测试消息（{interrupt_count + 1}）"
                    )
                    self.log_test_info(
                        f"  消息发送成功 "
                        f"(运行时间: {time.time() - start_time:.1f}s)"
                    )
                except Exception as e:
                    self.log_test_info(f"  消息发送失败: {e}")

                # 等待一段时间
                await asyncio.sleep(interval)

                # 模拟中断
                if client.is_connected():
                    self.log_test_info(f"  模拟中断 {interrupt_count + 1}")
                    if client.writer:
                        try:
                            client.writer.close()
                            await client.writer.wait_closed()
                        except:
                            pass
                    client.connected = False
                    interrupt_count += 1

                    # 等待后重连
                    await asyncio.sleep(2)
                    reconnected = await client.connect()
                    if reconnected:
                        self.log_test_info(f"  ✓ 重连成功")
                    else:
                        self.log_test_info(f"  ✗ 重连失败，退出测试")
                        break

            self.log_test_info(f"\n测试完成，共模拟 {interrupt_count} 次中断")

        finally:
            await client.close()

    @pytest.mark.boundary
    async def test_timeout_after_connection_loss(self):
        """测试连接丢失后的超时行为"""
        from client.nplt_client import NPLTClient

        # 创建一个短超时的客户端
        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=5  # 5秒超时
        )

        try:
            # 建立连接
            await client.connect()
            self.log_test_info("✓ 连接建立")

            # 断开连接
            self.log_test_info("断开连接")
            if client.writer:
                client.writer.close()
                await client.writer.wait_closed()
            client.connected = False

            # 尝试操作并测量超时
            self.log_test_info("尝试发送消息并等待超时...")
            start_time = time.time()

            try:
                await client.send_chat_message("测试超时")
                elapsed = time.time() - start_time
                self.log_test_info(f"  消息发送成功（耗时: {elapsed:.2f}s）")
            except Exception as e:
                elapsed = time.time() - start_time
                self.log_test_info(
                    f"  ✓ 在 {elapsed:.2f}s 后预期失败: {type(e).__name__}"
                )

                # 验证在合理时间内失败（不应该无限等待）
                assert elapsed < 10.0, \
                    f"操作在 {elapsed:.2f}s 后失败，耗时过长（可能未正确超时）"

        finally:
            await client.close()

    @pytest.mark.boundary
    async def test_rapid_connection_cycles(self):
        """测试快速连接/断开循环"""
        from client.nplt_client import NPLTClient

        cycles = 5
        self.log_test_info(f"执行 {cycles} 次快速连接/断开循环")

        for cycle in range(cycles):
            self.log_test_info(f"\n--- 循环 {cycle + 1}/{cycles} ---")

            client = NPLTClient(
                host=self.DEFAULT_HOST,
                port=self.DEFAULT_PORT,
                timeout=self.DEFAULT_TIMEOUT
            )

            try:
                # 连接
                connect_start = time.time()
                connected = await client.connect()
                connect_time = time.time() - connect_start

                if connected:
                    self.log_test_info(f"  ✓ 连接成功 ({connect_time:.3f}s)")

                    # 短暂等待
                    await asyncio.sleep(0.5)

                    # 发送快速消息
                    try:
                        await client.send_chat_message(f"快速测试 {cycle + 1}")
                        self.log_test_info(f"  ✓ 消息发送成功")
                    except Exception as e:
                        self.log_test_info(f"  消息发送失败: {e}")

                else:
                    self.log_test_info(f"  ✗ 连接失败")

            finally:
                # 断开
                await client.close()
                self.log_test_info(f"  ✓ 连接已关闭")

            # 循环间短暂等待
            if cycle < cycles - 1:
                await asyncio.sleep(1)

    def log_test_info(self, message: str):
        """记录测试信息"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[网络中断测试] {message}")
        print(f"  [INFO] {message}")
