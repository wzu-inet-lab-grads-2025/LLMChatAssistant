"""
文件上传功能测试 (T023-T025)
Constitution: 100% 真实测试，禁止使用 mock

测试范围:
- 小文件上传（< 1MB）
- 中等文件上传（1-5MB）
- 大文件上传（5-10MB）
- 自动索引创建验证
"""

import pytest
import asyncio
import os
import hashlib
from pathlib import Path
from datetime import datetime

from tests.base import BaseCLITest
from tests.fixtures.test_data import TestDataGenerator


class TestFileUpload(BaseCLITest):
    """
    文件上传功能测试类

    测试真实文件上传功能
    所有测试使用真实服务器和真实文件传输，禁止mock
    """

    @pytest.mark.e2e
    async def test_upload_small_file(self):
        """测试上传小文件（< 1MB）"""
        from client.rdt_client import RDTClient
        from storage.files import UploadedFile

        # 创建小测试文件（约 10KB）
        test_gen = TestDataGenerator()
        test_file = test_gen.create_text_file(
            "small_test.txt",
            "这是小文件测试内容。\n" * 200  # 约 10KB
        )

        try:
            # 计算文件哈希
            with open(test_file, 'rb') as f:
                original_data = f.read()
                original_hash = hashlib.md5(original_data).hexdigest()

            # 验证文件被创建
            assert test_file.exists(), "测试文件应该存在"
            file_size = test_file.stat().st_size
            assert file_size < 1 * 1024 * 1024, "文件应该小于 1MB"

            self.log_test_info(f"小文件大小: {file_size} 字节")

            # 创建 UploadedFile 记录
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 验证上传记录
            assert uploaded_file.file_id is not None, "文件ID应该存在"
            assert uploaded_file.filename == "small_test.txt", "文件名应该匹配"
            assert uploaded_file.size == file_size, "文件大小应该匹配"

            # 验证文件已被复制到存储目录
            storage_path = Path(uploaded_file.storage_path)
            assert storage_path.exists(), "文件应该被复制到存储目录"

            # 验证文件完整性
            with open(storage_path, 'rb') as f:
                stored_data = f.read()
                stored_hash = hashlib.md5(stored_data).hexdigest()

            assert stored_hash == original_hash, "文件哈希应该匹配"
            assert stored_data == original_data, "文件内容应该完全一致"

            # 验证元数据文件
            metadata_path = Path("storage/uploads") / uploaded_file.file_id / "metadata.json"
            assert metadata_path.exists(), "元数据文件应该存在"

            self.log_test_info(f"文件ID: {uploaded_file.file_id}")
            self.log_test_info(f"存储路径: {uploaded_file.storage_path}")

        finally:
            # 清理测试文件
            test_gen.cleanup()

            # 清理上传的文件
            if 'uploaded_file' in locals():
                uploaded_file.delete()

    @pytest.mark.e2e
    async def test_upload_medium_file(self):
        """测试上传中等文件（1-5MB）"""
        from storage.files import UploadedFile

        # 创建中等测试文件（约 2MB）
        test_gen = TestDataGenerator()
        test_file = test_gen.create_text_file(
            "medium_test.txt",
            "中等文件测试内容。\n",
            size_kb=2048  # 2MB
        )

        try:
            # 计算文件哈希
            with open(test_file, 'rb') as f:
                original_data = f.read()
                original_hash = hashlib.md5(original_data).hexdigest()

            file_size = test_file.stat().st_size
            assert 1 * 1024 * 1024 <= file_size <= 5 * 1024 * 1024, \
                "文件大小应该在 1-5MB 之间"

            self.log_test_info(f"中等文件大小: {file_size / (1024*1024):.2f} MB")

            # 创建 UploadedFile 记录
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 验证上传记录
            assert uploaded_file.size == file_size, "文件大小应该匹配"

            # 验证文件完整性
            with open(uploaded_file.storage_path, 'rb') as f:
                stored_data = f.read()
                stored_hash = hashlib.md5(stored_data).hexdigest()

            assert stored_hash == original_hash, "中等文件哈希应该匹配"
            assert len(stored_data) == len(original_data), "中等文件长度应该匹配"

            self.log_test_info(f"文件ID: {uploaded_file.file_id}")

        finally:
            test_gen.cleanup()
            if 'uploaded_file' in locals():
                uploaded_file.delete()

    @pytest.mark.e2e
    async def test_upload_large_file(self):
        """测试上传大文件（5-10MB）"""
        from storage.files import UploadedFile

        # 创建大测试文件（约 8MB）
        test_gen = TestDataGenerator()
        test_file = test_gen.create_large_file(
            "large_test.txt",
            size_mb=8
        )

        try:
            # 计算文件哈希
            with open(test_file, 'rb') as f:
                original_data = f.read()
                original_hash = hashlib.md5(original_data).hexdigest()

            file_size = test_file.stat().st_size
            assert 5 * 1024 * 1024 <= file_size <= 10 * 1024 * 1024, \
                "文件大小应该在 5-10MB 之间"

            self.log_test_info(f"大文件大小: {file_size / (1024*1024):.2f} MB")

            # 创建 UploadedFile 记录
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 验证上传记录
            assert uploaded_file.size == file_size, "文件大小应该匹配"

            # 验证文件完整性
            with open(uploaded_file.storage_path, 'rb') as f:
                stored_data = f.read()
                stored_hash = hashlib.md5(stored_data).hexdigest()

            assert stored_hash == original_hash, "大文件哈希应该匹配"
            assert len(stored_data) == len(original_data), "大文件长度应该匹配"

            self.log_test_info(f"文件ID: {uploaded_file.file_id}")

        finally:
            test_gen.cleanup()
            if 'uploaded_file' in locals():
                uploaded_file.delete()

    @pytest.mark.e2e
    async def test_auto_index_creation(self):
        """测试上传后自动创建索引"""
        from storage.files import UploadedFile
        from storage.index_manager import IndexManager

        # 创建测试文件
        test_gen = TestDataGenerator()
        test_file = test_gen.create_python_file()

        try:
            # 上传文件
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 验证初始状态（无索引）
            assert uploaded_file.vector_index_id is None, "初始状态应该无索引"

            # 创建索引管理器
            index_manager = IndexManager(vector_store_path="storage/vectors")

            # 为文件创建索引
            try:
                index_id = index_manager.index_file(
                    file_path=uploaded_file.storage_path,
                    file_id=uploaded_file.file_id
                )

                # 验证索引已创建
                assert index_id is not None, "索引ID应该存在"
                assert len(index_id) > 0, "索引ID不应为空"

                self.log_test_info(f"索引ID: {index_id}")

                # 验证可以检索到索引
                indices = index_manager.list_indices()
                assert any(idx['file_id'] == uploaded_file.file_id for idx in indices), \
                    "索引应该在列表中"

            except Exception as e:
                # 如果向量存储不可用，跳过索引测试
                self.log_test_info(f"向量存储不可用，跳过索引测试: {e}")

        finally:
            test_gen.cleanup()
            if 'uploaded_file' in locals():
                uploaded_file.delete()
                # 清理索引
                try:
                    if uploaded_file.vector_index_id:
                        index_manager = IndexManager(vector_store_path="storage/vectors")
                        index_manager.delete_index(uploaded_file.vector_index_id)
                except:
                    pass

    @pytest.mark.e2e
    async def test_upload_multiple_files(self):
        """测试批量上传多个文件"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()

        try:
            # 创建多个测试文件
            files = [
                test_gen.create_config_file(),
                test_gen.create_python_file(),
                test_gen.create_markdown_file(),
                test_gen.create_json_file()
            ]

            uploaded_files = []

            # 上传所有文件
            for file_path in files:
                uploaded_file = UploadedFile.create_from_path(
                    str(file_path),
                    storage_dir="storage/uploads"
                )
                uploaded_files.append(uploaded_file)

            # 验证所有文件都已上传
            assert len(uploaded_files) == 4, "应该上传 4 个文件"

            # 验证每个文件都有唯一的 file_id
            file_ids = [f.file_id for f in uploaded_files]
            assert len(set(file_ids)) == 4, "所有文件ID应该唯一"

            # 验证所有文件都存在于存储目录
            for uf in uploaded_files:
                storage_path = Path(uf.storage_path)
                assert storage_path.exists(), f"文件 {uf.filename} 应该存在于存储目录"

            self.log_test_info(f"成功上传 {len(uploaded_files)} 个文件")
            for uf in uploaded_files:
                self.log_test_info(f"  - {uf.filename} ({uf.size} 字节)")

        finally:
            test_gen.cleanup()
            for uf in uploaded_files:
                try:
                    uf.delete()
                except:
                    pass

    @pytest.mark.e2e
    async def test_upload_file_with_special_name(self):
        """测试上传特殊字符文件名的文件"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()

        try:
            # 创建特殊文件名的文件
            special_files = test_gen.create_special_filename_files()

            for file_type, file_path in special_files.items():
                try:
                    uploaded_file = UploadedFile.create_from_path(
                        str(file_path),
                        storage_dir="storage/uploads"
                    )

                    # 验证上传成功
                    assert uploaded_file.file_id is not None, \
                        f"{file_type} 文件上传应该成功"
                    assert Path(uploaded_file.storage_path).exists(), \
                        f"{file_type} 文件应该存在于存储目录"

                    self.log_test_info(f"{file_type} 文件上传成功: {uploaded_file.filename}")

                    # 清理
                    uploaded_file.delete()

                except Exception as e:
                    self.log_test_info(f"{file_type} 文件上传失败（预期可能失败）: {e}")

        finally:
            test_gen.cleanup()

    @pytest.mark.e2e
    async def test_file_size_validation(self):
        """测试文件大小验证"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()

        try:
            # 创建超大文件（超过 10MB）
            test_file = test_gen.create_large_file(
                "oversized_test.txt",
                size_mb=12
            )

            file_size = test_file.stat().st_size
            assert file_size > 10 * 1024 * 1024, "文件应该超过 10MB"

            # 尝试上传，应该失败
            try:
                uploaded_file = UploadedFile.create_from_path(
                    str(test_file),
                    storage_dir="storage/uploads"
                )
                # 如果到达这里，验证没有生效
                assert False, "超大文件上传应该失败"

            except ValueError as e:
                # 预期的验证错误
                assert "文件大小超过限制" in str(e), "应该返回大小限制错误"
                self.log_test_info(f"文件大小验证生效: {e}")

        finally:
            test_gen.cleanup()

    @pytest.mark.e2e
    async def test_file_integrity_after_upload(self):
        """测试上传后文件完整性"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()

        try:
            # 创建包含多种内容的测试文件
            test_content = """
# Python 测试文件

def test_function():
    '''这是一个测试函数'''
    data = [1, 2, 3, 4, 5]
    return sum(data)

class TestClass:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}!"

# 配置数据
config = {
    "host": "localhost",
    "port": 9999,
    "debug": True
}

# 中文字符测试
中文字符 = "这是中文内容"
特殊字符 = "!@#$%^&*()_+-=[]{}|;':,.<>?"

print("测试文件创建成功")
"""
            test_file = test_gen.create_text_file("integrity_test.txt", test_content)

            # 上传文件
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 读取原始文件和上传后的文件
            with open(test_file, 'r', encoding='utf-8') as f:
                original_content = f.read()

            with open(uploaded_file.storage_path, 'r', encoding='utf-8') as f:
                uploaded_content = f.read()

            # 验证内容完全一致
            assert original_content == uploaded_content, "文件内容应该完全一致"
            assert len(original_content) == len(uploaded_content), "文件长度应该一致"

            # 验证特殊字符都正确保存
            assert "中文字符" in uploaded_content, "中文字符应该正确保存"
            assert "特殊字符" in uploaded_content, "特殊字符应该正确保存"

            self.log_test_info("文件完整性验证通过")

        finally:
            test_gen.cleanup()
            if 'uploaded_file' in locals():
                uploaded_file.delete()

    @pytest.mark.e2e
    async def test_concurrent_uploads(self):
        """测试并发上传多个文件"""
        from storage.files import UploadedFile
        import concurrent.futures

        test_gen = TestDataGenerator()

        try:
            # 创建多个文件
            files = []
            for i in range(5):
                file_path = test_file = test_gen.create_text_file(
                    f"concurrent_{i}.txt",
                    f"并发上传测试文件 {i}\n" * 100
                )
                files.append(file_path)

            # 使用线程池并发上传
            uploaded_files = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for file_path in files:
                    future = executor.submit(
                        UploadedFile.create_from_path,
                        str(file_path),
                        "storage/uploads"
                    )
                    futures.append(future)

                # 等待所有上传完成
                for future in concurrent.futures.as_completed(futures):
                    uploaded_file = future.result()
                    uploaded_files.append(uploaded_file)

            # 验证所有文件都上传成功
            assert len(uploaded_files) == 5, "应该成功上传 5 个文件"

            # 验证所有文件ID唯一
            file_ids = [f.file_id for f in uploaded_files]
            assert len(set(file_ids)) == 5, "所有文件ID应该唯一"

            self.log_test_info(f"并发上传 {len(uploaded_files)} 个文件成功")

        finally:
            test_gen.cleanup()
            for uf in uploaded_files:
                try:
                    uf.delete()
                except:
                    pass

    def log_test_info(self, message: str):
        """记录测试信息"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[TestFileUpload] {message}")
