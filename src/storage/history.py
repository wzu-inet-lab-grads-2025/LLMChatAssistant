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
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "status": self.status,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ToolCall':
        """从字典创建实例"""
        return cls(
            tool_name=data["tool_name"],
            arguments=data["arguments"],
            result=data["result"],
            status=data["status"],
            duration=data["duration"],
            timestamp=datetime.fromisoformat(data["timestamp"])
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
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ChatMessage':
        """从字典创建实例"""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
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

    def save(self, storage_dir: str = "storage/history"):
        """保存对话历史到磁盘

        Args:
            storage_dir: 存储目录
        """
        os.makedirs(storage_dir, exist_ok=True)

        # 使用日期作为文件名
        filename = f"session_{self.created_at.strftime('%Y%m%d')}_{self.session_id[:8]}.json"
        filepath = os.path.join(storage_dir, filename)

        data = {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
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

        # 尝试找到匹配的会话文件
        for filename in os.listdir(storage_dir):
            if filename.startswith(f"session_") and session_id[:8] in filename:
                filepath = os.path.join(storage_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    return cls(
                        session_id=data["session_id"],
                        messages=[ChatMessage.from_dict(msg) for msg in data["messages"]],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        updated_at=datetime.fromisoformat(data["updated_at"])
                    )
                except Exception as e:
                    print(f"警告：加载对话历史失败 {filename}: {e}")
                    return None

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
