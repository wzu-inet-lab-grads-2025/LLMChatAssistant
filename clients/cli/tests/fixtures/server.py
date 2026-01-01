"""
真实服务器 Fixture
Constitution: 启动真实服务器用于测试，禁止使用 mock
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncContextManager, Optional

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()


class RealServerFixture:
    """
    真实服务器 Fixture

    ⚠️  Constitution: 必须使用真实服务器，禁止 mock

    注意: 此 fixture 不启动服务器（服务器应手动启动）
    而是验证服务器是否运行并提供连接信息
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9999, rdt_port: int = 9998):
        self.host = host
        self.port = port
        self.rdt_port = rdt_port
        self.running = False

    async def check_server(self) -> bool:
        """检查服务器是否运行"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            self.running = (result == 0)
            return self.running
        except Exception:
            self.running = False
            return False

    def get_server_info(self) -> dict:
        """获取服务器信息"""
        return {
            "host": self.host,
            "port": self.port,
            "rdt_port": self.rdt_port,
            "running": self.running
        }


@pytest.fixture
async def real_server():
    """
    真实服务器 fixture

    使用方法:
        @pytest.mark.asyncio
        async def test_something(real_server):
            assert real_server["running"]
            # 使用 real_server["host"] 和 real_server["port"]
    """
    server = RealServerFixture()
    is_running = await server.check_server()

    if not is_running:
        pytest.skip(
            f"服务器未运行！请先启动服务器:\n"
            f"  python -m server.main"
        )

    return server.get_server_info()


@pytest.fixture
def server_config():
    """服务器配置 fixture"""
    return {
        "host": os.getenv("SERVER_HOST", "127.0.0.1"),
        "port": int(os.getenv("SERVER_PORT", "9999")),
        "rdt_port": int(os.getenv("RDT_PORT", "9998")),
        "timeout": int(os.getenv("SERVER_TIMEOUT", "30")),
    }
