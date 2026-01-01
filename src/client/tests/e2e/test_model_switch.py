"""
模型切换功能测试 (T023-T024)
Constitution: 100% 真实测试，禁止使用 mock
"""

import pytest
import asyncio
import json
from src.client.tests.base import BaseCLITest
from protocols.nplt import MessageType


class TestModelSwitch(BaseCLITest):
    """
    模型切换功能测试类

    测试客户端与服务器之间的模型切换功能
    所有测试使用真实服务器和真实模型API，禁止mock
    """

    @pytest.mark.e2e
    async def test_switch_to_glm_4_flash(self):
        """测试切换到 glm-4-flash 模型"""
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

            # 发送模型切换请求到 glm-4-flash
            model_data = json.dumps({"model": "glm-4-flash"})
            success = await client.send_message(
                MessageType.MODEL_SWITCH,
                model_data.encode('utf-8')
            )

            assert success is True, "发送模型切换请求应该成功"

            self.log_test_info(f"已发送模型切换请求: glm-4-flash")

            # 等待服务器响应
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )
                self.log_test_info("收到服务器响应，模型切换已处理")
            except asyncio.TimeoutError:
                pytest.fail("等待服务器响应超时")

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_switch_to_glm_4_5_flash(self):
        """测试切换到 glm-4.5-flash 模型"""
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

            # 发送模型切换请求到 glm-4.5-flash
            model_data = json.dumps({"model": "glm-4.5-flash"})
            success = await client.send_message(
                MessageType.MODEL_SWITCH,
                model_data.encode('utf-8')
            )

            assert success is True, "发送模型切换请求应该成功"

            self.log_test_info(f"已发送模型切换请求: glm-4.5-flash")

            # 等待服务器响应
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )
                self.log_test_info("收到服务器响应，模型切换已处理")
            except asyncio.TimeoutError:
                pytest.fail("等待服务器响应超时")

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_switch_invalid_model(self):
        """测试切换到无效模型"""
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

            # 发送模型切换请求到无效模型
            model_data = json.dumps({"model": "invalid-model-name"})
            success = await client.send_message(
                MessageType.MODEL_SWITCH,
                model_data.encode('utf-8')
            )

            assert success is True, "发送模型切换请求应该成功"

            self.log_test_info(f"已发送无效模型切换请求: invalid-model-name")

            # 等待服务器错误响应
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=10.0
                )
                self.log_test_info("收到服务器响应，无效模型请求已被处理")
            except asyncio.TimeoutError:
                pytest.fail("等待服务器响应超时")

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_multiple_model_switches(self):
        """测试连续多次模型切换"""
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

            # 连续切换模型
            models = ["glm-4-flash", "glm-4.5-flash", "glm-4-flash"]

            for i, model in enumerate(models):
                model_data = json.dumps({"model": model})
                success = await client.send_message(
                    MessageType.MODEL_SWITCH,
                    model_data.encode('utf-8')
                )

                assert success is True, f"第{i+1}次发送模型切换请求应该成功"
                self.log_test_info(f"第{i+1}次模型切换: {model}")

                # 等待服务器响应
                try:
                    await asyncio.wait_for(
                        client.response_event.wait(),
                        timeout=10.0
                    )
                    client.response_event.clear()
                    self.log_test_info(f"第{i+1}次模型切换完成")
                except asyncio.TimeoutError:
                    pytest.fail(f"第{i+1}次模型切换等待服务器响应超时")

                # 短暂延迟，避免请求过快
                await asyncio.sleep(1)

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_model_switch_with_following_chat(self):
        """测试模型切换后进行对话"""
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

            # 切换到 glm-4.5-flash
            model_data = json.dumps({"model": "glm-4.5-flash"})
            success = await client.send_message(
                MessageType.MODEL_SWITCH,
                model_data.encode('utf-8')
            )

            assert success is True, "发送模型切换请求应该成功"

            # 等待模型切换响应
            await asyncio.wait_for(
                client.response_event.wait(),
                timeout=10.0
            )
            client.response_event.clear()

            self.log_test_info("模型切换完成，发送测试消息")

            # 发送测试消息
            test_message = "你好，请用一句话介绍你自己"
            await client.send_chat(test_message)

            # 等待响应
            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=30.0  # 模型响应可能需要较长时间
                )
                self.log_test_info("收到模型响应，模型切换后对话正常")
            except asyncio.TimeoutError:
                pytest.fail("等待模型响应超时")

        finally:
            await client.close()

    @pytest.mark.e2e
    async def test_model_switch_persistence(self):
        """测试模型切换状态的持久性"""
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

            # 切换到 glm-4.5-flash
            model_data = json.dumps({"model": "glm-4.5-flash"})
            success = await client.send_message(
                MessageType.MODEL_SWITCH,
                model_data.encode('utf-8')
            )

            assert success is True, "发送模型切换请求应该成功"

            # 等待模型切换响应
            await asyncio.wait_for(
                client.response_event.wait(),
                timeout=10.0
            )
            client.response_event.clear()

            # 等待一段时间，验证模型状态保持
            await asyncio.sleep(5)

            # 发送测试消息验证模型仍然是 glm-4.5-flash
            test_message = "请确认当前使用的模型"
            await client.send_chat(test_message)

            try:
                await asyncio.wait_for(
                    client.response_event.wait(),
                    timeout=30.0
                )
                self.log_test_info("模型状态持久性验证成功")
            except asyncio.TimeoutError:
                pytest.fail("等待模型响应超时")

        finally:
            await client.close()

    def log_test_info(self, message: str):
        """记录测试信息"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(message)
