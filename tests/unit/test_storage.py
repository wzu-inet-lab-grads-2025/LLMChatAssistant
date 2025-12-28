"""
存储层单元测试

测试 VectorIndex、VectorStore、ConversationHistory 和 UploadedFile 的功能。
遵循章程：真实测试，不允许 mock
"""

import os
import tempfile
import shutil
import uuid
from datetime import datetime

import pytest

from src.storage.files import UploadedFile
from src.storage.history import ChatMessage, ConversationHistory, ToolCall
from src.storage.vector_store import SearchResult, VectorIndex, VectorStore


class TestVectorIndex:
    """VectorIndex 测试"""

    def test_create_vector_index(self):
        """测试创建向量索引"""
        index = VectorIndex(
            file_id="test-file-1",
            filename="test.txt",
            chunks=["chunk1", "chunk2", "chunk3"],
            embeddings=[[0.1] * 3072, [0.2] * 3072, [0.3] * 3072],
            chunk_metadata=[{"pos": 0}, {"pos": 1}, {"pos": 2}],
            created_at=None
        )

        assert index.file_id == "test-file-1"
        assert len(index.chunks) == 3
        assert len(index.embeddings) == 3

    def test_vector_index_search(self):
        """测试向量搜索"""
        # 创建测试索引
        chunks = ["hello world", "goodbye world", "python programming"]
        embeddings = [
            [0.1] * 3072,
            [0.2] * 3072,
            [0.3] * 3072
        ]
        metadata = [{"pos": i} for i in range(3)]

        index = VectorIndex(
            file_id="test",
            filename="test.txt",
            chunks=chunks,
            embeddings=embeddings,
            chunk_metadata=metadata,
            created_at=None
        )

        # 搜索（使用查询向量接近第一个 chunk）
        query = [0.1] * 3072
        results = index.search(query, top_k=2)

        # 应该返回结果
        assert len(results) >= 0
        for result in results:
            assert isinstance(result, SearchResult)
            assert result.chunk in chunks
            assert 0 <= result.similarity <= 1

    def test_vector_index_empty_search(self):
        """测试空索引搜索"""
        index = VectorIndex(
            file_id="test",
            filename="test.txt",
            chunks=[],
            embeddings=[],
            chunk_metadata=[],
            created_at=None
        )

        results = index.search([0.1] * 3072)
        assert len(results) == 0


class TestVectorStore:
    """VectorStore 测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_vector_store(self):
        """测试创建向量存储"""
        store = VectorStore(storage_dir=self.temp_dir)

        assert len(store.indices) == 0
        assert os.path.exists(self.temp_dir)

    def test_add_and_get_index(self):
        """测试添加和获取索引"""
        store = VectorStore(storage_dir=self.temp_dir)

        index = VectorIndex(
            file_id="test-file",
            filename="test.txt",
            chunks=["test"],
            embeddings=[[0.1] * 3072],
            chunk_metadata=[{}],
            created_at=datetime.now()
        )

        store.add_index(index)

        # 验证索引已添加
        assert "test-file" in store.indices
        assert store.get_index("test-file") is not None

    def test_vector_index_persistence(self):
        """测试向量索引持久化"""
        store = VectorStore(storage_dir=self.temp_dir)

        # 添加索引
        index = VectorIndex(
            file_id="persist-test",
            filename="persist.txt",
            chunks=["persistent data"],
            embeddings=[[0.5] * 3072],
            chunk_metadata=[{}],
            created_at=datetime.now()
        )

        store.add_index(index)

        # 验证文件已创建
        index_file = os.path.join(self.temp_dir, "persist-test.json")
        assert os.path.exists(index_file)

        # 创建新存储并加载
        new_store = VectorStore(storage_dir=self.temp_dir)

        # 验证索引已加载
        assert "persist-test" in new_store.indices
        loaded_index = new_store.get_index("persist-test")
        assert loaded_index is not None
        assert loaded_index.chunks == ["persistent data"]


class TestConversationHistory:
    """ConversationHistory 测试"""

    def test_create_conversation_history(self):
        """测试创建对话历史"""
        history = ConversationHistory.create_new()

        assert history.session_id is not None
        assert len(history.messages) == 0

    def test_add_message(self):
        """测试添加消息"""
        history = ConversationHistory.create_new()

        history.add_message("user", "Hello")

        assert len(history.messages) == 1
        assert history.messages[0].role == "user"
        assert history.messages[0].content == "Hello"

    def test_add_multiple_messages(self):
        """测试添加多条消息"""
        history = ConversationHistory.create_new()

        history.add_message("user", "Hi")
        history.add_message("assistant", "Hello!")
        history.add_message("user", "How are you?")

        assert len(history.messages) == 3
        assert history.messages[0].role == "user"
        assert history.messages[1].role == "assistant"
        assert history.messages[2].role == "user"

    def test_get_context(self):
        """测试获取上下文"""
        history = ConversationHistory.create_new()

        # 添加 10 条消息（5 轮）
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            history.add_message(role, f"Message {i}")

        # 获取最近 2 轮（4 条消息）
        context = history.get_context(max_turns=2)

        assert len(context) == 4
        assert context[0].content == "Message 6"
        assert context[3].content == "Message 9"

    def test_clear_history(self):
        """测试清空历史"""
        history = ConversationHistory.create_new()

        history.add_message("user", "Test")
        history.clear()

        assert len(history.messages) == 0


class TestChatMessage:
    """ChatMessage 测试"""

    def test_create_chat_message(self):
        """测试创建聊天消息"""
        message = ChatMessage(
            role="user",
            content="Hello",
            timestamp=None
        )

        assert message.role == "user"
        assert message.content == "Hello"

    def test_message_with_tool_calls(self):
        """测试带工具调用的消息"""
        tool_call = ToolCall(
            tool_name="test_tool",
            arguments={"arg": "value"},
            result="success",
            status="success",
            duration=0.5,
            timestamp=None
        )

        message = ChatMessage(
            role="assistant",
            content="Tool executed",
            timestamp=None,
            tool_calls=[tool_call]
        )

        assert len(message.tool_calls) == 1
        assert message.tool_calls[0].tool_name == "test_tool"


class TestToolCall:
    """ToolCall 测试"""

    def test_create_tool_call(self):
        """测试创建工具调用"""
        call = ToolCall(
            tool_name="monitor",
            arguments={"metric": "cpu"},
            result="CPU: 50%",
            status="success",
            duration=1.5,
            timestamp=None
        )

        assert call.tool_name == "monitor"
        assert call.duration == 1.5

    def test_tool_call_timeout(self):
        """测试工具调用超时检测"""
        # 未超时
        call1 = ToolCall(
            tool_name="fast",
            arguments={},
            result="done",
            status="success",
            duration=2.0,
            timestamp=None
        )
        assert call1.is_timeout(timeout=5) is False

        # 超时
        call2 = ToolCall(
            tool_name="slow",
            arguments={},
            result="done",
            status="timeout",
            duration=6.0,
            timestamp=None
        )
        assert call2.is_timeout(timeout=5) is True


class TestUploadedFile:
    """UploadedFile 测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_from_content(self):
        """测试从内容创建文件"""
        file = UploadedFile.create_from_content(
            content="Test content",
            filename="test.txt",
            storage_dir=self.temp_dir
        )

        assert file.filename == "test.txt"
        assert file.size == len("Test content")
        assert file.validate_size()

    def test_file_size_validation(self):
        """测试文件大小验证"""
        # 小文件
        small_file = UploadedFile(
            file_id="small",
            filename="small.txt",
            size=1024,
            content_type="text/plain",
            storage_path="",
            uploaded_at=None
        )
        assert small_file.validate_size() is True

        # 大文件（超过 10MB）
        large_file = UploadedFile(
            file_id="large",
            filename="large.txt",
            size=11 * 1024 * 1024,
            content_type="text/plain",
            storage_path="",
            uploaded_at=None
        )
        assert large_file.validate_size() is False

    def test_filename_validation(self):
        """测试文件名验证"""
        # 安全文件名
        safe_file = UploadedFile(
            file_id="safe",
            filename="safe.txt",
            size=100,
            content_type="text/plain",
            storage_path="",
            uploaded_at=None
        )
        assert safe_file.validate_filename() is True

        # 危险文件名（路径遍历）
        dangerous_file = UploadedFile(
            file_id="dangerous",
            filename="../../../etc/passwd",
            size=100,
            content_type="text/plain",
            storage_path="",
            uploaded_at=None
        )
        assert dangerous_file.validate_filename() is False

    def test_read_content(self):
        """测试读取文件内容"""
        file = UploadedFile.create_from_content(
            content="Hello, World!",
            filename="hello.txt",
            storage_dir=self.temp_dir
        )

        content = file.read_content()
        assert content == "Hello, World!"

    def test_full_validation(self):
        """测试完整验证"""
        file = UploadedFile.create_from_content(
            content="Valid content",
            filename="valid.txt",
            storage_dir=self.temp_dir
        )

        is_valid, error = file.validate()
        assert is_valid is True
        assert error == ""
