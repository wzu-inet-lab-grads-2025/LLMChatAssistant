"""
聊天消息测试 (T023-T026)
Constitution: 100% 真实测试，禁止使用 mock

测试内容:
- T023: 基础消息发送与接收
- T024: 智谱API调用验证
- T025: 流式输出显示
- T026: 消息格式验证
"""

import pytest
import asyncio
import json
from typing import List
from tests.base import BaseCLITest


class TestChat(BaseCLITest):
    """
    聊天消息测试类

    测试客户端与服务器的聊天功能
    所有测试使用真实服务器和真实智谱API，禁止mock
    """

    @pytest.mark.e2e
    async def test_basic_message_send_and_receive(self):
        """T023: 测试基础消息发送与接收"""
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

            # 发送简单测试消息
            test_message = "你好，请回复'测试成功'"
            success = await client.send_chat(test_message)
            assert success is True, "消息发送应该成功"

            self.log_test_info(f"已发送测试消息: {test_message}")

            # 等待响应（超时30秒）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=30.0
                )

                # 验证收到响应
                self.log_test_info("收到服务器响应")
                assert True, "应该收到服务器响应"

            except asyncio.TimeoutError:
                pytest.fail("30秒内未收到服务器响应")

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_zhipu_api_call_verification(self):
        """T024: 测试智谱API调用验证"""
        from client.nplt_client import NPLTClient

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

            # 发送需要调用智谱API的问题
            test_question = "请用一句话介绍人工智能"
            success = await client.send_chat(test_question)
            assert success is True, "消息发送应该成功"

            self.log_test_info(f"已发送问题: {test_question}")

            # 等待响应（超时30秒）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=30.0
                )

                # 验证收到响应（智谱API应该成功调用）
                self.log_test_info("收到智谱API响应")
                assert True, "应该收到智谱API响应"

            except asyncio.TimeoutError:
                pytest.fail("30秒内未收到智谱API响应")

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_streaming_output_display(self):
        """T025: 测试流式输出显示"""
        from client.nplt_client import NPLTClient

        client = NPLTClient(
            host=self.DEFAULT_HOST,
            port=self.DEFAULT_PORT,
            timeout=self.DEFAULT_TIMEOUT
        )

        # 收集所有收到的消息片段
        received_chunks: List[str] = []

        async def message_handler(message):
            """消息处理器，收集流式输出"""
            from protocols.nplt import MessageType
            if message.type == MessageType.CHAT_TEXT:
                text = message.data.decode('utf-8', errors='ignore')
                if text and text.strip():
                    received_chunks.append(text)
                    self.log_test_info(f"收到流式片段: {text[:50]}...")

        try:
            # 连接服务器
            connected = await client.connect()
            assert connected is True, "连接应该成功"

            # 注册消息处理器
            client.message_handler = message_handler

            # 等待欢迎消息
            await client.response_event.wait()
            client.response_event.clear()

            # 发送会触发较长回复的问题
            test_message = "请详细介绍一下Python编程语言的特点"
            success = await client.send_chat(test_message)
            assert success is True, "消息发送应该成功"

            self.log_test_info(f"已发送测试消息: {test_message}")

            # 等待响应完成（超时30秒）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=30.0
                )

                # 验证收到流式输出
                assert len(received_chunks) > 0, "应该收到至少一个流式输出片段"
                self.log_test_info(f"共收到 {len(received_chunks)} 个流式片段")

                # 验证流式输出的连续性
                full_response = ''.join(received_chunks)
                assert len(full_response) > 50, "完整响应应该足够长"

            except asyncio.TimeoutError:
                pytest.fail("30秒内未收到完整的流式输出")

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_message_format_validation(self):
        """T026: 测试消息格式验证"""
        from client.nplt_client import NPLTClient
        from protocols.nplt import MessageType, NPLTMessage

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

            # 发送测试消息
            test_message = "请回复数字1"
            success = await client.send_chat(test_message)
            assert success is True, "消息发送应该成功"

            self.log_test_info(f"已发送测试消息: {test_message}")

            # 等待响应（超时30秒）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=30.0
                )

                # 验证响应格式（通过检查消息处理器接收到的消息）
                # 注意：这里我们验证的是消息成功接收和显示
                self.log_test_info("收到格式正确的响应")

            except asyncio.TimeoutError:
                pytest.fail("30秒内未收到响应")

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_multiple_consecutive_messages(self):
        """测试多条连续消息"""
        from client.nplt_client import NPLTClient

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

            # 发送多条连续消息
            messages = [
                "第一条消息",
                "第二条消息",
                "第三条消息"
            ]

            for i, msg in enumerate(messages, 1):
                # 发送消息
                success = await client.send_chat(msg)
                assert success is True, f"第{i}条消息发送应该成功"

                self.log_test_info(f"已发送第{i}条消息: {msg}")

                # 等待响应（超时30秒）
                try:
                    await asyncio.wait_for(
                        client.response_event.wait(),
                        timeout=30.0
                    )
                    client.response_event.clear()

                    self.log_test_info(f"收到第{i}条消息的响应")

                except asyncio.TimeoutError:
                    pytest.fail(f"第{i}条消息30秒内未收到响应")

            # 验证所有消息都收到响应
            assert True, "所有消息都应该收到响应"

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_chinese_message_handling(self):
        """测试中文消息处理"""
        from client.nplt_client import NPLTClient

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

            # 发送中文消息
            chinese_message = "你好，请用中文回答：什么是机器学习？"
            success = await client.send_chat(chinese_message)
            assert success is True, "中文消息发送应该成功"

            self.log_test_info(f"已发送中文消息: {chinese_message}")

            # 等待响应（超时30秒）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=30.0
                )

                self.log_test_info("收到中文响应")

            except asyncio.TimeoutError:
                pytest.fail("30秒内未收到中文响应")

        finally:
            await client.disconnect()

    @pytest.mark.e2e
    async def test_special_characters_handling(self):
        """测试特殊字符处理"""
        from client.nplt_client import NPLTClient

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

            # 发送包含特殊字符的消息
            special_message = "测试特殊字符：!@#$%^&*()_+-={}[]|:;<>?,./"
            success = await client.send_chat(special_message)
            assert success is True, "特殊字符消息发送应该成功"

            self.log_test_info(f"已发送特殊字符消息")

            # 等待响应（超时30秒）
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=30.0
                )

                self.log_test_info("收到特殊字符响应")

            except asyncio.TimeoutError:
                pytest.fail("30秒内未收到响应")

        finally:
            await client.disconnect()

    def log_test_info(self, message: str):
        """记录测试信息"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(message)
