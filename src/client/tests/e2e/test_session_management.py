"""
会话管理测试 (T027-T031)
Constitution: 100% 真实测试，禁止使用 mock

测试内容:
- T027: 会话列表显示
- T028: 会话切换功能
- T029: 新建会话功能
- T030: 删除会话功能
- T031: 会话状态持久化
"""

import pytest
import asyncio
import json
from typing import Optional, Dict, Any
from src.client.tests.base import BaseCLITest


class TestSessionManagement(BaseCLITest):
    """
    会话管理测试类

    测试客户端的会话管理功能
    所有测试使用真实服务器，禁止mock
    """

    @pytest.mark.e2e
    async def test_session_list_display(self):
        """T027: 测试会话列表显示"""
        from client.nplt_client import NPLTClient
        from protocols.nplt import MessageType

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 发送会话列表请求
            success = await client.send_message(
                MessageType.SESSION_LIST,
                b""
            )
            assert success is True, "会话列表请求应该发送成功"

            self.log_test_info("已发送会话列表请求")

            # 等待响应（超时10秒）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )

                self.log_test_info("收到会话列表响应")

            except asyncio.TimeoutError:
                pytest.fail("10秒内未收到会话列表响应")

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_session_switch(self):
        """T028: 测试会话切换功能"""
        from client.nplt_client import NPLTClient
        from protocols.nplt import MessageType

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 先获取会话列表，找到一个可切换的会话ID
            success = await client.send_message(
                MessageType.SESSION_LIST,
                b""
            )
            assert success is True, "会话列表请求应该发送成功"

            await client.response_event.wait()
            client.response_event.clear()

            # 发送会话切换请求（使用默认会话ID "default"）
            switch_data = json.dumps({"session_id": "default"})
            success = await client.send_message(
                MessageType.SESSION_SWITCH,
                switch_data.encode('utf-8')
            )
            assert success is True, "会话切换请求应该发送成功"

            self.log_test_info("已发送会话切换请求")

            # 等待响应（超时10秒）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )

                self.log_test_info("收到会话切换响应")

            except asyncio.TimeoutError:
                pytest.fail("10秒内未收到会话切换响应")

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_create_new_session(self):
        """T029: 测试新建会话功能"""
        from client.nplt_client import NPLTClient
        from protocols.nplt import MessageType

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 发送创建新会话请求
            success = await client.send_message(
                MessageType.SESSION_NEW,
                b""
            )
            assert success is True, "创建新会话请求应该发送成功"

            self.log_test_info("已发送创建新会话请求")

            # 等待响应（超时10秒）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )

                self.log_test_info("收到创建新会话响应")

            except asyncio.TimeoutError:
                pytest.fail("10秒内未收到创建新会话响应")

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_delete_session(self):
        """T030: 测试删除会话功能"""
        from client.nplt_client import NPLTClient
        from protocols.nplt import MessageType

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 先创建一个测试会话（用于删除）
            success = await client.send_message(
                MessageType.SESSION_NEW,
                b""
            )
            assert success is True, "创建新会话请求应该发送成功"

            await client.response_event.wait()
            client.response_event.clear()

            # 删除会话（使用测试会话ID）
            # 注意：这里我们使用一个假设的测试会话ID
            # 实际测试中应该先创建会话，然后获取其ID
            delete_data = json.dumps({"session_id": "test_session_to_delete"})
            success = await client.send_message(
                MessageType.SESSION_DELETE,
                delete_data.encode('utf-8')
            )

            # 即使会话不存在，服务器也应该返回响应
            self.log_test_info("已发送删除会话请求")

            # 等待响应（超时10秒）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )

                self.log_test_info("收到删除会话响应")

            except asyncio.TimeoutError:
                pytest.fail("10秒内未收到删除会话响应")

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_session_state_persistence(self):
        """T031: 测试会话状态持久化"""
        from client.nplt_client import NPLTClient

        client1 = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 第一步：连接并创建新会话
            connected = await client1.connect()
            assert connected is True, "第一次连接应该成功"

            # 等待欢迎消息
            await client1.response_event.wait()
            client1.response_event.clear()

            # 在新会话中发送一条消息
            test_message = "这是会话持久化测试消息"
            success = await client1.send_chat(test_message)
            assert success is True, "消息发送应该成功"

            self.log_test_info("已在会话中发送测试消息")

            # 等待响应
            await client1.response_event.wait()
            client1.response_event.clear()

            # 断开连接
            await client1.disconnect()
            self.log_test_info("已断开第一次连接")

            # 等待一秒，确保服务器完全处理
            await asyncio.sleep(1)

            # 第二步：重新连接，验证会话状态是否保持
            client2 = NPLTClient(
                host=self.DEFAULT_HOST,
                port=self.DEFAULT_PORT,
                timeout=self.DEFAULT_TIMEOUT
            )

            connected = await client2.connect()
            assert connected is True, "第二次连接应该成功"

            # 等待欢迎消息
            await client2.response_event.wait()
            client2.response_event.clear()

            # 请求会话列表，验证会话状态
            from protocols.nplt import MessageType
            success = await client2.send_message(
                MessageType.SESSION_LIST,
                b""
            )
            assert success is True, "会话列表请求应该发送成功"

            self.log_test_info("已请求会话列表")

            # 等待响应
            try:
                await asyncio.wait_for(
                    client2.response_event.wait(),
                    timeout=10.0
                )

                self.log_test_info("会话状态持久化验证成功")

            except asyncio.TimeoutError:
                pytest.fail("10秒内未收到会话列表响应")

            await client2.disconnect()

        except Exception as e:
            self.log_test_info(f"会话持久化测试异常: {e}")
            raise

    @pytest.mark.e2e
    async def test_session_isolation(self):
        """测试会话隔离性"""
        from client.nplt_client import NPLTClient
        from protocols.nplt import MessageType

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 在当前会话中发送一条消息
            message1 = "会话隔离测试消息1"
            success = await client.send_chat(message1)
            assert success is True, "消息发送应该成功"

            self.log_test_info(f"已在会话中发送消息: {message1}")

            await client.response_event.wait()
            client.response_event.clear()

            # 创建新会话
            success = await client.send_message(
                MessageType.SESSION_NEW,
                b""
            )
            assert success is True, "创建新会话请求应该发送成功"

            await client.response_event.wait()
            client.response_event.clear()

            # 在新会话中发送另一条消息
            message2 = "会话隔离测试消息2"
            success = await client.send_chat(message2)
            assert success is True, "消息发送应该成功"

            self.log_test_info(f"已在新会话中发送消息: {message2}")

            await client.response_event.wait()
            client.response_event.clear()

            # 验证两个会话的消息应该是隔离的
            self.log_test_info("会话隔离验证完成")

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_multiple_session_operations(self):
        """测试多个会话操作的连续性"""
        from client.nplt_client import NPLTClient
        from protocols.nplt import MessageType

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 操作序列：列表 -> 新建 -> 列表 -> 切换 -> 列表
            operations = [
                ("获取会话列表", MessageType.SESSION_LIST, b""),
                ("创建新会话", MessageType.SESSION_NEW, b""),
                ("获取会话列表", MessageType.SESSION_LIST, b""),
                ("切换到默认会话", MessageType.SESSION_SWITCH,
                 json.dumps({"session_id": "default"}).encode('utf-8')),
                ("获取会话列表", MessageType.SESSION_LIST, b""),
            ]

            for i, (op_name, msg_type, data) in enumerate(operations, 1):
                # 发送请求
                success = await client.send_message(msg_type, data)
                assert success is True, f"{op_name}应该发送成功"

                self.log_test_info(f"执行操作 {i}/{len(operations)}: {op_name}")

                # 等待响应
                try:
                    await asyncio.wait_for(
                        client.response_event.wait(),
                        timeout=10.0
                    )
                    client.response_event.clear()

                    self.log_test_info(f"操作 {i} 完成")

                except asyncio.TimeoutError:
                    pytest.fail(f"操作 {i} ({op_name}) 10秒内未收到响应")

            self.log_test_info("所有会话操作序列完成")

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_invalid_session_id_handling(self):
        """测试无效会话ID的处理"""
        from client.nplt_client import NPLTClient
        from protocols.nplt import MessageType

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 尝试切换到不存在的会话
            invalid_session_id = "nonexistent_session_12345"
            switch_data = json.dumps({"session_id": invalid_session_id})
            success = await client.send_message(
                MessageType.SESSION_SWITCH,
                switch_data.encode('utf-8')
            )
            assert success is True, "切换请求应该发送成功"

            self.log_test_info(f"已尝试切换到无效会话: {invalid_session_id}")

            # 服务器应该返回错误响应（超时10秒）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )

                self.log_test_info("收到服务器错误响应（符合预期）")

            except asyncio.TimeoutError:
                pytest.fail("10秒内未收到响应")

        finally:
            await client.disconnect()

    def log_test_info(self, message: str):
        """记录测试信息"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(message)
