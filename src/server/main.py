"""
智能网络运维助手 - 服务器主入口

实现服务器启动逻辑、配置加载和生命周期管理。
遵循章程：真实实现，不允许虚假实现或占位符
"""

import asyncio
import signal
import sys
from pathlib import Path

from ..llm.zhipu import ZhipuProvider
from ..storage.vector_store import VectorStore
from ..tools.command import CommandTool
from ..tools.monitor import MonitorTool
from ..tools.rag import RAGTool
from ..utils.config import AppConfig
from ..utils.logger import get_server_logger
from ..protocols.nplt import MessageType
from .agent import ReActAgent
from .nplt_server import NPLTServer, Session
from .rdt_server import RDTServer


class Server:
    """服务器主类"""

    def __init__(self, config: AppConfig):
        """初始化服务器

        Args:
            config: 应用配置
        """
        self.config = config
        self.logger = get_server_logger(level=config.server.log_level)

        # LLM Provider
        self.llm_provider: ZhipuProvider = None

        # ReAct Agent
        self.agent: ReActAgent = None

        # 向量存储
        self.vector_store: VectorStore = None

        # NPLT 服务器
        self.nplt_server: NPLTServer = None

        # RDT 服务器
        self.rdt_server: RDTServer = None

        # 运行状态
        self.running = False

    async def start(self):
        """启动服务器"""
        self.logger.info("=" * 60)
        self.logger.info("智能网络运维助手 - 服务器启动")
        self.logger.info("=" * 60)

        # 显示配置
        self._show_config()

        try:
            # 初始化 LLM Provider
            self.logger.info("初始化 LLM Provider...")
            self.llm_provider = ZhipuProvider(
                api_key=self.config.llm.api_key,
                model=self.config.llm.model,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens
            )
            self.logger.success("LLM Provider 初始化成功")

            # 初始化向量存储
            self.logger.info("初始化向量存储...")
            storage_path = Path(self.config.storage.storage_dir)
            storage_path.mkdir(parents=True, exist_ok=True)
            vectors_dir = storage_path / "vectors"
            vectors_dir.mkdir(parents=True, exist_ok=True)
            self.vector_store = VectorStore(storage_dir=str(vectors_dir))
            self.logger.success("向量存储初始化成功")

            # 初始化 ReAct Agent
            self.logger.info("初始化 ReAct Agent...")
            self.agent = ReActAgent(
                llm_provider=self.llm_provider,
                tools={
                    "command_executor": CommandTool(),
                    "sys_monitor": MonitorTool(),
                    "rag_search": RAGTool(self.llm_provider, self.vector_store)
                },
                max_tool_rounds=5,
                tool_timeout=5
            )
            self.logger.success("ReAct Agent 初始化成功")

            # 创建 NPLT 服务器
            self.nplt_server = NPLTServer(
                host=self.config.server.host,
                port=self.config.server.port,
                max_clients=self.config.server.max_clients,
                heartbeat_interval=self.config.server.heartbeat_interval
            )

            # 创建 RDT 服务器
            self.rdt_server = RDTServer(
                host="0.0.0.0",
                port=9998,
                window_size=5,
                timeout=0.1
            )

            # 注册聊天处理器
            self.nplt_server.register_chat_handler(self._handle_chat)

            # 启动 NPLT 服务器
            await self.nplt_server.start()

            # 启动 RDT 服务器
            await self.rdt_server.start()

            self.running = True
            self.logger.success("服务器启动成功")
            self.logger.info(f"监听地址: {self.config.server.host}:{self.config.server.port}")
            self.logger.info(f"最大客户端数: {self.config.server.max_clients}")
            self.logger.info(f"心跳间隔: {self.config.server.heartbeat_interval} 秒")

            # 保持运行
            await self._run_forever()

        except Exception as e:
            self.logger.error(f"服务器启动失败: {e}")
            raise

    async def _handle_chat(self, session: Session, message: str) -> str:
        """处理聊天消息

        集成 ReActAgent，处理用户消息并发送工具调用过程。

        Args:
            session: 客户端会话
            message: 消息内容

        Returns:
            响应内容
        """
        try:
            self.logger.info(f"[{session.session_id[:8]}] 收到消息: {message[:50]}...")

            # 添加用户消息到历史
            session.conversation_history.add_message("user", message)

            # 使用 ReAct Agent 处理消息
            response, tool_calls = self.agent.react_loop(
                user_message=message,
                conversation_history=session.conversation_history
            )

            # 发送 Agent 思考过程（工具调用）
            for tool_call in tool_calls:
                # 构造 Agent 思考消息
                thought_text = f"[工具: {tool_call.tool_name}]\n"
                thought_text += f"参数: {tool_call.arguments}\n"
                thought_text += f"状态: {tool_call.status}\n"
                thought_text += f"耗时: {tool_call.duration:.2f}s\n"
                if tool_call.result:
                    thought_text += f"结果: {tool_call.result[:200]}"  # 限制长度

                # 发送 AGENT_THOUGHT 消息
                await session.send_message(
                    MessageType.AGENT_THOUGHT,
                    thought_text.encode('utf-8')
                )
                self.logger.debug(f"[{session.session_id[:8]}] 发送 Agent 思考")

            # 添加助手响应到历史
            session.conversation_history.add_message("assistant", response)

            return response

        except Exception as e:
            self.logger.error(f"[{session.session_id[:8]}] 处理消息失败: {e}")
            error_msg = f"处理失败: {str(e)}"
            session.conversation_history.add_message("assistant", error_msg)
            return error_msg

    async def offer_file_download(
        self,
        session: Session,
        filename: str,
        file_data: bytes
    ) -> bool:
        """向客户端提议下载文件

        Args:
            session: 客户端会话
            filename: 文件名
            file_data: 文件数据

        Returns:
            是否成功
        """
        try:
            import json

            self.logger.info(f"[{session.session_id[:8]}] 准备发送文件: {filename} ({len(file_data)} 字节)")

            # 创建 RDT 会话
            client_addr = session.client_addr  # TCP 地址
            download_token = self.rdt_server.create_session(
                filename=filename,
                file_data=file_data,
                client_addr=client_addr
            )

            # 获取 RDT 会话信息
            rdt_session = self.rdt_server.sessions.get(download_token)
            if not rdt_session:
                self.logger.error(f"创建 RDT 会话失败")
                return False

            # 构造下载提议消息
            offer_data = {
                "filename": filename,
                "size": rdt_session.file_size,
                "checksum": rdt_session.checksum,
                "download_token": download_token,
                "server_host": "0.0.0.0",  # RDT 服务器地址
                "server_port": 9998
            }

            offer_json = json.dumps(offer_data, ensure_ascii=False)

            # 发送 DOWNLOAD_OFFER 消息
            await session.send_message(
                MessageType.DOWNLOAD_OFFER,
                offer_json.encode('utf-8')
            )

            self.logger.info(f"[{session.session_id[:8]}] 已发送下载提议: {filename}")
            return True

        except Exception as e:
            self.logger.error(f"[{session.session_id[:8]}] 发送下载提议失败: {e}")
            return False

    async def _run_forever(self):
        """保持服务器运行"""
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.logger.info("收到停止信号")

    async def stop(self):
        """停止服务器"""
        if not self.running:
            return

        self.logger.info("正在停止服务器...")
        self.running = False

        # 停止 NPLT 服务器
        if self.nplt_server:
            await self.nplt_server.stop()

        # 停止 RDT 服务器
        if self.rdt_server:
            await self.rdt_server.stop()

        self.logger.success("服务器已停止")

    def _show_config(self):
        """显示配置信息"""
        self.logger.info("配置信息:")
        self.logger.info(f"  监听地址: {self.config.server.host}:{self.config.server.port}")
        self.logger.info(f"  最大客户端: {self.config.server.max_clients}")
        self.logger.info(f"  心跳间隔: {self.config.server.heartbeat_interval} 秒")
        self.logger.info(f"  LLM 模型: {self.config.llm.model}")
        self.logger.info(f"  温度: {self.config.llm.temperature}")
        self.logger.info(f"  最大令牌: {self.config.llm.max_tokens}")
        self.logger.info(f"  存储目录: {self.config.storage.storage_dir}")


async def main():
    """主函数"""
    # 加载配置
    config = AppConfig.load()

    # 创建服务器
    server = Server(config)

    # 设置信号处理
    loop = asyncio.get_running_loop()

    def signal_handler():
        """信号处理器"""
        server.logger.info("收到中断信号，正在优雅关闭...")
        server.running = False

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # 启动服务器
    try:
        await server.start()
    except Exception as e:
        config.logger = server.logger
        config.logger.error(f"服务器运行错误: {e}")
        sys.exit(1)
    finally:
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务器已停止")
