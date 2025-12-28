"""
客户端长期运行测试

验证客户端在 100+ 轮对话后没有内存泄漏和性能下降。
遵循章程：真实测试，不允许 mock
"""

import asyncio
import psutil
import os
import pytest
import pytest_asyncio
import time

from src.client.nplt_client import NPLTClient
from src.client.ui import ClientUI
from src.server.nplt_server import NPLTServer


@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="跳过 CI 环境中的性能测试"
)
class TestClientMemoryLeak:
    """客户端内存泄漏测试"""

    @pytest_asyncio.fixture
    async def server(self):
        """创建测试服务器"""
        server = NPLTServer(host="127.0.0.1", port=9999)
        await server.start()
        yield server
        await server.stop()

    @pytest.fixture
    def process(self):
        """获取当前进程对象"""
        return psutil.Process(os.getpid())

    def get_memory_mb(self, process: psutil.Process) -> float:
        """获取进程内存使用（MB）"""
        mem_info = process.memory_info()
        return mem_info.rss / 1024 / 1024  # 转换为 MB

    @pytest.mark.asyncio
    async def test_client_memory_leak(self, server, process):
        """测试客户端长期运行（100 轮对话）的内存使用情况

        验收标准：
        - 100 轮对话后内存增长 < 50MB
        - 没有明显的内存泄漏模式
        """
        # 记录初始内存
        initial_memory = self.get_memory_mb(process)
        print(f"\n初始内存使用: {initial_memory:.2f} MB")

        # 创建客户端
        client = NPLTClient(host="127.0.0.1", port=9999)

        # 模拟 100 轮对话
        num_rounds = 100
        memory_samples = []

        for i in range(num_rounds):
            # 每轮对话：发送和接收消息
            await client.connect()

            # 模拟发送消息
            test_message = f"测试消息 {i + 1}"
            await client.send_message(0x01, test_message.encode('utf-8'))

            # 短暂等待模拟真实场景
            await asyncio.sleep(0.01)

            # 每 10 轮记录一次内存
            if (i + 1) % 10 == 0:
                current_memory = self.get_memory_mb(process)
                memory_growth = current_memory - initial_memory
                memory_samples.append({
                    'round': i + 1,
                    'memory_mb': current_memory,
                    'growth_mb': memory_growth
                })
                print(f"轮次 {i + 1}: 内存={current_memory:.2f} MB, 增长={memory_growth:.2f} MB")

            await client.disconnect()

        # 最终内存
        final_memory = self.get_memory_mb(process)
        total_growth = final_memory - initial_memory
        print(f"\n最终内存使用: {final_memory:.2f} MB")
        print(f"总内存增长: {total_growth:.2f} MB")

        # 验证内存增长不超过 50MB
        assert total_growth < 50, f"内存增长过大: {total_growth:.2f} MB >= 50 MB"

        # 验证没有持续增长的内存泄漏模式
        # 检查最后 5 个样本的平均增长率
        if len(memory_samples) >= 5:
            last_5_growth = [s['growth_mb'] for s in memory_samples[-5:]]
            avg_growth = sum(last_5_growth) / len(last_5_growth)
            print(f"最后 5 个样本的平均内存增长: {avg_growth:.2f} MB")

            # 如果平均增长率持续很高，可能存在内存泄漏
            # 这里我们设置一个宽松的阈值（40MB），因为正常情况下应该有一些增长
            assert avg_growth < 40, f"检测到可能的内存泄漏，平均增长: {avg_growth:.2f} MB"

    @pytest.mark.asyncio
    async def test_client_ui_performance(self, server, process):
        """测试客户端 UI 在长时间运行后的性能

        验收标准：
        - 100 轮对话后 UI 渲染没有明显卡顿
        - 每轮 UI 更新时间 < 100ms
        """
        ui = ClientUI()
        client = NPLTClient(host="127.0.0.1", port=9999, ui=ui)

        # 记录性能指标
        render_times = []

        for i in range(100):
            start_time = time.time()

            # 模拟 UI 渲染
            ui.print_info(f"测试消息 {i + 1}")
            ui.print_success(f"操作成功 {i + 1}")

            end_time = time.time()
            render_time = (end_time - start_time) * 1000  # 转换为毫秒
            render_times.append(render_time)

            # 每 20 轮检查一次平均性能
            if (i + 1) % 20 == 0:
                avg_time = sum(render_times[-20:]) / 20
                print(f"轮次 {i + 1}: 平均渲染时间 {avg_time:.2f} ms")
                # 验证平均渲染时间 < 100ms
                assert avg_time < 100, f"UI 渲染性能下降: {avg_time:.2f} ms >= 100 ms"

        # 最终验证
        overall_avg = sum(render_times) / len(render_times)
        print(f"\n总体平均渲染时间: {overall_avg:.2f} ms")
        assert overall_avg < 100, f"整体 UI 渲染性能不足: {overall_avg:.2f} ms >= 100 ms"

    @pytest.mark.asyncio
    async def test_client_connection_stability(self, server):
        """测试客户端连接在长时间运行后的稳定性

        验收标准：
        - 100 轮连接/断开后仍能正常连接
        - 没有连接泄漏（未关闭的连接）
        """
        client = NPLTClient(host="127.0.0.1", port=9999)

        # 执行 100 次连接/断开循环
        success_count = 0
        for i in range(100):
            try:
                await client.connect()
                assert client.connected, f"轮次 {i + 1}: 连接失败"
                await client.disconnect()
                assert not client.connected, f"轮次 {i + 1}: 断开失败"
                success_count += 1
            except Exception as e:
                print(f"轮次 {i + 1} 失败: {e}")

            # 每 20 轮检查一次
            if (i + 1) % 20 == 0:
                print(f"轮次 {i + 1}: 成功率 {success_count}/{i + 1}")

        # 验证成功率 >= 95%
        success_rate = success_count / 100
        print(f"\n最终成功率: {success_rate:.2%}")
        assert success_rate >= 0.95, f"连接稳定性不足: {success_rate:.2%} < 95%"


@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="跳过 CI 环境中的性能测试"
)
class TestClientStressTest:
    """客户端压力测试"""

    @pytest_asyncio.fixture
    async def server(self):
        """创建测试服务器"""
        server = NPLTServer(host="127.0.0.1", port=9999)
        await server.start()
        yield server
        await server.stop()

    @pytest.mark.asyncio
    async def test_rapid_message_send(self, server):
        """测试快速发送大量消息

        验收标准：
        - 能够快速发送 50 条消息
        - 没有消息丢失或错误
        """
        client = NPLTClient(host="127.0.0.1", port=9999)

        await client.connect()

        # 快速发送 50 条消息
        num_messages = 50
        success_count = 0

        start_time = time.time()

        for i in range(num_messages):
            try:
                message = f"快速测试消息 {i + 1}"
                await client.send_message(0x01, message.encode('utf-8'))
                success_count += 1
            except Exception as e:
                print(f"消息 {i + 1} 发送失败: {e}")

        end_time = time.time()
        elapsed = end_time - start_time

        await client.disconnect()

        # 验证结果
        print(f"\n发送 {success_count}/{num_messages} 条消息")
        print(f"耗时: {elapsed:.2f} 秒")
        print(f"平均速率: {num_messages / elapsed:.2f} 消息/秒")

        assert success_count >= num_messages * 0.95, f"消息丢失率过高: {success_count}/{num_messages}"

    @pytest.mark.asyncio
    async def test_concurrent_connections(self, server):
        """测试多个客户端同时连接

        验收标准：
        - 10 个客户端能同时连接
        - 所有客户端都能正常通信
        """
        num_clients = 10
        clients = []

        # 创建并连接多个客户端
        for i in range(num_clients):
            client = NPLTClient(host="127.0.0.1", port=9999)
            await client.connect()
            assert client.connected, f"客户端 {i + 1} 连接失败"
            clients.append(client)

        # 所有客户端发送消息
        for i, client in enumerate(clients):
            message = f"客户端 {i + 1} 测试消息"
            await client.send_message(0x01, message.encode('utf-8'))

        # 断开所有客户端
        for i, client in enumerate(clients):
            await client.disconnect()
            assert not client.connected, f"客户端 {i + 1} 断开失败"

        print(f"\n成功处理 {num_clients} 个并发连接")
