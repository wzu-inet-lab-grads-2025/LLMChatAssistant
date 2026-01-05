"""
智能网络运维助手 - 服务器主入口

实现服务器启动逻辑、配置加载和生命周期管理。
遵循章程：真实实现，不允许虚假实现或占位符
"""

import asyncio
import signal
import sys
from pathlib import Path

from server.llm.zhipu import ZhipuProvider
from server.storage.vector_store import VectorStore
from server.storage.history import SessionManager
from server.tools.command import CommandTool
from server.tools.monitor import MonitorTool
from server.tools.semantic_search import SemanticSearchTool
from shared.utils.config import AppConfig
from shared.utils.logger import get_server_logger
from shared.protocols.nplt import MessageType
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

        # 会话管理器（多会话管理）
        self.session_manager: SessionManager = None

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
                model=self.config.llm.chat_model
            )
            self.logger.info("LLM Provider 初始化成功")

            # 初始化向量存储
            self.logger.info("初始化向量存储...")
            storage_path = Path(self.config.server.storage_dir)
            storage_path.mkdir(parents=True, exist_ok=True)
            vectors_dir = storage_path / "vectors"
            vectors_dir.mkdir(parents=True, exist_ok=True)
            self.vector_store = VectorStore(storage_dir=str(vectors_dir))
            self.logger.info("向量存储初始化成功")

            # 初始化 ReAct Agent
            self.logger.info("初始化 ReAct Agent...")

            # 初始化路径验证器
            from server.tools.command import CommandTool
            from server.tools.monitor import MonitorTool
            from server.tools.semantic_search import SemanticSearchTool
            from server.tools.file_upload import FileUploadTool
            from server.tools.file_download import FileDownloadTool
            from server.storage.index_manager import IndexManager
            from shared.utils.path_validator import get_path_validator

            path_validator = get_path_validator(self.config.file_access)

            # 初始化索引管理器
            index_manager = IndexManager(
                vector_store=self.vector_store,
                llm_provider=self.llm_provider,
                path_validator=path_validator,
                config=self.config.file_access
            )

            # 创建 RDT 服务器（必须在 Agent 之前创建）
            # 关键依赖：FileDownloadTool 需要有效的 rdt_server 实例
            # 如果在 Agent 之后创建，rdt_server 会是 None，导致文件下载降级到 NPLT 模式
            # 参考：server/tools/file_download.py:246-250
            self.rdt_server = RDTServer(
                host="0.0.0.0",
                port=9998,
                window_size=5,
                timeout=0.1
            )

            # 创建 NPLT 服务器
            self.nplt_server = NPLTServer(
                host=self.config.server.host,
                port=self.config.server.port,
                max_clients=self.config.server.max_clients,
                heartbeat_interval=self.config.server.heartbeat_interval
            )

            # 创建工具实例（RDT 服务器现在可用）
            # FileDownloadTool 的关键集成：
            # - rdt_server: 用于 UDP 文件传输（必须已初始化）
            # - server: 用于调用 offer_file_download() 发送 DOWNLOAD_OFFER 消息
            # - client_type: 决定传输模式（cli→RDT, web→HTTP）
            # 参考：server/tools/file_download.py, server/main.py:305-363
            self.agent = ReActAgent(
                llm_provider=self.llm_provider,
                tools={
                    "command_executor": CommandTool(
                        path_validator=path_validator,
                        max_output_size=self.config.file_access.max_output_size
                    ),
                    "sys_monitor": MonitorTool(),
                    "semantic_search": SemanticSearchTool(
                        llm_provider=self.llm_provider,
                        vector_store=self.vector_store,
                        index_manager=index_manager,
                        path_validator=path_validator,
                        auto_index=self.config.file_access.auto_index
                    ),
                    "file_upload": FileUploadTool(),
                    "file_download": FileDownloadTool(
                        path_validator=path_validator,
                        rdt_server=self.rdt_server,  # 现在不是 None 了
                        server=self,  # 传入 server 实例，用于调用 offer_file_download
                        http_base_url=f"http://{self.config.server.host}:{self.config.server.port}",
                        client_type="cli"
                    )
                },
                max_tool_rounds=5,
                tool_timeout=5
            )
            self.logger.info("ReAct Agent 初始化成功")

            # 初始化会话管理器
            self.logger.info("初始化会话管理器...")
            history_dir = storage_path / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            self.session_manager = SessionManager(storage_dir=str(history_dir))

            # 如果没有会话，创建默认会话
            if not self.session_manager.sessions:
                self.session_manager.create_session(name="默认会话")

            self.logger.info("会话管理器初始化成功")

            # 注册聊天处理器
            self.nplt_server.register_chat_handler(self._handle_chat)

            # 注册模型切换回调 (遵循 FR-020: 服务器验证模型切换成功)
            self.nplt_server.model_switch_callback = self.llm_provider.set_model

            # 集成会话管理器（T090）
            self.nplt_server.session_manager = self.session_manager

            # 集成索引管理器（用于文件自动索引）
            self.nplt_server.index_manager = index_manager

            # 启动 NPLT 服务器
            await self.nplt_server.start()

            # 启动 RDT 服务器
            await self.rdt_server.start()

            self.running = True
            self.logger.info("服务器启动成功")
            self.logger.info(f"监听地址: {self.config.server.host}:{self.config.server.port}")
            self.logger.info(f"最大客户端数: {self.config.server.max_clients}")
            self.logger.info(f"心跳间隔: {self.config.server.heartbeat_interval} 秒")

            # 保持运行
            await self._run_forever()

        except Exception as e:
            self.logger.error(f"服务器启动失败: {e}")
            raise

    async def _handle_chat(self, session: Session, message: str):
        """处理聊天消息（真正的流式输出）

        使用 LLM 的流式 API，边生成边发送边显示。

        Args:
            session: 客户端会话
            message: 消息内容
        """
        try:
            self.logger.info(f"[{session.session_id[:8]}] 收到消息: {message[:50]}...")

            # 添加用户消息到历史
            session.conversation_history.add_message("user", message)

            # 设置 Agent 的状态回调（用于发送状态更新）
            self.agent.status_callback = lambda msg: session.send_status_json(msg)

            # 动态更新file_download工具的client_type（支持混合传输架构）
            if "file_download" in self.agent.tools:
                self.agent.tools["file_download"].client_type = session.client_type
                self.logger.debug(f"[{session.session_id[:8]}] 文件下载工具客户端类型: {session.client_type}")

            # 使用 Agent 的 think_stream 方法，它会自动发送状态通知
            full_response = ""
            buffer = ""
            buffer_size = 10  # 较小缓冲区，配合客户端渐进显示（每次2字符）
            stream_started = False  # 跟踪是否已发送流式开始标记
            first_chunk_received = False  # 跟踪是否收到第一个 chunk

            async for chunk in self.agent.think_stream(
                user_message=message,
                conversation_history=session.conversation_history,
                session=session  # 传递 session 对象，让工具可以访问 uploaded_files
            ):
                full_response += chunk
                buffer += chunk

                # 收到第一个 chunk 时发送流式开始标记
                if not first_chunk_received:
                    await session.send_stream_start()
                    stream_started = True
                    first_chunk_received = True

                # 缓冲区满了就发送
                if len(buffer) >= buffer_size:
                    await session.send_stream_chunk(buffer)
                    buffer = ""

            # 发送剩余的缓冲区内容
            if buffer:
                await session.send_stream_chunk(buffer)

            # 发送流式结束标记（如果流式已开始）
            if stream_started:
                await session.send_stream_end()

            # 保存助手响应到历史（注意：think_stream是generator，无法在其中保存）
            # 检查是否已经在_react_loop_with_tools中保存（通过检查历史记录的最后一条消息）
            last_message = session.conversation_history.messages[-1] if session.conversation_history.messages else None
            if not last_message or last_message.role != "assistant":
                # 如果最后一条不是助手消息，说明需要保存
                session.conversation_history.add_message(
                    role="assistant",
                    content=full_response
                )

            # 保存对话历史到磁盘
            session.conversation_history.save()

            # T091: 集成会话命名 - 在第 3 轮对话后触发 AI 自动命名
            message_count = len(session.conversation_history.messages)
            if message_count >= 6:  # 3 轮对话 = 6 条消息（用户 + 助手）
                # 检查当前会话是否已命名（如果名称还是默认的，触发 AI 命名）
                current_conv_session = self.session_manager.get_current_session()
                if current_conv_session and current_conv_session.name.startswith("20"):
                    # 默认名称格式是 "YYYY-MM-DD HH:MM"，以 "20" 开头
                    # 如果是默认名称，触发 AI 命名
                    context_messages = [
                        {"role": msg.role, "content": msg.content}
                        for msg in session.conversation_history.messages
                    ]
                    success = self.session_manager.auto_name_session(
                        current_conv_session.session_id,
                        self.llm_provider,
                        context_messages
                    )
                    if success:
                        self.logger.info(f"[{session.session_id[:8]}] 会话已自动命名")

            # 更新会话消息计数
            if self.session_manager.current_session_id:
                self.session_manager.increment_message_count(self.session_manager.current_session_id)

        except Exception as e:
            import traceback
            self.logger.error(f"[{session.session_id[:8]}] 处理消息失败: {e}")
            self.logger.debug(f"[{session.session_id[:8]}] 错误堆栈:\n{traceback.format_exc()}")
            error_msg = f"处理失败: {str(e)}"
            session.conversation_history.add_message("assistant", error_msg)
            # 发送错误消息
            try:
                await session.send_stream_chunk(error_msg)
                await session.send_stream_end()
            except:
                pass

    async def offer_file_download(
        self,
        session: Session,
        filename: str,
        file_data: bytes
    ) -> bool:
        """向客户端提议下载文件

        端到端流程中的关键集成点：
        1. 创建 RDT 会话（rdt_server.create_session）
        2. 构造 DOWNLOAD_OFFER 消息（包含下载令牌、校验和等）
        3. 通过 NPLT 协议发送给客户端
        4. 客户端接收后连接 RDT 服务器准备接收文件

        由 FileDownloadTool._download_via_rdt() 调用
        参考：server/tools/file_download.py:269-300, server/main.py:305-363

        Args:
            session: 客户端会话（包含 client_addr）
            filename: 文件名
            file_data: 文件数据（完整内容）

        Returns:
            是否成功发送 DOWNLOAD_OFFER 消息
        """
        try:
            import json

            self.logger.info(f"[{session.session_id[:8]}] 准备发送文件: {filename} ({len(file_data)} 字节)")

            # 构造客户端 UDP 地址（用于 RDT 传输）
            if session.client_udp_port:
                # 使用客户端注册的 UDP 端口
                client_addr = (session.client_addr[0], session.client_udp_port)
                self.logger.info(f"[{session.session_id[:8]}] 使用客户端 UDP 端口: {session.client_udp_port}")
            else:
                # Fallback: 使用 TCP 地址（可能无法工作）
                client_addr = session.client_addr
                self.logger.warning(f"[{session.session_id[:8]}] 客户端未注册 UDP 端口，使用 TCP 地址: {client_addr}")

            # 创建 RDT 会话
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

        self.logger.info("服务器已停止")

    def _show_config(self):
        """显示配置信息"""
        self.logger.info("配置信息:")
        self.logger.info(f"  监听地址: {self.config.server.host}:{self.config.server.port}")
        self.logger.info(f"  最大客户端: {self.config.server.max_clients}")
        self.logger.info(f"  心跳间隔: {self.config.server.heartbeat_interval} 秒")
        self.logger.info(f"  LLM 模型: {self.config.llm.chat_model}")
        self.logger.info(f"  温度: {self.config.llm.temperature}")
        self.logger.info(f"  最大令牌: {self.config.llm.max_tokens}")
        self.logger.info(f"  存储目录: {self.config.server.storage_dir}")


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
