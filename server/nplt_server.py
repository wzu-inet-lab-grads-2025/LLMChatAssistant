"""
NPLT 服务器模块

实现 NPLT 协议的服务器端处理、会话管理和心跳机制。
遵循章程：真实实现，不允许虚假实现或占位符
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Optional, Tuple

from server.protocols.nplt import MessageType, NPLTMessage
from server.storage.history import ConversationHistory, SessionManager


class SessionState(Enum):
    """会话状态"""
    CONNECTING = "connecting"
    ACTIVE = "active"
    IDLE = "idle"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class Session:
    """客户端会话（扩展版，支持文件索引管理）"""

    session_id: str                              # 会话唯一标识 (UUID)
    client_addr: Tuple[str, int]                 # 客户端地址 (IP, Port)
    connected_at: datetime                       # 连接时间
    last_heartbeat: datetime                     # 最后心跳时间
    state: SessionState                          # 会话状态
    reader: asyncio.StreamReader                 # 读取流
    writer: asyncio.StreamWriter                 # 写入流
    send_seq: int = 0                            # 发送序列号
    recv_seq: int = 0                            # 接收序列号
    conversation_history: Optional[ConversationHistory] = None  # 对话历史

    # 文件上传相关字段（Constitution v1.5.1）
    uploaded_files: list = field(default_factory=lambda: [])  # 已上传文件元数据列表
    # [{
    #     "file_id": "abc123-def456",
    #     "filename": "config.yaml",
    #     "file_path": "/storage/uploads/abc123/config.yaml",
    #     "uploaded_at": datetime(2025, 12, 31, 8, 0, 0),
    #     "size": 1024,
    #     "indexed": True
    # }]

    upload_state: Optional[Dict] = field(default_factory=dict)  # 当前上传状态
    # {
    #     "file_id": "abc123",
    #     "filename": "config.yaml",
    #     "file_size": 1024,
    #     "received_data": [],
    #     "received_size": 0
    # }

    client_type: str = "cli"                     # 客户端类型：cli | web | desktop

    HEARTBEAT_TIMEOUT = 90  # 心跳超时时间（秒）

    def is_timeout(self) -> bool:
        """检查是否超时"""
        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        return elapsed > self.HEARTBEAT_TIMEOUT

    def update_heartbeat(self):
        """更新心跳时间"""
        self.last_heartbeat = datetime.now()

    async def send_message(self, message_type: MessageType, data: bytes):
        """发送 NPLT 消息

        Args:
            message_type: 消息类型
            data: 消息数据
        """
        try:
            # 创建消息
            message = NPLTMessage(
                type=message_type,
                seq=self.send_seq,
                data=data
            )

            # 编码并发送
            encoded = message.encode()
            self.writer.write(encoded)
            await self.writer.drain()

            # 更新序列号
            self.send_seq = (self.send_seq + 1) % 65536
        except Exception as e:
            # 发送失败，通常意味着连接已关闭
            print(f"[ERROR] [SERVER] 发送消息失败: {e}")
            self.state = SessionState.ERROR
            raise

    async def send_stream_start(self):
        """发送流式输出开始标记"""
        import json
        start_msg = json.dumps({"type": "stream_start"}, ensure_ascii=False)
        await self.send_message(MessageType.AGENT_THOUGHT, start_msg.encode('utf-8'))

    async def send_stream_chunk(self, chunk: str):
        """发送流式内容片段

        Args:
            chunk: 文本片段
        """
        await self.send_message(MessageType.CHAT_TEXT, chunk.encode('utf-8'))

    async def send_stream_end(self):
        """发送流式输出结束标记（空消息）"""
        await self.send_message(MessageType.CHAT_TEXT, b"")

    async def send_status(self, status_type: str, content: str):
        """发送 Agent 状态更新

        Args:
            status_type: 状态类型 (thinking, tool_call, generating)
            content: 状态内容
        """
        import json
        status_msg = json.dumps({
            "type": status_type,
            "content": content
        }, ensure_ascii=False)
        await self.send_message(MessageType.AGENT_THOUGHT, status_msg.encode('utf-8'))

    async def send_status_json(self, status_json: str):
        """发送 Agent 状态更新（JSON 格式字符串）

        Args:
            status_json: JSON 格式的状态消息
        """
        await self.send_message(MessageType.AGENT_THOUGHT, status_json.encode('utf-8'))

    async def close(self):
        """关闭会话"""
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass
        self.state = SessionState.DISCONNECTED

    # ===== 文件索引管理方法（Constitution v1.5.1） =====

    def get_last_uploaded_file(self) -> Optional[dict]:
        """获取最后上传的文件

        Returns:
            最后上传的文件元数据字典，如果不存在则返回None
        """
        if not self.uploaded_files:
            return None
        return self.uploaded_files[-1]

    def get_uploaded_file(self, file_id: str) -> Optional[dict]:
        """根据file_id获取文件信息

        Args:
            file_id: 文件ID

        Returns:
            文件元数据字典，如果不存在则返回None
        """
        for file_info in self.uploaded_files:
            if file_info.get("file_id") == file_id:
                return file_info
        return None

    def add_uploaded_file(self, file_info: dict):
        """记录上传的文件

        Args:
            file_info: 文件元数据字典，必须包含:
                - file_id: 文件ID
                - filename: 文件名
                - file_path: 文件路径
                - uploaded_at: 上传时间
                - size: 文件大小
                - indexed: 是否已索引
        """
        self.uploaded_files.append(file_info)


@dataclass
class NPLTServer:
    """NPLT 服务器"""

    host: str = "0.0.0.0"
    port: int = 9999
    max_clients: int = 10
    heartbeat_interval: int = 90  # 心跳间隔（秒）

    # 内部状态
    sessions: Dict[str, Session] = field(default_factory=dict)
    server: Optional[asyncio.Server] = None
    running: bool = False

    # 消息处理器
    chat_handler: Optional[Callable] = None

    # 会话管理器（多会话管理）
    session_manager: Optional[SessionManager] = None

    def register_chat_handler(self, handler: Callable):
        """注册聊天消息处理器

        Args:
            handler: 聊天消息处理器函数
        """
        self.chat_handler = handler

    async def start(self):
        """启动服务器"""
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )

        self.running = True
        addr = self.server.sockets[0].getsockname()
        print(f"[INFO] [SERVER] NPLT 服务器启动在 {addr[0]}:{addr[1]}")

        # 启动心跳检查任务
        asyncio.create_task(self._heartbeat_checker())

        # 启动超时检查任务
        asyncio.create_task(self._timeout_checker())

    async def stop(self):
        """停止服务器"""
        self.running = False

        # 关闭所有会话
        for session in list(self.sessions.values()):
            await session.close()

        self.sessions.clear()

        # 关闭服务器
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        print("[INFO] [SERVER] NPLT 服务器已停止")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理客户端连接

        Args:
            reader: 读取流
            writer: 写入流
        """
        # 检查连接数限制
        if len(self.sessions) >= self.max_clients:
            print(f"[WARN] [SERVER] 达到最大客户端数限制 ({self.max_clients})，拒绝新连接")
            writer.close()
            await writer.wait_closed()
            return

        # 获取客户端地址
        addr = writer.get_extra_info('peername')
        client_ip, client_port = addr

        # 创建会话
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            client_addr=addr,
            connected_at=datetime.now(),
            last_heartbeat=datetime.now(),
            state=SessionState.CONNECTING,
            reader=reader,
            writer=writer,
            conversation_history=ConversationHistory.create_new(session_id)
        )

        self.sessions[session_id] = session
        print(f"[INFO] [SERVER] 客户端连接: {client_ip}:{client_port} (会话ID: {session_id[:8]})")

        try:
            # 更新会话状态
            session.state = SessionState.ACTIVE

            # 发送欢迎消息
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"欢迎使用智能网络运维助手！会话ID: {session_id[:8]}".encode('utf-8')
            )

            # 处理客户端消息
            while self.running and session.state != SessionState.DISCONNECTED:
                try:
                    # 读取消息头部（4 字节）
                    header = await asyncio.wait_for(
                        reader.readexactly(NPLTMessage.HEADER_SIZE),
                        timeout=self.heartbeat_interval + 10  # 超时时间略大于心跳间隔
                    )

                    # 解码头部获取数据长度
                    type_val, seq, length = NPLTMessage.decode_header(header)

                    # 读取数据部分
                    if length > 0:
                        data = await asyncio.wait_for(
                            reader.readexactly(length),
                            timeout=5.0
                        )
                    else:
                        data = b""

                    # 组装完整消息
                    full_message = header + data

                    # 解码消息
                    message = NPLTMessage.decode(full_message)

                    # 验证消息
                    if not message.validate():
                        print(f"[WARN] [SERVER] 无效消息: {message}")
                        continue

                    # 更新心跳
                    session.update_heartbeat()

                    # 处理消息
                    await self._process_message(session, message)

                except asyncio.TimeoutError:
                    # 读取超时，检查是否应该发送心跳
                    elapsed = (datetime.now() - session.last_heartbeat).total_seconds()
                    if elapsed >= self.heartbeat_interval:
                        # 发送心跳消息（使用 CHAT_TEXT 类型，内容为 "HEARTBEAT"）
                        await session.send_message(
                            MessageType.CHAT_TEXT,
                            b"HEARTBEAT"
                        )
                        print(f"[DEBUG] [SERVER] 发送心跳到 {session_id[:8]}")

                except Exception as e:
                    print(f"[ERROR] [SERVER] 处理消息失败: {e}")
                    session.state = SessionState.ERROR
                    break

        except Exception as e:
            print(f"[ERROR] [SERVER] 客户端 {session_id[:8]} 连接错误: {e}")
            session.state = SessionState.ERROR

        finally:
            # 清理会话
            await session.close()
            if session_id in self.sessions:
                del self.sessions[session_id]
            print(f"[INFO] [SERVER] 客户端断开: {client_ip}:{client_port} (会话ID: {session_id[:8]})")

    async def _process_message(self, session: Session, message: NPLTMessage):
        """处理消息

        Args:
            session: 会话
            message: NPLT 消息
        """
        try:
            if message.type == MessageType.CHAT_TEXT:
                # 聊天文本消息
                text = message.data.decode('utf-8', errors='ignore')

                # 忽略心跳响应
                if text == "HEARTBEAT":
                    return

                # 忽略空消息（流式输出结束标记）
                if not text or not text.strip():
                    return

                print(f"[DEBUG] [SERVER] 收到聊天消息: {text[:50]}...")

                # 调用聊天处理器（如果存在）
                if self.chat_handler:
                    try:
                        # 设置 Agent 的状态回调（用于发送状态更新）
                        from server.agent import ReActAgent
                        if isinstance(self.chat_handler, ReActAgent):
                            self.chat_handler.status_callback = lambda msg: session.send_status_json(msg)

                        # 使用流式处理
                        await self.chat_handler(session, text)

                    except Exception as e:
                        print(f"[ERROR] [SERVER] 聊天处理器失败: {e}")
                        import traceback
                        print(f"[DEBUG] [SERVER] 错误堆栈:\n{traceback.format_exc()}")
                        try:
                            await session.send_message(
                                MessageType.CHAT_TEXT,
                                f"处理失败: {str(e)}".encode('utf-8')
                            )
                        except:
                            print(f"[ERROR] [SERVER] 发送错误消息失败，连接可能已关闭")
                            raise

            elif message.type == MessageType.AGENT_THOUGHT:
                # Agent 思考过程（通常由服务器发送给客户端，不应该收到）
                print(f"[WARN] [SERVER] 收到 AGENT_THOUGHT 消息（不应该）")

            elif message.type == MessageType.DOWNLOAD_OFFER:
                # 下载提议（通常由服务器发送给客户端，不应该收到）
                print(f"[WARN] [SERVER] 收到 DOWNLOAD_OFFER 消息（不应该）")

            elif message.type == MessageType.FILE_METADATA:
                # 文件元数据
                await self._handle_file_metadata(session, message)

            elif message.type == MessageType.FILE_DATA:
                # 文件数据
                await self._handle_file_data(session, message)

            elif message.type == MessageType.MODEL_SWITCH:
                # 模型切换请求
                await self._handle_model_switch(session, message)

            elif message.type == MessageType.HISTORY_REQUEST:
                # 历史记录请求
                await self._handle_history_request(session, message)

            elif message.type == MessageType.CLEAR_REQUEST:
                # 清空会话请求
                await self._handle_clear_request(session, message)

            elif message.type == MessageType.SESSION_LIST:
                # 会话列表请求
                await self._handle_session_list(session, message)

            elif message.type == MessageType.SESSION_SWITCH:
                # 切换会话请求
                await self._handle_session_switch(session, message)

            elif message.type == MessageType.SESSION_NEW:
                # 创建新会话请求
                await self._handle_session_new(session, message)

            elif message.type == MessageType.SESSION_DELETE:
                # 删除会话请求
                await self._handle_session_delete(session, message)

            else:
                print(f"[WARN] [SERVER] 未知消息类型: {message.type}")

        except Exception as e:
            print(f"[ERROR] [SERVER] 处理消息失败: {e}")

    async def _heartbeat_checker(self):
        """心跳检查任务"""
        while self.running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # 检查所有会话的心跳时间
                for session_id, session in list(self.sessions.items()):
                    elapsed = (datetime.now() - session.last_heartbeat).total_seconds()
                    if elapsed >= self.heartbeat_interval:
                        # 发送心跳
                        try:
                            await session.send_message(
                                MessageType.CHAT_TEXT,
                                b"HEARTBEAT"
                            )
                            print(f"[DEBUG] [SERVER] 发送心跳到 {session_id[:8]}")
                        except Exception as e:
                            print(f"[ERROR] [SERVER] 发送心跳失败: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] [SERVER] 心跳检查失败: {e}")

    async def _timeout_checker(self):
        """超时检查任务"""
        while self.running:
            try:
                await asyncio.sleep(30)  # 每 30 秒检查一次

                # 检查超时的会话
                for session_id, session in list(self.sessions.items()):
                    if session.is_timeout():
                        print(f"[WARN] [SERVER] 会话 {session_id[:8]} 超时，关闭连接")
                        await session.close()
                        if session_id in self.sessions:
                            del self.sessions[session_id]

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] [SERVER] 超时检查失败: {e}")

    async def _handle_file_metadata(self, session: Session, message: NPLTMessage):
        """处理文件元数据"""
        try:
            metadata = json.loads(message.data.decode('utf-8'))
            filename = metadata['filename']
            filesize = metadata['size']
            
            print(f"[INFO] [SERVER] 开始接收文件: {filename} ({filesize} 字节)")
            
            # 初始化上传状态
            session.upload_state = {
                'filename': filename,
                'filesize': filesize,
                'received_data': b'',
                'chunks_received': 0
            }
            
        except Exception as e:
            print(f"[ERROR] [SERVER] 解析文件元数据失败: {e}")
    
    async def _handle_file_data(self, session: Session, message: NPLTMessage):
        """处理文件数据"""
        from server.storage.files import UploadedFile
        
        try:
            if not session.upload_state:
                print("[WARN] [SERVER] 收到文件数据但没有元数据")
                return
            
            # 追加数据
            session.upload_state['received_data'] += message.data
            session.upload_state['chunks_received'] += 1
            
            # 检查是否接收完成
            received = len(session.upload_state['received_data'])
            expected = session.upload_state['filesize']
            
            if received >= expected:
                # 接收完成，保存文件
                filename = session.upload_state['filename']
                file_data = session.upload_state['received_data']
                
                print(f"[INFO] [SERVER] 文件接收完成: {filename} ({received} 字节)")
                
                # 保存文件到 storage
                try:
                    uploaded_file = UploadedFile.create_from_content(
                        content=file_data.decode('utf-8', errors='ignore'),
                        filename=filename,
                        storage_dir="storage/uploads"
                    )

                    print(f"[INFO] [SERVER] 文件已保存: {uploaded_file.file_id}")

                    # 将文件元数据添加到 session（关键修复！）
                    session.add_uploaded_file({
                        "file_id": uploaded_file.file_id,
                        "filename": uploaded_file.filename,
                        "file_path": uploaded_file.storage_path,
                        "uploaded_at": uploaded_file.uploaded_at,
                        "size": uploaded_file.size,
                        "indexed": False  # 尚未索引
                    })

                    print(f"[INFO] [SERVER] 文件元数据已注册到 session: {session.session_id}")

                    # 发送成功确认
                    await session.send_message(
                        MessageType.CHAT_TEXT,
                        f"文件上传成功: {filename} (ID: {uploaded_file.file_id})".encode('utf-8')
                    )
                    
                except Exception as e:
                    print(f"[ERROR] [SERVER] 保存文件失败: {e}")
                    await session.send_message(
                        MessageType.CHAT_TEXT,
                        f"文件保存失败: {str(e)}".encode('utf-8')
                    )
                
                # 清除上传状态
                session.upload_state = None
                
        except Exception as e:
            print(f"[ERROR] [SERVER] 处理文件数据失败: {e}")
            session.upload_state = None


    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话

        Args:
            session_id: 会话 ID

        Returns:
            Session 实例或 None
        """
        return self.sessions.get(session_id)

    def get_active_sessions_count(self) -> int:
        """获取活跃会话数"""
        return len(self.sessions)

    async def _handle_model_switch(self, session: Session, message: NPLTMessage):
        """处理模型切换请求

        遵循 FR-020: 服务器必须验证模型确实切换成功后才发送确认消息
        """
        try:
            import json

            # 解析请求
            request = json.loads(message.data.decode('utf-8'))
            model = request.get('model', '')

            print(f"[INFO] [SERVER] 模型切换请求: {model}")

            # 验证模型名称
            available_models = ["glm-4-flash", "glm-4.5-flash"]
            if model not in available_models:
                print(f"[WARN] [SERVER] 无效的模型: {model}")
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    f"无效的模型: {model}，可用模型: {', '.join(available_models)}".encode('utf-8')
                )
                return

            # 验证回调是否已设置 (遵循规范边界情况: LLM Provider回调未设置)
            if not hasattr(self, 'model_switch_callback') or not self.model_switch_callback:
                print(f"[ERROR] [SERVER] 模型切换回调未设置")
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    f"模型切换失败: 服务器回调未设置".encode('utf-8')
                )
                return

            # 尝试切换模型并验证成功 (遵循 FR-020: 验证切换成功)
            try:
                self.model_switch_callback(model)
                print(f"[INFO] [SERVER] 模型切换成功: {model}")
            except Exception as switch_error:
                print(f"[ERROR] [SERVER] 模型切换失败: {switch_error}")
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    f"模型切换失败: {str(switch_error)}".encode('utf-8')
                )
                return

            # 切换成功，发送确认 (遵循 FR-020: 验证成功后才发送确认)
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"模型已切换: {model}".encode('utf-8')
            )

        except Exception as e:
            print(f"[ERROR] [SERVER] 处理模型切换失败: {e}")
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"模型切换失败: {str(e)}".encode('utf-8')
            )

    async def _handle_history_request(self, session: Session, message: NPLTMessage):
        """处理历史记录请求"""
        try:
            if not session.conversation_history:
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    "暂无对话历史".encode('utf-8')
                )
                return

            # 获取历史记录
            messages = session.conversation_history.get_context(num_messages=20)

            # 格式化历史记录
            history_text = "\n\n=== 对话历史 ===\n\n"
            for msg in messages:
                role = "用户" if msg["role"] == "user" else "助手"
                history_text += f"{role}: {msg['content']}\n\n"

            # 发送历史记录
            await session.send_message(
                MessageType.CHAT_TEXT,
                history_text.encode('utf-8')
            )

            print(f"[INFO] [SERVER] 发送历史记录: {len(messages)} 条消息")

        except Exception as e:
            print(f"[ERROR] [SERVER] 处理历史记录请求失败: {e}")
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"获取历史记录失败: {str(e)}".encode('utf-8')
            )

    async def _handle_clear_request(self, session: Session, message: NPLTMessage):
        """处理清空会话请求"""
        try:
            # 清空会话历史
            if session.conversation_history:
                session.conversation_history.clear()

            # 发送确认
            await session.send_message(
                MessageType.CHAT_TEXT,
                "会话历史已清空".encode('utf-8')
            )

            print(f"[INFO] [SERVER] 会话历史已清空: {session.session_id[:8]}")

        except Exception as e:
            print(f"[ERROR] [SERVER] 清空会话历史失败: {e}")
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"清空失败: {str(e)}".encode('utf-8')
            )

    async def _handle_session_list(self, session: Session, message: NPLTMessage):
        """处理会话列表请求"""
        try:
            if not self.session_manager:
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    "会话管理器未初始化".encode('utf-8')
                )
                return

            # 获取会话列表
            session_list = self.session_manager.list_sessions()

            # 格式化会话列表
            response = "\n\n=== 会话列表 ===\n\n"
            if not session_list:
                response += "暂无会话\n"
            else:
                for idx, sinfo in enumerate(session_list, 1):
                    current = " (当前)" if sinfo.is_current else ""
                    response += f"{idx}. [{sinfo.session_id[:8]}] {sinfo.name}{current}\n"
                    response += f"   消息数: {sinfo.message_count}\n"
                    response += f"   最后访问: {sinfo.last_accessed.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            # 发送会话列表
            await session.send_message(
                MessageType.CHAT_TEXT,
                response.encode('utf-8')
            )

            print(f"[INFO] [SERVER] 发送会话列表: {len(session_list)} 个会话")

        except Exception as e:
            print(f"[ERROR] [SERVER] 处理会话列表请求失败: {e}")
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"获取会话列表失败: {str(e)}".encode('utf-8')
            )

    async def _handle_session_switch(self, session: Session, message: NPLTMessage):
        """处理切换会话请求"""
        try:
            import json

            if not self.session_manager:
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    "会话管理器未初始化".encode('utf-8')
                )
                return

            # 解析请求
            request = json.loads(message.data.decode('utf-8'))
            target_session_id = request.get('session_id', '')

            if not target_session_id:
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    "会话ID不能为空".encode('utf-8')
                )
                return

            print(f"[INFO] [SERVER] 切换会话请求: {target_session_id}")

            # 切换会话
            if not self.session_manager.switch_session(target_session_id):
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    f"切换失败: 会话不存在或已归档".encode('utf-8')
                )
                return

            # 加载新会话的上下文（T092）
            new_history = ConversationHistory.load(target_session_id)
            if new_history:
                session.conversation_history = new_history
                print(f"[INFO] [SERVER] 已加载会话上下文: {target_session_id[:8]}")
            else:
                # 如果加载失败，创建新的历史记录
                session.conversation_history = ConversationHistory.create_new(target_session_id)
                print(f"[WARN] [SERVER] 未找到会话历史，创建新的: {target_session_id[:8]}")

            # 发送确认
            target_session = self.session_manager.sessions.get(target_session_id)
            session_name = target_session.name if target_session else target_session_id[:8]
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"已切换到会话: {session_name}".encode('utf-8')
            )

            print(f"[INFO] [SERVER] 会话已切换: {target_session_id[:8]}")

        except Exception as e:
            print(f"[ERROR] [SERVER] 处理切换会话请求失败: {e}")
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"切换会话失败: {str(e)}".encode('utf-8')
            )

    async def _handle_session_new(self, session: Session, message: NPLTMessage):
        """处理创建新会话请求"""
        try:
            if not self.session_manager:
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    "会话管理器未初始化".encode('utf-8')
                )
                return

            print(f"[INFO] [SERVER] 创建新会话请求")

            # 创建新会话
            new_session = self.session_manager.create_session()
            new_session_id = new_session.session_id

            # 切换到新会话
            self.session_manager.switch_session(new_session_id)

            # 为客户端连接创建新的对话历史
            session.conversation_history = ConversationHistory.create_new(new_session_id)

            # 发送确认
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"已创建新会话: {new_session_id[:8]}".encode('utf-8')
            )

            print(f"[INFO] [SERVER] 新会话已创建: {new_session_id[:8]}")

        except Exception as e:
            print(f"[ERROR] [SERVER] 处理创建新会话请求失败: {e}")
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"创建新会话失败: {str(e)}".encode('utf-8')
            )

    async def _handle_session_delete(self, session: Session, message: NPLTMessage):
        """处理删除会话请求"""
        try:
            import json

            if not self.session_manager:
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    "会话管理器未初始化".encode('utf-8')
                )
                return

            # 解析请求
            request = json.loads(message.data.decode('utf-8'))
            target_session_id = request.get('session_id', '')

            if not target_session_id:
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    "会话ID不能为空".encode('utf-8')
                )
                return

            print(f"[INFO] [SERVER] 删除会话请求: {target_session_id}")

            # 删除会话
            if not self.session_manager.delete_session(target_session_id):
                await session.send_message(
                    MessageType.CHAT_TEXT,
                    f"删除失败: 会话不存在、是当前会话或其他错误".encode('utf-8')
                )
                return

            # 发送确认
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"会话已删除: {target_session_id[:8]}".encode('utf-8')
            )

            print(f"[INFO] [SERVER] 会话已删除: {target_session_id[:8]}")

        except Exception as e:
            print(f"[ERROR] [SERVER] 处理删除会话请求失败: {e}")
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"删除会话失败: {str(e)}".encode('utf-8')
            )


# NPLTMessage.decode_header 是一个辅助方法，用于解码头部
def _decode_header_helper():
    """为 NPLTMessage 添加 decode_header 辅助方法"""
    import struct

    def decode_header(cls, data: bytes):
        """解码头部获取 Type, Seq, Len"""
        type_val, seq, length = struct.unpack(
            cls.HEADER_FORMAT,
            data[:cls.HEADER_SIZE]
        )
        return type_val, seq, length

    NPLTMessage.decode_header = classmethod(decode_header)


_decode_header_helper()
