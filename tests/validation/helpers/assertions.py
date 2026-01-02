"""
断言辅助类

提供测试中常用的断言方法，统一断言逻辑和错误消息格式。
"""

class AssertionHelper:
    """断言辅助类"""

    @staticmethod
    def assert_response_time(duration: float, max_duration: float, operation: str):
        """
        断言响应时间在合理范围内

        Args:
            duration: 实际耗时（秒）
            max_duration: 最大允许耗时（秒）
            operation: 操作名称（用于错误消息）

        Raises:
            AssertionError: 如果超时
        """
        assert duration <= max_duration, \
            f"{operation}耗时{duration:.2f}秒，超过最大限制{max_duration}秒"

    @staticmethod
    def assert_not_empty(response, message: str = "响应为空"):
        """
        断言响应非空

        Args:
            response: 响应对象
            message: 错误消息

        Raises:
            AssertionError: 如果响应为空
        """
        assert response is not None, message
        if isinstance(response, (str, list, dict)):
            assert len(response) > 0, message

    @staticmethod
    def assert_api_success(response: dict):
        """
        断言API调用成功

        Args:
            response: API响应字典

        Raises:
            AssertionError: 如果API调用失败
        """
        assert response.get("success", False), \
            f"API调用失败: {response.get('error', 'Unknown error')}"

    @staticmethod
    def assert_file_exists(file_path: str):
        """
        断言文件存在

        Args:
            file_path: 文件路径

        Raises:
            AssertionError: 如果文件不存在
        """
        from pathlib import Path
        assert Path(file_path).exists(), f"文件不存在: {file_path}"
