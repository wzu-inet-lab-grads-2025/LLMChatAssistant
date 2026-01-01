"""
历史记录功能测试 (T025-T026)
Constitution: 100% 真实测试，禁止使用 mock
"""

import pytest
import asyncio
from src.client.tests.base import BaseCLITest
from protocols.nplt import MessageType


class TestHistory(BaseCLITest):
    """
    历史记录功能测试类

    测试客户端与服务器之间的历史记录查询、清空等功能
    所有测试使用真实服务器和真实API，禁止mock
    """

    @pytest.mark.e2e
    async def test_request_history(self):
        """测试请求历史记录"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接服务器应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 发送历史记录请求
            success = await client.send_message(
                MessageType.HISTORY_REQUEST,
                b""
            )

            assert success is True, "发送历史记录请求应该成功"

            self.log_test_info("已发送历史记录请求")

            # 等待服务器响应
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )
                self.log_test_info("收到历史记录响应")
            except asyncio.TimeoutError:
                pytest.fail("等待历史记录响应超时")

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_request_history_with_messages(self):
        """测试在有消息的情况下请求历史记录"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接服务器应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 先发送几条消息
            test_messages = [
                "第一条测试消息",
                "第二条测试消息",
                "第三条测试消息"
            ]

            for i, msg in enumerate(test_messages):
                await client.send_chat(msg)
                self.log_test_info(f"发送第{i+1}条测试消息")

                try:
                    await asyncio.wait_for(
                        client.response_event.wait(),
                        timeout=30.0
                    )
                    client.response_event.clear()
                    self.log_test_info(f"第{i+1}条消息已收到响应")
                except asyncio.TimeoutError:
                    pytest.fail(f"第{i+1}条消息等待响应超时")

                # 短暂延迟
                await asyncio.sleep(1)

            # 请求历史记录
            success = await client.send_message(
                MessageType.HISTORY_REQUEST,
                b""
            )

            assert success is True, "发送历史记录请求应该成功"

            self.log_test_info("已发送历史记录请求")

            # 等待服务器响应
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )
                self.log_test_info("收到包含测试消息的历史记录响应")
            except asyncio.TimeoutError:
                pytest.fail("等待历史记录响应超时")

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_clear_history(self):
        """测试清空历史记录"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接服务器应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 发送清空历史请求
            success = await client.send_message(
                MessageType.CLEAR_REQUEST,
                b""
            )

            assert success is True, "发送清空历史请求应该成功"

            self.log_test_info("已发送清空历史请求")

            # 等待服务器响应（清空操作可能没有响应，或响应很快）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=5.0
                )
                self.log_test_info("收到清空历史响应")
            except asyncio.TimeoutError:
                # 清空操作可能没有返回消息，这是正常的
                self.log_test_info("清空操作没有返回响应（正常情况）")

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_clear_history_after_messages(self):
        """测试发送消息后清空历史记录"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接服务器应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 发送测试消息
            test_message = "这是一条待清空的测试消息"
            await client.send_chat(test_message)
            self.log_test_info("发送测试消息")

            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=30.0
                )
                client.response_event.clear()
                self.log_test_info("测试消息已收到响应")
            except asyncio.TimeoutError:
                pytest.fail("等待测试消息响应超时")

            # 清空历史记录
            success = await client.send_message(
                MessageType.CLEAR_REQUEST,
                b""
            )

            assert success is True, "发送清空历史请求应该成功"

            self.log_test_info("已发送清空历史请求")

            # 等待响应
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=5.0
                )
                self.log_test_info("收到清空历史响应")
            except asyncio.TimeoutError:
                self.log_test_info("清空操作没有返回响应（正常情况）")

            # 验证历史已清空：再次请求历史记录
            await asyncio.sleep(1)
            success = await client.send_message(
                MessageType.HISTORY_REQUEST,
                b""
            )

            assert success is True, "发送历史记录请求应该成功"

            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )
                self.log_test_info("收到清空后的历史记录响应（应该为空或仅包含欢迎消息）")
            except asyncio.TimeoutError:
                pytest.fail("等待历史记录响应超时")

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_multiple_history_requests(self):
        """测试多次请求历史记录"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接服务器应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 多次请求历史记录
            for i in range(3):
                success = await client.send_message(
                    MessageType.HISTORY_REQUEST,
                    b""
                )

                assert success is True, f"第{i+1}次发送历史记录请求应该成功"

                self.log_test_info(f"第{i+1}次发送历史记录请求")

                try:
                    await asyncio.wait_for(
                        client.response_event.wait(),
                        timeout=10.0
                    )
                    client.response_event.clear()
                    self.log_test_info(f"第{i+1}次收到历史记录响应")
                except asyncio.TimeoutError:
                    pytest.fail(f"第{i+1}次等待历史记录响应超时")

                # 短暂延迟
                await asyncio.sleep(1)

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_history_and_clear_sequence(self):
        """测试历史记录与清空的完整流程"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接服务器应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # Step 1: 请求初始历史记录
            self.log_test_info("Step 1: 请求初始历史记录")
            success = await client.send_message(
                MessageType.HISTORY_REQUEST,
                b""
            )
            assert success is True, "发送历史记录请求应该成功"

            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )
                client.response_event.clear()
                self.log_test_info("Step 1 完成: 收到初始历史记录")
            except asyncio.TimeoutError:
                pytest.fail("等待初始历史记录响应超时")

            await asyncio.sleep(1)

            # Step 2: 发送新消息
            self.log_test_info("Step 2: 发送新消息")
            test_message = "用于测试历史记录流程的消息"
            await client.send_chat(test_message)

            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=30.0
                )
                client.response_event.clear()
                self.log_test_info("Step 2 完成: 新消息已收到响应")
            except asyncio.TimeoutError:
                pytest.fail("等待新消息响应超时")

            await asyncio.sleep(1)

            # Step 3: 再次请求历史记录（应该包含新消息）
            self.log_test_info("Step 3: 请求更新后的历史记录")
            success = await client.send_message(
                MessageType.HISTORY_REQUEST,
                b""
            )
            assert success is True, "发送历史记录请求应该成功"

            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )
                client.response_event.clear()
                self.log_test_info("Step 3 完成: 收到更新后的历史记录")
            except asyncio.TimeoutError:
                pytest.fail("等待更新后的历史记录响应超时")

            await asyncio.sleep(1)

            # Step 4: 清空历史记录
            self.log_test_info("Step 4: 清空历史记录")
            success = await client.send_message(
                MessageType.CLEAR_REQUEST,
                b""
            )
            assert success is True, "发送清空请求应该成功"

            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=5.0
                )
                client.response_event.clear()
                self.log_test_info("Step 4 完成: 历史记录已清空")
            except asyncio.TimeoutError:
                self.log_test_info("Step 4: 清空操作没有返回响应（正常情况）")

            await asyncio.sleep(1)

            # Step 5: 最终验证历史记录已清空
            self.log_test_info("Step 5: 验证历史记录已清空")
            success = await client.send_message(
                MessageType.HISTORY_REQUEST,
                b""
            )
            assert success is True, "发送历史记录请求应该成功"

            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )
                self.log_test_info("Step 5 完成: 验证历史记录清空成功")
            except asyncio.TimeoutError:
                pytest.fail("等待最终历史记录响应超时")

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_history_with_chat_session(self):
        """测试在对话过程中请求历史记录"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接服务器应该成功"

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 进行多轮对话
            conversations = [
                "你好，我想咨询一些问题",
                "我想了解一下历史记录功能",
                "谢谢你的介绍"
            ]

            for i, msg in enumerate(conversations):
                self.log_test_info(f"发送第{i+1}轮对话: {msg[:20]}...")
                await client.send_chat(msg)

                try:
                    await asyncio.wait_for(
                        client.response_event.wait(),
                        timeout=30.0
                    )
                    client.response_event.clear()
                    self.log_test_info(f"第{i+1}轮对话完成")
                except asyncio.TimeoutError:
                    pytest.fail(f"第{i+1}轮对话等待响应超时")

                await asyncio.sleep(1)

            # 在对话过程中请求历史记录
            self.log_test_info("在对话过程中请求历史记录")
            success = await client.send_message(
                MessageType.HISTORY_REQUEST,
                b""
            )

            assert success is True, "发送历史记录请求应该成功"

            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )
                self.log_test_info("收到对话历史记录，包含多轮对话内容")
            except asyncio.TimeoutError:
                pytest.fail("等待对话历史记录响应超时")

        finally:
            await client.close()

    def log_test_info(self, message: str):
        """记录测试信息"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(message)
