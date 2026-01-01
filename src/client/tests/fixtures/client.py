"""
真实客户端 Fixture
Constitution: 创建真实客户端用于测试，禁止使用 mock
"""

import asyncio
from typing import Optional

import pytest

from client.main import ClientMain


@pytest.fixture
async def real_client(real_server):
    """
    真实客户端 fixture

    自动连接到服务器，测试完成后自动断开

    使用方法:
        @pytest.mark.asyncio
        async def test_chat(real_client):
            await real_client.send_message("你好")
    """
    client = ClientMain(
        host=real_server["host"],
        port=real_server["port"]
    )

    # 连接客户端
    try:
        connected = await client.connect()
        if not connected:
            pytest.fail("客户端连接失败")
    except Exception as e:
        pytest.fail(f"客户端连接异常: {e}")

    yield client

    # 清理：断开连接
    try:
        await client.close()
    except Exception:
        pass


@pytest.fixture
def client_config():
    """客户端配置 fixture"""
    return {
        "host": "127.0.0.1",
        "port": 9999,
        "timeout": 30,
        "auto_reconnect": True,
        "max_retries": 3,
        "default_model": "glm-4-flash",
    }


@pytest.fixture
def temp_session(real_client):
    """
    临时会话 fixture

    为测试创建一个临时会话，测试结束后自动清理
    """
    session_id = None

    async def create_session():
        # 创建新会话的逻辑
        # 这里的实现取决于客户端的会话管理 API
        pass

    async def cleanup_session():
        # 清理会话的逻辑
        pass

    # 创建会话
    session_id = await create_session()

    yield session_id

    # 清理会话
    await cleanup_session()
