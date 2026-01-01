"""
数据验证助手
验证消息格式、文件完整性、会话状态等
"""

from typing import Any, Dict, List
from datetime import datetime
import hashlib


class DataValidator:
    """数据验证器类"""

    @staticmethod
    def validate_message(message: dict) -> tuple[bool, str]:
        """
        验证消息格式

        Args:
            message: 消息字典

        Returns:
            (是否有效, 错误信息)
        """
        required_fields = ["role", "content", "timestamp"]
        for field in required_fields:
            if field not in message:
                return False, f"缺少必需字段: {field}"

        if message["role"] not in ["user", "assistant", "system"]:
            return False, f"无效的role: {message['role']}"

        if not isinstance(message["content"], str):
            return False, "content 必须是字符串"

        return True, ""

    @staticmethod
    def validate_file_integrity(
        file_path: str,
        expected_hash: str = None,
        expected_size: int = None
    ) -> tuple[bool, str]:
        """
        验证文件完整性

        Args:
            file_path: 文件路径
            expected_hash: 预期的哈希值（可选）
            expected_size: 预期的文件大小（可选）

        Returns:
            (是否有效, 错误信息)
        """
        from pathlib import Path

        filepath = Path(file_path)
        if not filepath.exists():
            return False, f"文件不存在: {file_path}"

        actual_size = filepath.stat().st_size

        # 验证文件大小
        if expected_size is not None and actual_size != expected_size:
            return False, f"文件大小不匹配: {actual_size} != {expected_size}"

        # 验证文件大小限制
        if actual_size > 10 * 1024 * 1024:
            return False, f"文件大小超过10MB限制: {actual_size}"

        # 验证哈希值
        if expected_hash is not None:
            actual_hash = DataValidator._calculate_file_hash(filepath)
            if actual_hash != expected_hash:
                return False, f"文件哈希不匹配: {actual_hash} != {expected_hash}"

        return True, ""

    @staticmethod
    def _calculate_file_hash(filepath) -> str:
        """计算文件 SHA256 哈希"""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def validate_session_state(session: dict) -> tuple[bool, str]:
        """
        验证会话状态

        Args:
            session: 会话字典

        Returns:
            (是否有效, 错误信息)
        """
        required_fields = ["session_id", "messages", "uploaded_files"]
        for field in required_fields:
            if field not in session:
                return False, f"会话缺少字段: {field}"

        if not isinstance(session["messages"], list):
            return False, "messages 必须是列表"

        if not isinstance(session["uploaded_files"], list):
            return False, "uploaded_files 必须是列表"

        return True, ""

    @staticmethod
    def validate_api_response(response: dict) -> tuple[bool, str]:
        """
        验证 API 响应格式

        Args:
            response: API 响应字典

        Returns:
            (是否有效, 错误信息)
        """
        if response is None:
            return False, "响应为空"

        if "error" in response and response["error"]:
            error_msg = response.get("message", "未知错误")
            return False, f"API返回错误: {error_msg}"

        return True, ""

    @staticmethod
    def validate_timestamp(timestamp: Any) -> tuple[bool, str]:
        """
        验证时间戳格式

        Args:
            timestamp: 时间戳（字符串或datetime对象）

        Returns:
            (是否有效, 错误信息)
        """
        if isinstance(timestamp, datetime):
            return True, ""

        if isinstance(timestamp, str):
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return True, ""
            except ValueError:
                return False, f"无效的时间戳格式: {timestamp}"

        return False, f"无效的时间戳类型: {type(timestamp)}"

    @staticmethod
    def validate_model_name(model: str) -> tuple[bool, str]:
        """
        验证模型名称

        Args:
            model: 模型名称

        Returns:
            (是否有效, 错误信息)
        """
        valid_models = ["glm-4-flash", "glm-4.5-flash", "glm-4"]

        if model not in valid_models:
            return False, f"无效的模型名称: {model}"

        return True, ""
