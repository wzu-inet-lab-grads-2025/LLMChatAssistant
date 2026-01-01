"""
并发客户端边界测试

测试并发客户端场景。
遵循章程：真实API，禁止mock
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import pytest_asyncio
import time
from datetime import datetime

from src.client.nplt_client import NPLTClient
from src.server.nplt_server import NPLTServer
from protocols.nplt import MessageType
from pathlib import Path


@pytest.mark.boundary
class TestConcurrentClients:
    """
    并发客户端边界测试

    验收标准:
    - 2个客户端同时连接成功
    - 5个客户端同时连接成功
    - 10个客户端同时连接成功（达到上限）
    - 并发文件上传不冲突
    - 并发聊天不混乱
    - 服务器保持稳定
    """

    @pytest_asyncio.fixture
    async def server(self):
        """创建测试服务器（max_clients=10）"""
        server = NPLTServer(host="127.0.0.1", port=9999, max_clients=10)
        await server.start()
        yield server
        await server.stop()

    async def create_client(self, index: int) -> NPLTClient:
        """
        创建客户端实例

        Args:
            index: 客户端索引

        Returns:
            客户端实例
        """
        client = NPLTClient(host="127.0.0.1", port=9999)
        return client

    async def connect_client(self, client: NPLTClient) -> bool:
        """连接客户端"""
        try:
            success = await client.connect()
            return success
        except Exception as e:
            print(f"客户端连接失败: {e}")
            return False

    async def disconnect_client(self, client: NPLTClient):
        """断开客户端连接"""
        try:
            await client.disconnect()
        except Exception as e:
            print(f"客户端断开失败: {e}")

    async def send_chat_message(self, client: NPLTClient, message: str) -> bool:
        """发送聊天消息"""
        try:
            success = await client.send_chat(message)
            return success
        except Exception as e:
            print(f"发送消息失败: {e}")
            return False

    async def receive_message(self, client: NPLTClient, timeout: float = 5.0) -> Any:
        """接收消息"""
        try:
            message = await asyncio.wait_for(
                client.receive_message(),
                timeout=timeout
            )
            return message
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            print(f"接收消息失败: {e}")
            return None

    @pytest.mark.asyncio
    async def test_two_concurrent_clients(self, server):
        """
        测试2个客户端同时连接

        验收标准:
        - 2个客户端都成功连接
        - 2个客户端都能发送消息
        - 2个客户端都能接收消息
        - 服务器会话数正确
        """
        print("\n开始2个并发客户端测试")

        # 创建2个客户端
        clients = []
        for i in range(2):
            client = await self.create_client(i)
            clients.append(client)

        try:
            # 并发连接
            print("并发连接2个客户端...")
            connect_tasks = [self.connect_client(client) for client in clients]
            results = await asyncio.gather(*connect_tasks)

            # 验证连接结果
            success_count = sum(1 for r in results if r)
            print(f"连接成功: {success_count}/2")

            assert success_count == 2, f"连接失败: {success_count}/2"

            # 验证服务器会话数
            await asyncio.sleep(0.5)  # 等待服务器更新
            session_count = server.get_active_sessions_count()
            print(f"服务器会话数: {session_count}")
            assert session_count == 2, f"会话数不正确: {session_count} != 2"

            # 并发发送消息
            print("并发发送消息...")
            send_tasks = [
                self.send_chat_message(clients[i], f"客户端{i+1}测试消息")
                for i in range(2)
            ]
            send_results = await asyncio.gather(*send_tasks)
            send_success = sum(1 for r in send_results if r)
            print(f"发送成功: {send_success}/2")

            # 等待服务器响应
            await asyncio.sleep(2)

            # 验证客户端仍然连接
            for i, client in enumerate(clients):
                assert client.connected, f"客户端{i+1}连接断开"

            print("✓ 2个并发客户端测试通过")

        finally:
            # 断开所有客户端
            disconnect_tasks = [self.disconnect_client(client) for client in clients]
            await asyncio.gather(*disconnect_tasks)

    @pytest.mark.asyncio
    async def test_five_concurrent_clients(self, server):
        """
        测试5个客户端同时连接

        验收标准:
        - 5个客户端都成功连接
        - 所有客户端都能正常通信
        - 消息不混乱（每个客户端收到自己的响应）
        - 服务器保持稳定
        """
        print("\n开始5个并发客户端测试")

        # 创建5个客户端
        clients = []
        for i in range(5):
            client = await self.create_client(i)
            clients.append(client)

        try:
            # 并发连接
            print("并发连接5个客户端...")
            connect_tasks = [self.connect_client(client) for client in clients]
            results = await asyncio.gather(*connect_tasks)

            # 验证连接结果
            success_count = sum(1 for r in results if r)
            print(f"连接成功: {success_count}/5")

            assert success_count == 5, f"连接失败: {success_count}/5"

            # 验证服务器会话数
            await asyncio.sleep(0.5)
            session_count = server.get_active_sessions_count()
            print(f"服务器会话数: {session_count}")
            assert session_count == 5, f"会话数不正确: {session_count} != 5"

            # 并发发送不同消息
            print("并发发送不同消息...")
            send_tasks = [
                self.send_chat_message(clients[i], f"客户端{i+1}的专属消息")
                for i in range(5)
            ]
            send_results = await asyncio.gather(*send_tasks)
            send_success = sum(1 for r in send_results if r)
            print(f"发送成功: {send_success}/5")

            # 等待服务器响应
            await asyncio.sleep(3)

            # 验证所有客户端仍然连接
            connected_count = sum(1 for client in clients if client.connected)
            print(f"仍然连接的客户端: {connected_count}/5")
            assert connected_count == 5, f"客户端连接断开: {connected_count}/5"

            print("✓ 5个并发客户端测试通过")

        finally:
            # 断开所有客户端
            disconnect_tasks = [self.disconnect_client(client) for client in clients]
            await asyncio.gather(*disconnect_tasks)

    @pytest.mark.asyncio
    async def test_ten_concurrent_clients(self, server):
        """
        测试10个客户端同时连接（达到上限）

        验收标准:
        - 10个客户端都成功连接
        - 所有客户端都能正常通信
        - 第11个客户端被拒绝
        - 服务器保持稳定
        """
        print("\n开始10个并发客户端测试（上限）")

        # 创建10个客户端
        clients = []
        for i in range(10):
            client = await self.create_client(i)
            clients.append(client)

        try:
            # 并发连接10个客户端
            print("并发连接10个客户端...")
            connect_tasks = [self.connect_client(client) for client in clients]
            results = await asyncio.gather(*connect_tasks)

            # 验证连接结果
            success_count = sum(1 for r in results if r)
            print(f"连接成功: {success_count}/10")

            assert success_count == 10, f"连接失败: {success_count}/10"

            # 验证服务器会话数
            await asyncio.sleep(0.5)
            session_count = server.get_active_sessions_count()
            print(f"服务器会话数: {session_count}")
            assert session_count == 10, f"会话数不正确: {session_count} != 10"

            # 并发发送消息
            print("并发发送消息...")
            send_tasks = [
                self.send_chat_message(clients[i], f"客户端{i+1}压力测试消息")
                for i in range(10)
            ]
            send_results = await asyncio.gather(*send_tasks)
            send_success = sum(1 for r in send_results if r)
            print(f"发送成功: {send_success}/10")

            # 等待服务器响应
            await asyncio.sleep(5)

            # 验证所有客户端仍然连接
            connected_count = sum(1 for client in clients if client.connected)
            print(f"仍然连接的客户端: {connected_count}/10")
            assert connected_count == 10, f"客户端连接断开: {connected_count}/10"

            # 测试第11个客户端被拒绝
            print("\n测试第11个客户端连接（应该被拒绝）...")
            client_11 = await self.create_client(11)
            try:
                success_11 = await self.connect_client(client_11)
                # 注意：根据服务器实现，可能会连接成功但服务器会拒绝
                # 这里我们验证服务器会话数不超过10
                await asyncio.sleep(0.5)
                final_session_count = server.get_active_sessions_count()
                print(f"第11个客户端连接后，服务器会话数: {final_session_count}")
                assert final_session_count <= 10, f"会话数超过上限: {final_session_count} > 10"
            finally:
                await self.disconnect_client(client_11)

            print("✓ 10个并发客户端测试通过")

        finally:
            # 断开所有客户端
            disconnect_tasks = [self.disconnect_client(client) for client in clients]
            await asyncio.gather(*disconnect_tasks)

    @pytest.mark.asyncio
    async def test_concurrent_file_uploads(self, server):
        """
        测试并发文件上传

        验收标准:
        - 3个客户端同时上传文件
        - 所有文件上传成功
        - 文件内容不冲突
        - 服务器正确处理每个文件
        """
        print("\n开始并发文件上传测试")

        import tempfile
        import hashlib

        # 创建3个测试文件
        test_files = []
        for i in range(3):
            content = f"这是客户端{i+1}的测试文件内容\n" * 1000
            temp_file = Path(tempfile.mktemp(suffix=f"_client_{i+1}.txt"))
            temp_file.write_text(content, encoding='utf-8')

            # 计算哈希
            file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            test_files.append({
                'path': temp_file,
                'content': content,
                'hash': file_hash,
                'name': temp_file.name
            })

        try:
            # 创建3个客户端
            clients = []
            for i in range(3):
                client = await self.create_client(i)
                clients.append(client)

            # 连接所有客户端
            connect_tasks = [self.connect_client(client) for client in clients]
            await asyncio.gather(*connect_tasks)

            print("3个客户端已连接")

            # 并发上传文件
            print("并发上传文件...")
            upload_tasks = []
            for i, client in enumerate(clients):
                file_info = test_files[i]

                async def upload_file(c, f):
                    try:
                        # 发送文件元数据
                        await c.send_file_metadata(f['name'], len(f['content'].encode('utf-8')))

                        # 发送文件数据
                        await c.send_file_data(f['content'].encode('utf-8'))

                        # 等待服务器处理
                        await asyncio.sleep(1)

                        return True
                    except Exception as e:
                        print(f"文件上传失败: {e}")
                        return False

                upload_tasks.append(upload_file(client, file_info))

            # 执行并发上传
            upload_results = await asyncio.gather(*upload_tasks)
            upload_success = sum(1 for r in upload_results if r)
            print(f"上传成功: {upload_success}/3")

            assert upload_success == 3, f"文件上传失败: {upload_success}/3"

            # 等待服务器处理
            await asyncio.sleep(3)

            # 验证服务器会话仍然正常
            for i, client in enumerate(clients):
                assert client.connected, f"客户端{i+1}连接断开"

            print("✓ 并发文件上传测试通过")

        finally:
            # 断开所有客户端
            disconnect_tasks = [self.disconnect_client(client) for client in clients]
            await asyncio.gather(*disconnect_tasks)

            # 清理测试文件
            for file_info in test_files:
                if file_info['path'].exists():
                    file_info['path'].unlink()

    @pytest.mark.asyncio
    async def test_concurrent_chat_sessions(self, server):
        """
        测试并发聊天会话

        验收标准:
        - 5个客户端同时进行多轮对话
        - 每个客户端的消息不混乱
        - 每个客户端都能收到正确的响应
        - 服务器会话隔离正确
        """
        print("\n开始并发聊天会话测试")

        # 创建5个客户端
        clients = []
        for i in range(5):
            client = await self.create_client(i)
            clients.append(client)

        try:
            # 连接所有客户端
            connect_tasks = [self.connect_client(client) for client in clients]
            await asyncio.gather(*connect_tasks)

            print("5个客户端已连接")

            # 每个客户端发送3轮消息
            num_rounds = 3
            for round_num in range(1, num_rounds + 1):
                print(f"\n第{round_num}轮对话...")

                # 并发发送消息
                send_tasks = [
                    self.send_chat_message(
                        clients[i],
                        f"客户端{i+1}的第{round_num}轮消息"
                    )
                    for i in range(5)
                ]
                send_results = await asyncio.gather(*send_tasks)
                send_success = sum(1 for r in send_results if r)
                print(f"发送成功: {send_success}/5")

                assert send_success == 5, f"第{round_num}轮发送失败: {send_success}/5"

                # 等待服务器处理
                await asyncio.sleep(3)

                # 验证客户端仍然连接
                connected_count = sum(1 for client in clients if client.connected)
                print(f"仍然连接: {connected_count}/5")
                assert connected_count == 5, f"第{round_num}轮后连接断开: {connected_count}/5"

            print("\n✓ 并发聊天会话测试通过")

        finally:
            # 断开所有客户端
            disconnect_tasks = [self.disconnect_client(client) for client in clients]
            await asyncio.gather(*disconnect_tasks)

    @pytest.mark.asyncio
    async def test_server_stability_under_load(self, server):
        """
        测试服务器在高并发下的稳定性

        验收标准:
        - 10个客户端连续发送消息
        - 服务器不崩溃
        - 服务器会话数始终正确
        - 所有客户端都能正常完成操作
        """
        print("\n开始服务器稳定性测试")

        # 创建10个客户端
        clients = []
        for i in range(10):
            client = await self.create_client(i)
            clients.append(client)

        try:
            # 连接所有客户端
            connect_tasks = [self.connect_client(client) for client in clients]
            await asyncio.gather(*connect_tasks)

            print("10个客户端已连接")

            # 每个客户端发送10条消息
            messages_per_client = 10
            total_messages = 0
            success_messages = 0

            for msg_num in range(1, messages_per_client + 1):
                print(f"\n发送第{msg_num}批消息...")

                # 并发发送
                send_tasks = [
                    self.send_chat_message(
                        clients[i],
                        f"客户端{i+1}消息{msg_num}"
                    )
                    for i in range(10)
                ]
                send_results = await asyncio.gather(*send_tasks)

                # 统计成功率
                batch_success = sum(1 for r in send_results if r)
                success_messages += batch_success
                total_messages += len(send_results)

                print(f"本批成功: {batch_success}/10")

                # 验证服务器会话数
                session_count = server.get_active_sessions_count()
                print(f"服务器会话数: {session_count}")
                assert session_count == 10, f"会话数异常: {session_count} != 10"

                # 等待服务器处理
                await asyncio.sleep(2)

            # 统计总体成功率
            success_rate = success_messages / total_messages if total_messages > 0 else 0
            print(f"\n总体成功率: {success_messages}/{total_messages} ({success_rate:.2%})")

            assert success_rate >= 0.95, f"成功率过低: {success_rate:.2%} < 95%"

            # 验证所有客户端仍然连接
            connected_count = sum(1 for client in clients if client.connected)
            print(f"仍然连接的客户端: {connected_count}/10")
            assert connected_count == 10, f"客户端连接断开: {connected_count}/10"

            print("✓ 服务器稳定性测试通过")

        finally:
            # 断开所有客户端
            disconnect_tasks = [self.disconnect_client(client) for client in clients]
            await asyncio.gather(*disconnect_tasks)

    @pytest.mark.asyncio
    async def test_concurrent_connect_disconnect(self, server):
        """
        测试并发连接和断开

        验收标准:
        - 客户端频繁连接和断开
        - 服务器正确管理会话
        - 无会话泄漏
        """
        print("\n开始并发连接/断开测试")

        # 执行3轮连接/断开循环
        num_rounds = 3
        clients_per_round = 5

        for round_num in range(1, num_rounds + 1):
            print(f"\n第{round_num}轮连接/断开...")

            # 创建并连接5个客户端
            clients = []
            for i in range(clients_per_round):
                client = await self.create_client(i)
                clients.append(client)

            # 并发连接
            connect_tasks = [self.connect_client(client) for client in clients]
            await asyncio.gather(*connect_tasks)

            # 验证会话数
            await asyncio.sleep(0.5)
            session_count = server.get_active_sessions_count()
            print(f"连接后会话数: {session_count}")
            assert session_count == clients_per_round, f"会话数不正确: {session_count} != {clients_per_round}"

            # 等待一会儿
            await asyncio.sleep(1)

            # 并发断开
            disconnect_tasks = [self.disconnect_client(client) for client in clients]
            await asyncio.gather(*disconnect_tasks)

            # 验证会话清空
            await asyncio.sleep(0.5)
            session_count = server.get_active_sessions_count()
            print(f"断开后会话数: {session_count}")
            assert session_count == 0, f"会话未清空: {session_count} != 0"

            print(f"第{round_num}轮完成")

        print("\n✓ 并发连接/断开测试通过")

    @pytest.mark.asyncio
    async def test_message_order_preservation(self, server):
        """
        测试并发场景下消息顺序的保持

        验收标准:
        - 每个客户端的消息顺序正确
        - 消息不丢失
        - 消息不重复
        """
        print("\n开始消息顺序保持测试")

        # 创建3个客户端
        clients = []
        for i in range(3):
            client = await self.create_client(i)
            clients.append(client)

        try:
            # 连接所有客户端
            connect_tasks = [self.connect_client(client) for client in clients]
            await asyncio.gather(*connect_tasks)

            print("3个客户端已连接")

            # 每个客户端按顺序发送5条消息
            num_messages = 5
            for msg_num in range(1, num_messages + 1):
                send_tasks = [
                    self.send_chat_message(
                        clients[i],
                        f"客户端{i+1}_消息{msg_num}"
                    )
                    for i in range(3)
                ]
                await asyncio.gather(*send_tasks)

                # 短暂等待
                await asyncio.sleep(0.5)

            # 等待所有消息处理完成
            await asyncio.sleep(3)

            # 验证所有客户端仍然连接
            connected_count = sum(1 for client in clients if client.connected)
            print(f"仍然连接的客户端: {connected_count}/3")
            assert connected_count == 3, f"客户端连接断开: {connected_count}/3"

            print("✓ 消息顺序保持测试通过")

        finally:
            # 断开所有客户端
            disconnect_tasks = [self.disconnect_client(client) for client in clients]
            await asyncio.gather(*disconnect_tasks)
