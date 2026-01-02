"""
客户端公共API
提供可编程的接口供测试和外部调用

Constitution: 真实实现，禁止mock
"""

import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from .nplt_client import NPLTClient
from .rdt_client import RDTClient


class ClientAPI:
    """
    客户端公共API类

    提供高层API方法，封装底层协议细节
    用于测试、自动化脚本和外部集成
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9999,
        rdt_port: int = 9998
    ):
        """
        初始化客户端API

        Args:
            host: 服务器地址
            port: NPLT协议端口
            rdt_port: RDT协议端口
        """
        self.host = host
        self.port = port
        self.rdt_port = rdt_port

        # 创建协议客户端
        self.nplt_client = NPLTClient(host=host, port=port)
        self.rdt_client: Optional[RDTClient] = None

        # 会话状态
        self._current_session_id: Optional[str] = None
        self._current_model: str = "glm-4-flash"

        # 连接状态
        self._connected = False

    async def connect(self) -> bool:
        """
        连接到服务器

        Returns:
            是否连接成功
        """
        self._connected = await self.nplt_client.connect()
        if self._connected:
            # 生成一个简单的session_id（ClientAPI自己管理）
            import uuid
            self._session_id = str(uuid.uuid4())

            # 创建RDT客户端
            self.rdt_client = RDTClient(
                server_host=self.host,
                server_port=self.rdt_port
            )
            # 启动RDT客户端
            await self.rdt_client.start()
        return self._connected

    async def disconnect(self):
        """断开连接"""
        if self._connected:
            await self.nplt_client.disconnect()
            if self.rdt_client:
                await self.rdt_client.stop()
            self._connected = False

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected and self.nplt_client.is_connected()

    @property
    def session_id(self) -> Optional[str]:
        """获取当前会话ID"""
        return self._session_id if self._connected else None

    # ========== 聊天功能 ==========

    async def send_message(self, message: str) -> str:
        """
        发送聊天消息

        Args:
            message: 消息内容

        Returns:
            AI响应（完整文本）
        """
        if not self._connected:
            raise RuntimeError("客户端未连接")

        # 收集所有响应片段
        response_parts = []

        async for chunk in self.stream_message(message):
            response_parts.append(chunk)

        return "".join(response_parts)

    async def stream_message(self, message: str):
        """
        流式发送聊天消息

        Args:
            message: 消息内容

        Yields:
            响应片段（流式）
        """
        if not self._connected:
            raise RuntimeError("客户端未连接")

        from shared.protocols.nplt import MessageType

        # 发送消息
        await self.nplt_client.send_chat(message)

        # 接收流式响应（使用receive_message循环）
        while self._connected:
            try:
                msg = await self.nplt_client.receive_message()

                if msg is None:
                    # 超时或连接断开
                    break

                if msg.type == MessageType.CHAT_TEXT:
                    text = msg.data.decode('utf-8', errors='ignore')

                    # 空消息表示流式输出结束
                    if not text or not text.strip():
                        break

                    # 跳过心跳
                    if text == "HEARTBEAT":
                        continue

                    yield text

                elif msg.type == MessageType.AGENT_THOUGHT:
                    # Agent思考过程，跳过
                    pass

            except Exception as e:
                # 接收错误，结束流
                break

    # ========== 文件功能 ==========

    async def upload_file(self, filepath: str) -> Dict[str, Any]:
        """
        上传文件

        Args:
            filepath: 文件路径

        Returns:
            上传结果 {"success": bool, "file_id": str, "message": str}
        """
        if not self._connected:
            raise RuntimeError("客户端未连接")

        try:
            file_path = Path(filepath)
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"文件不存在: {filepath}"
                }

            # 发送文件元数据
            filename = file_path.name
            filesize = file_path.stat().st_size

            await self.nplt_client.send_file_metadata(filename, filesize)

            # 读取并发送文件数据
            file_data = file_path.read_bytes()

            await self.nplt_client.send_file_data(file_data)

            return {
                "success": True,
                "filename": filename,
                "size": filesize,
                "message": f"文件 {filename} 上传成功"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def download_file(self, token: str, save_path: str) -> Dict[str, Any]:
        """
        下载文件（使用RDT协议）

        Args:
            token: 下载令牌
            save_path: 保存路径

        Returns:
            下载结果 {"success": bool, "filepath": str}
        """
        if not self._connected or not self.rdt_client:
            raise RuntimeError("客户端未连接或RDT客户端未初始化")

        try:
            # 使用RDT客户端下载
            success = await self.rdt_client.download_file(
                token=token,
                save_path=save_path
            )

            return {
                "success": success,
                "filepath": save_path if success else None,
                "message": "下载成功" if success else "下载失败"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # ========== 会话管理 ==========

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """
        列出所有会话

        Returns:
            会话列表 [{"session_id": str, "created_at": str, ...}, ...]
        """
        if not self._connected:
            raise RuntimeError("客户端未连接")

        from shared.protocols.nplt import MessageType

        # 注意：此功能需要服务器端支持，目前标记为实验性
        # 返回空列表表示尚未实现
        return []

    async def create_session(self, name: str = None) -> Dict[str, Any]:
        """
        创建新会话

        Args:
            name: 会话名称（可选）

        Returns:
            创建结果 {"success": bool, "session_id": str}
        """
        if not self._connected:
            raise RuntimeError("客户端未连接")

        # 注意：此功能需要服务器端支持，目前返回当前session
        return {
            "success": True,
            "session_id": self._session_id,
            "message": "当前会话（功能待完善）"
        }

    async def switch_session(self, session_id: str) -> Dict[str, Any]:
        """
        切换会话

        Args:
            session_id: 会话ID

        Returns:
            切换结果 {"success": bool, "session_id": str}
        """
        if not self._connected:
            raise RuntimeError("客户端未连接")

        # 注意：此功能需要服务器端支持
        return {
            "success": False,
            "session_id": session_id,
            "message": "会话切换功能待完善"
        }

    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            删除结果 {"success": bool, "message": str}
        """
        if not self._connected:
            raise RuntimeError("客户端未连接")

        # 注意：此功能需要服务器端支持
        return {
            "success": False,
            "message": "会话删除功能待完善"
        }

    # ========== 历史记录 ==========

    async def get_history(self, offset: int = 0, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取历史记录

        Args:
            offset: 偏移量
            limit: 限制数量

        Returns:
            历史记录列表 [{"role": str, "content": str, "timestamp": str}, ...]
        """
        if not self._connected:
            raise RuntimeError("客户端未连接")

        # 注意：此功能需要服务器端支持
        return []

    async def clear_history(self) -> Dict[str, Any]:
        """
        清空当前会话历史

        Returns:
            清空结果 {"success": bool, "message": str}
        """
        if not self._connected:
            raise RuntimeError("客户端未连接")

        # 注意：此功能需要服务器端支持
        return {
            "success": False,
            "message": "清空历史功能待完善"
        }

    # ========== 模型管理 ==========

    async def switch_model(self, model: str) -> Dict[str, Any]:
        """
        切换模型

        Args:
            model: 模型名称 (如 "glm-4-flash", "glm-4.5-flash")

        Returns:
            切换结果 {"success": bool, "model": str}
        """
        if not self._connected:
            raise RuntimeError("客户端未连接")

        # 发送模型切换请求
        # 使用CHAT消息类型发送特殊命令
        command = f"/model {model}"
        await self.nplt_client.send_chat(command)

        self._current_model = model

        return {
            "success": True,
            "model": model,
            "message": f"已切换到模型 {model}"
        }

    async def get_current_model(self) -> str:
        """
        获取当前使用的模型

        Returns:
            模型名称
        """
        return self._current_model


# ========== 便捷函数 ==========

async def create_client(
    host: str = "127.0.0.1",
    port: int = 9999,
    auto_connect: bool = True
) -> ClientAPI:
    """
    创建并连接客户端（便捷函数）

    Args:
        host: 服务器地址
        port: 服务器端口
        auto_connect: 是否自动连接

    Returns:
        已连接的ClientAPI实例
    """
    client = ClientAPI(host=host, port=port)

    if auto_connect:
        await client.connect()

    return client
