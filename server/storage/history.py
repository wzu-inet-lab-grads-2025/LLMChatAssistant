"""
对话历史模块

提供对话历史记录管理和持久化功能。
遵循章程：数据持久化到 storage/history/ 目录
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional


@dataclass
class ToolCall:
    """工具调用"""
    tool_name: str          # 工具名称
    arguments: dict         # 工具参数
    result: str             # 执行结果
    status: str             # 执行状态
    duration: float         # 执行时长（秒）
    timestamp: datetime     # 调用时间

    def is_timeout(self, timeout: int = 5) -> bool:
        """检查是否超时"""
        return self.duration > timeout

    def to_dict(self) -> dict:
        """转换为字典"""
        # 防御性编程：处理 timestamp 可能是字符串的情况
        if isinstance(self.timestamp, datetime):
            timestamp_str = self.timestamp.isoformat()
        elif isinstance(self.timestamp, str):
            timestamp_str = self.timestamp
        else:
            print(f"[WARN] ToolCall.to_dict: timestamp 类型异常 {type(self.timestamp)}, 使用当前时间")
            timestamp_str = datetime.now().isoformat()

        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "status": self.status,
            "duration": self.duration,
            "timestamp": timestamp_str
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ToolCall':
        """从字典创建实例"""
        # 防御性编程：处理 timestamp 可能是 datetime 对象的情况
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif not isinstance(timestamp, datetime):
            print(f"[WARN] ToolCall.from_dict: timestamp 类型异常 {type(timestamp)}, 使用当前时间")
            timestamp = datetime.now()

        return cls(
            tool_name=data["tool_name"],
            arguments=data["arguments"],
            result=data["result"],
            status=data["status"],
            duration=data["duration"],
            timestamp=timestamp
        )


@dataclass
class ChatMessage:
    """聊天消息"""
    role: Literal["user", "assistant", "system"]  # 角色
    content: str                      # 消息内容
    timestamp: datetime                # 时间戳
    tool_calls: List[ToolCall] = field(default_factory=list)  # 工具调用
    metadata: dict = field(default_factory=dict)              # 元数据

    def to_dict(self) -> dict:
        """转换为字典"""
        # 防御性编程：处理 timestamp 可能是字符串的情况
        if isinstance(self.timestamp, datetime):
            timestamp_str = self.timestamp.isoformat()
        elif isinstance(self.timestamp, str):
            # 已经是字符串，直接使用
            timestamp_str = self.timestamp
        else:
            # 其他类型，使用当前时间
            print(f"[WARN] ChatMessage.to_dict: timestamp 类型异常 {type(self.timestamp)}, 使用当前时间")
            timestamp_str = datetime.now().isoformat()

        return {
            "role": self.role,
            "content": self.content,
            "timestamp": timestamp_str,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ChatMessage':
        """从字典创建实例"""
        # 防御性编程：处理 timestamp 可能是 datetime 对象的情况
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif not isinstance(timestamp, datetime):
            print(f"[WARN] ChatMessage.from_dict: timestamp 类型异常 {type(timestamp)}, 使用当前时间")
            timestamp = datetime.now()

        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=timestamp,
            tool_calls=[ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])],
            metadata=data.get("metadata", {})
        )


@dataclass
class ConversationHistory:
    """对话历史"""
    session_id: str               # 会话 ID
    messages: List[ChatMessage]   # 消息列表
    created_at: datetime          # 创建时间
    updated_at: datetime          # 更新时间
    uploaded_files: List[dict] = field(default_factory=list)  # 上传的文件列表

    def add_message(self, role: str, content: str, tool_calls: List[ToolCall] = None, metadata: dict = None):
        """添加消息

        Args:
            role: 角色（user, assistant, system）
            content: 消息内容
            tool_calls: 工具调用列表（可选）
            metadata: 元数据（可选）
        """
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            tool_calls=tool_calls or [],
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_context(self, max_turns: int = 10) -> List[ChatMessage]:
        """获取最近 N 轮对话作为上下文

        Args:
            max_turns: 最大轮数（一轮 = 用户消息 + AI 回复）

        Returns:
            最近 N 轮对话的消息列表
        """
        # 调试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DEBUG] get_context[{self.session_id[:8]}]: 总消息数={len(self.messages)}, max_turns={max_turns}")
        for i, msg in enumerate(self.messages):
            logger.info(f"[DEBUG]   消息[{i}]: role={msg.role}, content前50字符={repr(msg.content[:50])}")

        # 返回最近 max_turns * 2 条消息
        return self.messages[-max_turns*2:]

    def get_last_n_messages(self, n: int = 5) -> List[ChatMessage]:
        """获取最近 N 条消息

        Args:
            n: 消息数量

        Returns:
            最近 N 条消息
        """
        return self.messages[-n:]

    def clear(self):
        """清空对话历史"""
        self.messages = []
        self.updated_at = datetime.now()

    def add_uploaded_file(self, file_info: dict):
        """添加上传的文件

        Args:
            file_info: 文件信息字典
                {
                    "file_id": "uuid",
                    "filename": "name.txt",
                    "file_path": "/path/to/file",
                    "size": 1234,
                    "uploaded_at": datetime,
                    "indexed": False
                }
        """
        # 检查是否已存在（避免重复）
        for existing in self.uploaded_files:
            if existing.get("file_id") == file_info.get("file_id"):
                return  # 已存在，不重复添加

        self.uploaded_files.append(file_info)
        self.updated_at = datetime.now()

    def get_uploaded_files(self) -> List[dict]:
        """获取所有上传的文件

        Returns:
            上传文件列表
        """
        return self.uploaded_files.copy()  # 返回副本，避免外部修改

    def remove_uploaded_file(self, file_id: str) -> bool:
        """移除上传的文件

        Args:
            file_id: 文件ID

        Returns:
            是否移除成功
        """
        for i, file_info in enumerate(self.uploaded_files):
            if file_info.get("file_id") == file_id:
                self.uploaded_files.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def save(self, storage_dir: str = "storage/history"):
        """保存对话历史到磁盘

        Args:
            storage_dir: 存储目录
        """
        os.makedirs(storage_dir, exist_ok=True)

        # 使用日期和完整的 session_id 作为文件名（但限制长度以避免文件名过长）
        # 对于短 session_id 直接使用，对于长的使用前32个字符
        session_prefix = self.session_id if len(self.session_id) <= 32 else self.session_id[:32]
        filename = f"session_{self.created_at.strftime('%Y%m%d')}_{session_prefix}.json"
        filepath = os.path.join(storage_dir, filename)

        # 序列化 uploaded_files（datetime 对象转为 ISO 字符串）
        uploaded_files_serialized = []
        for file_info in self.uploaded_files:
            file_copy = file_info.copy()
            uploaded_at = file_copy.get("uploaded_at")
            # 处理各种可能的类型（防御性编程）
            if isinstance(uploaded_at, datetime):
                file_copy["uploaded_at"] = uploaded_at.isoformat()
            elif isinstance(uploaded_at, str):
                # 已经是字符串（ISO格式），直接使用
                pass
            else:
                # 其他类型（None、数字等），使用当前时间
                print(f"[WARN] uploaded_at 类型异常: {type(uploaded_at)}, 使用当前时间")
                file_copy["uploaded_at"] = datetime.now().isoformat()
            uploaded_files_serialized.append(file_copy)

        data = {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "uploaded_files": uploaded_files_serialized,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, session_id: str, storage_dir: str = "storage/history") -> Optional['ConversationHistory']:
        """从磁盘加载对话历史

        Args:
            session_id: 会话 ID
            storage_dir: 存储目录

        Returns:
            ConversationHistory 实例或 None
        """
        # 查找匹配的文件
        os.makedirs(storage_dir, exist_ok=True)

        # 尝试找到匹配的会话文件（通过验证完整的 session_id）
        for filename in os.listdir(storage_dir):
            if filename.startswith(f"session_") and filename.endswith(".json"):
                filepath = os.path.join(storage_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # 验证完整的 session_id 是否匹配
                    if data.get("session_id") == session_id:
                        # 反序列化 uploaded_files（ISO 字符串转为 datetime）
                        uploaded_files = []
                        for file_info in data.get("uploaded_files", []):
                            file_copy = file_info.copy()
                            if "uploaded_at" in file_copy:
                                if isinstance(file_copy["uploaded_at"], str):
                                    file_copy["uploaded_at"] = datetime.fromisoformat(file_copy["uploaded_at"])
                            uploaded_files.append(file_copy)

                        return cls(
                            session_id=data["session_id"],
                            messages=[ChatMessage.from_dict(msg) for msg in data["messages"]],
                            uploaded_files=uploaded_files,
                            created_at=datetime.fromisoformat(data["created_at"]),
                            updated_at=datetime.fromisoformat(data["updated_at"])
                        )
                except Exception as e:
                    print(f"警告：加载对话历史失败 {filename}: {e}")
                    continue

        return None

    @classmethod
    def create_new(cls, session_id: str = None) -> 'ConversationHistory':
        """创建新的对话历史

        Args:
            session_id: 会话 ID（可选，默认生成 UUID）

        Returns:
            ConversationHistory 实例
        """
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())

        now = datetime.now()
        return cls(
            session_id=session_id,
            messages=[],
            created_at=now,
            updated_at=now
        )


@dataclass
class ConversationSession:
    """对话会话（多会话管理）

    用于管理多个会话的元数据，每个会话包含会话ID、名称、时间戳等信息。
    会话的详细对话内容存储在对应的 ConversationHistory 中。
    """
    session_id: str               # 会话唯一标识 (UUID)
    name: str                     # 会话名称（AI 自动生成或用户手动设置）
    created_at: datetime          # 创建时间
    updated_at: datetime          # 最后更新时间
    last_accessed: datetime       # 最后访问时间
    message_count: int            # 消息数量
    archived: bool = False        # 是否已归档
    archive_path: str | None = None  # 归档文件路径（如果已归档）

    def to_dict(self) -> dict:
        """序列化为字典"""
        # 防御性编程：处理各种可能的类型
        def safe_isoformat(value):
            """安全地转换为 ISO 格式字符串"""
            if isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, str):
                # 已经是字符串，直接返回
                return value
            else:
                # 其他类型，转换或使用默认值
                print(f"[WARN] to_dict: 异常类型 {type(value)}, 使用当前时间")
                return datetime.now().isoformat()

        return {
            'session_id': self.session_id,
            'name': self.name,
            'created_at': safe_isoformat(self.created_at),
            'updated_at': safe_isoformat(self.updated_at),
            'last_accessed': safe_isoformat(self.last_accessed),
            'message_count': self.message_count,
            'archived': self.archived,
            'archive_path': self.archive_path
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationSession':
        """从字典反序列化"""
        return cls(
            session_id=data['session_id'],
            name=data['name'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            last_accessed=datetime.fromisoformat(data['last_accessed']),
            message_count=data['message_count'],
            archived=data.get('archived', False),
            archive_path=data.get('archive_path')
        )

    def touch(self) -> None:
        """更新最后访问时间"""
        self.last_accessed = datetime.now()
        self.updated_at = datetime.now()


@dataclass
class SessionInfo:
    """会话信息（用于会话列表显示）

    简化的会话信息，用于在 /sessions 命令中显示会话列表。
    """
    session_id: str       # 会话 ID
    name: str             # 会话名称
    message_count: int    # 消息数量
    last_accessed: datetime  # 最后访问时间
    is_current: bool      # 是否为当前会话

    def to_dict(self) -> dict:
        """序列化为字典"""
        # 防御性编程：处理各种可能的类型
        def safe_isoformat(value):
            """安全地转换为 ISO 格式字符串"""
            if isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, str):
                return value
            else:
                print(f"[WARN] SessionInfo.to_dict: 异常类型 {type(value)}, 使用当前时间")
                return datetime.now().isoformat()

        return {
            'session_id': self.session_id,
            'name': self.name,
            'message_count': self.message_count,
            'last_accessed': safe_isoformat(self.last_accessed),
            'is_current': self.is_current
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SessionInfo':
        """从字典反序列化"""
        return cls(
            session_id=data['session_id'],
            name=data['name'],
            message_count=data['message_count'],
            last_accessed=datetime.fromisoformat(data['last_accessed']),
            is_current=data['is_current']
        )


class SessionManager:
    """会话管理器

    负责管理多个会话的创建、切换、删除、命名和归档功能。
    """

    def __init__(self, storage_dir: str = "storage/history"):
        """初始化会话管理器

        Args:
            storage_dir: 会话存储目录
        """
        self.storage_dir = storage_dir
        self.sessions: dict[str, ConversationSession] = {}  # session_id -> ConversationSession
        self.current_session_id: str | None = None
        os.makedirs(storage_dir, exist_ok=True)
        self._load_sessions()

    def _load_sessions(self) -> None:
        """从磁盘加载所有会话元数据"""
        sessions_file = os.path.join(self.storage_dir, "sessions.json")
        if os.path.exists(sessions_file):
            try:
                with open(sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions = {
                        sid: ConversationSession.from_dict(sdata)
                        for sid, sdata in data.get('sessions', {}).items()
                    }
                    self.current_session_id = data.get('current_session_id')
            except Exception as e:
                print(f"警告：加载会话元数据失败: {e}")
                self.sessions = {}

    def _save_sessions(self) -> None:
        """保存会话元数据到磁盘"""
        sessions_file = os.path.join(self.storage_dir, "sessions.json")
        data = {
            'sessions': {
                sid: session.to_dict()
                for sid, session in self.sessions.items()
            },
            'current_session_id': self.current_session_id
        }
        with open(sessions_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_session(self, session_id: str | None = None, name: str | None = None) -> ConversationSession:
        """创建新会话

        Args:
            session_id: 会话 ID（可选，默认生成 UUID）
            name: 会话名称（可选，默认使用时间格式）

        Returns:
            新创建的 ConversationSession 实例
        """
        import uuid

        if session_id is None:
            session_id = str(uuid.uuid4())

        if name is None:
            # 使用默认命名规则（T084）
            name = datetime.now().strftime("%Y-%m-%d %H:%M")

        now = datetime.now()
        session = ConversationSession(
            session_id=session_id,
            name=name,
            created_at=now,
            updated_at=now,
            last_accessed=now,
            message_count=0,
            archived=False,
            archive_path=None
        )

        self.sessions[session_id] = session

        # 如果是第一个会话，自动设为当前会话
        if self.current_session_id is None:
            self.current_session_id = session_id

        self._save_sessions()
        return session

    def switch_session(self, session_id: str) -> bool:
        """切换到指定会话

        Args:
            session_id: 目标会话 ID

        Returns:
            是否切换成功
        """
        if session_id not in self.sessions:
            return False

        if self.sessions[session_id].archived:
            print(f"错误：无法切换到已归档的会话 {session_id}")
            return False

        self.current_session_id = session_id
        self.sessions[session_id].touch()
        self._save_sessions()
        return True

    def list_sessions(self) -> list[SessionInfo]:
        """列出所有会话

        Returns:
            SessionInfo 列表
        """
        session_list = []
        for session_id, session in self.sessions.items():
            if not session.archived:
                session_list.append(SessionInfo(
                    session_id=session.session_id,
                    name=session.name,
                    message_count=session.message_count,
                    last_accessed=session.last_accessed,
                    is_current=(session_id == self.current_session_id)
                ))
        # 按最后访问时间排序（最近访问的在前）
        session_list.sort(key=lambda x: x.last_accessed, reverse=True)
        return session_list

    def delete_session(self, session_id: str) -> bool:
        """删除会话

        Args:
            session_id: 要删除的会话 ID

        Returns:
            是否删除成功
        """
        if session_id not in self.sessions:
            return False

        # 不允许删除当前会话
        if session_id == self.current_session_id:
            print(f"错误：无法删除当前活动会话")
            return False

        # 删除会话对应的对话历史文件（通过查找匹配的文件）
        session = self.sessions[session_id]

        # 查找匹配的会话文件（通过验证 session_id）
        deleted_history = False
        if os.path.exists(self.storage_dir):
            for filename in os.listdir(self.storage_dir):
                if filename.startswith("session_") and filename.endswith(".json"):
                    filepath = os.path.join(self.storage_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if data.get("session_id") == session_id:
                                os.remove(filepath)
                                deleted_history = True
                                break
                    except Exception as e:
                        print(f"警告：检查会话文件失败 {filename}: {e}")

        if not deleted_history:
            print(f"警告：未找到会话 {session_id[:8]} 的对话历史文件")

        # 从内存中删除
        del self.sessions[session_id]
        self._save_sessions()

        # 如果没有活动会话了，创建一个默认会话
        if self.current_session_id is None:
            self.create_session()

        return True

    def auto_name_session(self, session_id: str, llm_provider, context_messages: list) -> bool:
        """使用 AI 自动生成会话名称

        Args:
            session_id: 会话 ID
            llm_provider: LLM Provider 实例
            context_messages: 上下文消息列表（前几轮对话）

        Returns:
            是否命名成功
        """
        if session_id not in self.sessions:
            return False

        try:
            # 构建提示词
            prompt = "请根据以下对话内容，生成一个简洁的会话标题（不超过10个字）：\n\n"
            for msg in context_messages[:6]:  # 前 3 轮对话
                role = "用户" if msg['role'] == 'user' else "助手"
                prompt += f"{role}: {msg['content'][:100]}\n"

            # 调用 LLM 生成标题
            response = llm_provider.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            # 提取标题（去除引号、多余空格等）
            title = response.strip().strip('"').strip("'").strip()

            # 更新会话名称
            if title and len(title) > 0:
                self.sessions[session_id].name = title
                self.sessions[session_id].updated_at = datetime.now()
                self._save_sessions()
                return True

        except Exception as e:
            print(f"警告：AI 命名失败: {e}")

        return False

    def archive_old_sessions(self, days: int = 30) -> int:
        """归档旧会话

        Args:
            days: 归档天数阈值（默认 30 天）

        Returns:
            归档的会话数量
        """
        now = datetime.now()
        archived_count = 0

        for session_id, session in list(self.sessions.items()):
            if session.archived:
                continue

            # 计算未访问天数
            days_since_access = (now - session.last_accessed).days

            if days_since_access >= days and session_id != self.current_session_id:
                # 归档会话
                archive_dir = os.path.join(self.storage_dir, "archive")
                archive_month_dir = os.path.join(archive_dir, session.created_at.strftime("%Y-%m"))
                os.makedirs(archive_month_dir, exist_ok=True)

                # 查找并移动会话文件（通过验证 session_id）
                if os.path.exists(self.storage_dir):
                    for filename in os.listdir(self.storage_dir):
                        if filename.startswith("session_") and filename.endswith(".json"):
                            src_path = os.path.join(self.storage_dir, filename)
                            try:
                                with open(src_path, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    if data.get("session_id") == session_id:
                                        # 找到匹配的文件，移动它
                                        dst_path = os.path.join(archive_month_dir, filename)
                                        import shutil
                                        shutil.move(src_path, dst_path)

                                        # 更新会话状态
                                        session.archived = True
                                        session.archive_path = dst_path
                                        archived_count += 1
                                        break
                            except Exception as e:
                                print(f"警告：检查会话文件失败 {filename}: {e}")

        # 保存更新后的元数据
        if archived_count > 0:
            self._save_sessions()

        return archived_count

    def get_current_session(self) -> ConversationSession | None:
        """获取当前活动会话

        Returns:
            当前 ConversationSession 实例或 None
        """
        if self.current_session_id is None:
            return None
        return self.sessions.get(self.current_session_id)

    def increment_message_count(self, session_id: str) -> None:
        """增加会话消息计数

        Args:
            session_id: 会话 ID
        """
        if session_id in self.sessions:
            self.sessions[session_id].message_count += 1
            self.sessions[session_id].updated_at = datetime.now()
            self._save_sessions()
