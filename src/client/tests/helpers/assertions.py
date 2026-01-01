"""
自定义断言助手
提供专门的断言方法，验证API调用、协议格式、响应时间等
"""

import time
from typing import Any, Optional


class AssertionHelper:
    """断言助手类"""

    @staticmethod
    def assert_api_success(response: dict, operation: str = "API调用"):
        """
        断言 API 调用成功

        Args:
            response: API 响应字典
            operation: 操作名称
        """
        assert response is not None, f"{operation}: 响应为空"
        assert "success" in response or "error" not in response, \
            f"{operation}: API返回错误"
        assert response.get("success", True), \
            f"{operation}: success=False"

    @staticmethod
    def assert_response_time(
        elapsed: float,
        max_seconds: float,
        operation: str
    ):
        """
        断言响应时间符合要求

        Args:
            elapsed: 实际执行时间（秒）
            max_seconds: 最大允许时间（秒）
            operation: 操作名称
        """
        assert elapsed <= max_seconds, \
            f"{operation} 响应时间超时: {elapsed:.2f}s > {max_seconds}s"

    @staticmethod
    def assert_message_format(message: dict):
        """
        断言消息格式符合 NPLT 协议

        Args:
            message: 消息字典
        """
        required_fields = ["role", "content", "timestamp"]
        for field in required_fields:
            assert field in message, f"消息缺少必需字段: {field}"

        assert message["role"] in ["user", "assistant", "system"], \
            f"无效的role: {message['role']}"

        assert isinstance(message["content"], str), \
            f"content 必须是字符串"

    @staticmethod
    def assert_file_metadata(metadata: dict):
        """
        断言文件元数据格式正确

        Args:
            metadata: 文件元数据字典
        """
        required_fields = ["file_id", "filename", "size", "file_path"]
        for field in required_fields:
            assert field in metadata, f"文件元数据缺少字段: {field}"

        assert isinstance(metadata["size"], int), \
            "文件大小必须是整数"

        assert metadata["size"] <= 10 * 1024 * 1024, \
            f"文件大小超过10MB限制: {metadata['size']}"

    @staticmethod
    def assert_session_state(session: dict):
        """
        断言会话状态正确

        Args:
            session: 会话字典
        """
        assert "session_id" in session, "会话缺少 session_id"
        assert "messages" in session, "会话缺少 messages"
        assert "uploaded_files" in session, "会话缺少 uploaded_files"

        assert isinstance(session["messages"], list), \
            "messages 必须是列表"

    @staticmethod
    def assert_tool_call(tool_call: dict):
        """
        断言工具调用记录格式正确

        Args:
            tool_call: 工具调用字典
        """
        required_fields = ["tool_name", "arguments", "status"]
        for field in required_fields:
            assert field in tool_call, f"工具调用缺少字段: {field}"

        assert tool_call["status"] in ["pending", "success", "failed"], \
            f"无效的status: {tool_call['status']}"

        if tool_call["status"] == "success":
            assert "result" in tool_call, "成功状态必须有 result"
