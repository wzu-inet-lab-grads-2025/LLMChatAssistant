"""
测试基类 - CLI客户端测试基础设施
Constitution: 100% 真实测试，禁止使用 mock
"""

import asyncio
import os
import sys
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class BaseCLITest:
    """
    CLI客户端测试基类

    提供客户端启动、服务器连接等公共方法
    所有测试必须继承此类

    Constitution 合规:
    - 使用真实服务器（禁止 mock）
    - 使用真实智谱 API（禁止模拟回复）
    - 所有日志写入 logs/ 文件夹
    """

    # 默认配置
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 9999
    DEFAULT_RDT_PORT = 9998
    DEFAULT_TIMEOUT = 30  # 秒

    # 测试配置
    TEST_MODEL = "glm-4-flash"  # 使用免费模型

    @classmethod
    def setup_class(cls):
        """测试类初始化（所有测试运行前执行一次）"""
        print(f"\n{'='*60}")
        print(f"测试类: {cls.__name__}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # 验证环境
        cls._verify_environment()

        # 初始化测试数据
        cls._setup_test_data()

    @classmethod
    def teardown_class(cls):
        """测试类清理（所有测试运行后执行一次）"""
        print(f"\n{'='*60}")
        print(f"测试类完成: {cls.__name__}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

    def setup_method(self, method):
        """测试方法初始化（每个测试运行前执行）"""
        print(f"\n{'─'*60}")
        print(f"测试: {method.__name__}")
        print(f"{'─'*60}")

    def teardown_method(self, method):
        """测试方法清理（每个测试运行后执行）"""
        print(f"{'─'*60}")
        print(f"测试完成: {method.__name__}")
        print(f"{'─'*60}\n")

    @classmethod
    def _verify_environment(cls):
        """验证测试环境"""
        # 检查 API Key
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ZHIPU_API_KEY 未配置！\n"
                "请在 .env 文件中设置 ZHIPU_API_KEY"
            )

        # 检查 logs 目录
        logs_dir = Path("logs")
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _setup_test_data(cls):
        """设置测试数据"""
        # 测试文件目录
        cls.test_data_dir = project_root / "tests" / "fixtures" / "data"

        if not cls.test_data_dir.exists():
            raise FileNotFoundError(
                f"测试数据目录不存在: {cls.test_data_dir}\n"
                "请运行: python tests/fixtures/test_data.py"
            )

        # 测试临时目录
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="llmchat_test_"))
        cls.temp_dir.mkdir(parents=True, exist_ok=True)

    async def start_server(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        rdt_port: int = DEFAULT_RDT_PORT
    ) -> Dict[str, Any]:
        """
        启动真实服务器（用于集成测试）

        ⚠️  Constitution: 必须使用真实服务器，禁止使用 mock

        Args:
            host: 服务器地址
            port: 服务器端口
            rdt_port: RDT端口

        Returns:
            服务器信息字典
        """
        # 检查服务器是否已运行
        server_running = await self._is_server_running(host, port)

        if server_running:
            print(f"✓ 服务器已在运行: {host}:{port}")
            return {
                "host": host,
                "port": port,
                "rdt_port": rdt_port,
                "running": True
            }

        # 如果服务器未运行，抛出异常（测试需要手动启动服务器）
        raise RuntimeError(
            f"服务器未运行！请先启动服务器：\n"
            f"  python -m server.main\n\n"
            f"或在另一个终端运行：\n"
            f"  .venv/bin/python -m server.main"
        )

    async def _is_server_running(self, host: str, port: int) -> bool:
        """检查服务器是否正在运行"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    async def create_client(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT
    ):
        """
        创建客户端实例（使用新的ClientAPI）

        Args:
            host: 服务器地址
            port: 服务器端口

        Returns:
            客户端实例 (ClientAPI)
        """
        # 使用新的ClientAPI
        try:
            from clients.cli import create_client
            client = await create_client(host=host, port=port, auto_connect=True)
            return client
        except ImportError as e:
            raise ImportError(
                f"无法导入客户端模块: {e}\n"
                f"请确保在项目根目录运行测试"
            )

    async def connect_client(self, client) -> bool:
        """
        连接客户端到服务器

        Args:
            client: 客户端实例

        Returns:
            是否连接成功
        """
        try:
            connected = await client.connect()
            if connected:
                print(f"✓ 客户端已连接: {client.host}:{client.port}")
            return connected
        except Exception as e:
            print(f"✗ 客户端连接失败: {e}")
            return False

    async def disconnect_client(self, client):
        """断开客户端连接"""
        try:
            await client.disconnect()  # ClientAPI使用disconnect()
            print(f"✓ 客户端已断开")
        except Exception as e:
            print(f"✗ 客户端断开失败: {e}")

    def get_test_file(self, filename: str) -> Path:
        """
        获取测试文件路径

        Args:
            filename: 文件名

        Returns:
            文件完整路径
        """
        filepath = self.test_data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"测试文件不存在: {filepath}")
        return filepath

    def create_temp_file(self, content: str, filename: str = None) -> Path:
        """
        创建临时测试文件

        Args:
            content: 文件内容
            filename: 文件名（可选）

        Returns:
            文件路径
        """
        if filename is None:
            filename = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        filepath = self.temp_dir / filename
        filepath.write_text(content, encoding="utf-8")
        return filepath

    def measure_time(self, func, *args, **kwargs) -> tuple:
        """
        测量函数执行时间（同步版本）

        Args:
            func: 要测量的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            (执行结果, 执行时间秒)
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed = end_time - start_time
        return result, elapsed

    async def measure_time_async(self, coro, *args, **kwargs) -> tuple:
        """
        测量异步函数执行时间

        Args:
            coro: 要测量的协程函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            (执行结果, 执行时间秒)
        """
        start_time = time.time()
        result = await coro(*args, **kwargs)
        end_time = time.time()
        elapsed = end_time - start_time
        return result, elapsed

    def assert_response_time(self, elapsed: float, max_seconds: float, operation: str):
        """
        断言响应时间符合要求

        Args:
            elapsed: 实际执行时间（秒）
            max_seconds: 最大允许时间（秒）
            operation: 操作名称
        """
        if elapsed > max_seconds:
            raise AssertionError(
                f"{operation} 响应时间超时: {elapsed:.2f}s > {max_seconds}s"
            )
        print(f"✓ {operation} 响应时间: {elapsed:.3f}s")

    def log_test_result(
        self,
        test_name: str,
        passed: bool,
        details: str = "",
        duration: float = None
    ):
        """
        记录测试结果到日志文件

        Args:
            test_name: 测试名称
            passed: 是否通过
            details: 详细信息
            duration: 执行时间（秒）
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "result": "PASS" if passed else "FAIL",
            "details": details,
            "duration": f"{duration:.3f}s" if duration else None
        }

        # 写入日志
        log_file = Path("logs") / "test_results.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{log_entry}\n")

    def cleanup_temp_files(self):
        """清理临时文件"""
        if self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
            print(f"✓ 已清理临时文件: {self.temp_dir}")

    async def check_server_status(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        """检查服务器状态"""
        running = await self._is_server_running(host, port)
        if running:
            return {"host": host, "port": port, "running": True}
        return None

    async def send_chat_message(self, client, message: str) -> str:
        """发送聊天消息并返回响应"""
        # 这里需要调用实际的客户端方法
        # 暂时返回模拟响应，需要根据实际客户端实现调整
        if hasattr(client, 'send_message'):
            return await client.send_message(message)
        elif hasattr(client, 'chat'):
            return await client.chat(message)
        else:
            raise NotImplementedError("客户端不支持send_message或chat方法")

    async def stream_chat_message(self, client, message: str):
        """流式发送聊天消息"""
        if hasattr(client, 'stream_message'):
            async for chunk in client.stream_message(message):
                yield chunk
        else:
            # 如果不支持流式，回退到普通消息
            response = await self.send_chat_message(client, message)
            yield response

    async def upload_file(self, client, filepath: str) -> dict:
        """上传文件"""
        if hasattr(client, 'upload_file'):
            return await client.upload_file(filepath)
        else:
            # 临时模拟实现
            return {"success": False, "error": "客户端不支持upload_file方法"}

    async def download_file(self, client, token: str, save_path: str) -> dict:
        """下载文件"""
        if hasattr(client, 'download_file'):
            return await client.download_file(token, save_path)
        else:
            # 临时模拟实现
            return {"success": False, "error": "客户端不支持download_file方法"}

    async def list_sessions(self, client) -> list:
        """列出所有会话"""
        if hasattr(client, 'list_sessions'):
            return await client.list_sessions()
        else:
            return []

    async def create_session(self, client, name: str) -> dict:
        """创建新会话"""
        if hasattr(client, 'create_session'):
            return await client.create_session(name)
        else:
            return {"success": False, "error": "客户端不支持create_session方法"}

    async def switch_session(self, client, session_id: str) -> dict:
        """切换会话"""
        if hasattr(client, 'switch_session'):
            return await client.switch_session(session_id)
        else:
            return {"success": False, "error": "客户端不支持switch_session方法"}

    async def delete_session(self, client, session_id: str) -> dict:
        """删除会话"""
        if hasattr(client, 'delete_session'):
            return await client.delete_session(session_id)
        else:
            return {"success": False, "error": "客户端不支持delete_session方法"}

    async def get_history(self, client, offset: int = 0, limit: int = None) -> list:
        """获取历史记录"""
        if hasattr(client, 'get_history'):
            return await client.get_history(offset=offset, limit=limit)
        else:
            return []

    async def clear_history(self, client) -> dict:
        """清空历史记录"""
        if hasattr(client, 'clear_history'):
            return await client.clear_history()
        else:
            return {"success": False, "error": "客户端不支持clear_history方法"}

    async def switch_model(self, client, model: str) -> dict:
        """切换模型"""
        if hasattr(client, 'switch_model'):
            return await client.switch_model(model)
        else:
            return {"success": False, "error": "客户端不支持switch_model方法"}

    async def get_current_model(self, client) -> str:
        """获取当前模型"""
        if hasattr(client, 'get_current_model'):
            return await client.get_current_model()
        else:
            return "unknown"


# 异步测试基类
class AsyncBaseCLITest(BaseCLITest):
    """
    异步测试基类

    用于需要异步执行的测试
    """

    @pytest.mark.asyncio
    async def setup_method(self, method):
        """异步测试方法初始化"""
        await super().setup_method(method)

    @pytest.mark.asyncio
    async def teardown_method(self, method):
        """异步测试方法清理"""
        await super().teardown_method(method)
