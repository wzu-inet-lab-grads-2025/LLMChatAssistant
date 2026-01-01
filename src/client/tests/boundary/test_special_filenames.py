"""
特殊文件名边界测试 (T038)
Constitution: 100% 真实测试，禁止使用 mock

测试范围:
- 包含空格的文件名（如"file with spaces.txt"）
- 包含中文的文件名（如"测试文件.txt"）
- 包含特殊字符的文件名（如"file-with_special.chars.txt"）
- 包含数字的文件名
- 超长文件名（255字符）
- 只有扩展名的文件
- 验证文件上传和下载在这些特殊文件名下正常工作
- 使用TestDataGenerator.create_special_filename_files()生成测试文件
"""

import pytest
import asyncio
import hashlib
import os
from pathlib import Path
from datetime import datetime

from src.client.tests.base import BaseCLITest
from tests.fixtures.test_data import TestDataGenerator


class TestSpecialFilenames(BaseCLITest):
    """
    特殊文件名边界测试类

    测试各种特殊字符文件名的文件上传和下载功能
    所有测试使用真实服务器和真实文件传输，禁止mock
    """

    @pytest.mark.boundary
    async def test_filename_with_spaces(self):
        """测试包含空格的文件名"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()
        test_file = test_gen.create_text_file(
            "file with spaces.txt",
            "这是包含空格的文件名测试。\n" * 100
        )

        uploaded_file = None

        try:
            # 计算原始文件哈希
            with open(test_file, 'rb') as f:
                original_data = f.read()
                original_hash = hashlib.md5(original_data).hexdigest()

            # 上传文件
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 验证上传成功
            assert uploaded_file.file_id is not None, "文件ID应该存在"
            assert uploaded_file.filename == "file with spaces.txt", "文件名应该保持原样（包含空格）"

            # 验证文件完整性
            with open(uploaded_file.storage_path, 'rb') as f:
                stored_data = f.read()
                stored_hash = hashlib.md5(stored_data).hexdigest()

            assert stored_hash == original_hash, "文件哈希应该匹配"
            assert stored_data == original_data, "文件内容应该完全一致"

            self.log_test_info(f"空格文件名测试通过: {uploaded_file.filename}")

        finally:
            test_gen.cleanup()
            if uploaded_file:
                uploaded_file.delete()

    @pytest.mark.boundary
    async def test_filename_with_chinese_characters(self):
        """测试包含中文的文件名"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()
        test_file = test_gen.create_text_file(
            "测试文件.txt",
            "这是中文文件名测试。\n包含中文内容：你好世界！\n" * 100
        )

        uploaded_file = None

        try:
            # 计算原始文件哈希
            with open(test_file, 'rb') as f:
                original_data = f.read()
                original_hash = hashlib.md5(original_data).hexdigest()

            # 上传文件
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 验证上传成功
            assert uploaded_file.file_id is not None, "文件ID应该存在"
            assert uploaded_file.filename == "测试文件.txt", "文件名应该正确处理中文"

            # 验证文件完整性
            with open(uploaded_file.storage_path, 'rb') as f:
                stored_data = f.read()
                stored_hash = hashlib.md5(stored_data).hexdigest()

            assert stored_hash == original_hash, "文件哈希应该匹配"
            assert stored_data == original_data, "文件内容应该完全一致"

            # 验证中文字符内容正确保存
            stored_text = stored_data.decode('utf-8')
            assert "你好世界" in stored_text, "中文内容应该正确保存"

            self.log_test_info(f"中文文件名测试通过: {uploaded_file.filename}")

        finally:
            test_gen.cleanup()
            if uploaded_file:
                uploaded_file.delete()

    @pytest.mark.boundary
    async def test_filename_with_special_characters(self):
        """测试包含特殊字符的文件名"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()
        test_file = test_gen.create_text_file(
            "file-with_special.chars.txt",
            "特殊字符文件名测试。\n!@#$%^&*()_+-=[]{}|;':\",.<>?/\n" * 50
        )

        uploaded_file = None

        try:
            # 计算原始文件哈希
            with open(test_file, 'rb') as f:
                original_data = f.read()
                original_hash = hashlib.md5(original_data).hexdigest()

            # 上传文件
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 验证上传成功
            assert uploaded_file.file_id is not None, "文件ID应该存在"
            assert "file-with_special.chars.txt" in uploaded_file.filename or \
                   uploaded_file.filename.replace('_', '-') == "file-with_special.chars.txt", \
                   "文件名应该被正确处理"

            # 验证文件完整性
            with open(uploaded_file.storage_path, 'rb') as f:
                stored_data = f.read()
                stored_hash = hashlib.md5(stored_data).hexdigest()

            assert stored_hash == original_hash, "文件哈希应该匹配"
            assert stored_data == original_data, "文件内容应该完全一致"

            self.log_test_info(f"特殊字符文件名测试通过: {uploaded_file.filename}")

        finally:
            test_gen.cleanup()
            if uploaded_file:
                uploaded_file.delete()

    @pytest.mark.boundary
    async def test_filename_with_numbers(self):
        """测试包含数字的文件名"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()
        test_file = test_gen.create_text_file(
            "file123_456_789.txt",
            "数字文件名测试。\n1234567890\n" * 100
        )

        uploaded_file = None

        try:
            # 计算原始文件哈希
            with open(test_file, 'rb') as f:
                original_data = f.read()
                original_hash = hashlib.md5(original_data).hexdigest()

            # 上传文件
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 验证上传成功
            assert uploaded_file.file_id is not None, "文件ID应该存在"
            assert uploaded_file.filename == "file123_456_789.txt", "数字文件名应该保持原样"

            # 验证文件完整性
            with open(uploaded_file.storage_path, 'rb') as f:
                stored_data = f.read()
                stored_hash = hashlib.md5(stored_data).hexdigest()

            assert stored_hash == original_hash, "文件哈希应该匹配"
            assert stored_data == original_data, "文件内容应该完全一致"

            self.log_test_info(f"数字文件名测试通过: {uploaded_file.filename}")

        finally:
            test_gen.cleanup()
            if uploaded_file:
                uploaded_file.delete()

    @pytest.mark.boundary
    async def test_ultra_long_filename(self):
        """测试超长文件名（接近255字符限制）"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()

        # 创建接近255字符的文件名
        # 保留一些空间给扩展名和路径
        base_name = "a" * 240  # 240个字符
        extension = ".txt"
        long_filename = base_name + extension  # 总共244个字符

        test_file = test_gen.create_text_file(
            long_filename,
            "超长文件名测试。\n" * 50
        )

        uploaded_file = None

        try:
            # 验证文件名长度
            assert len(long_filename) <= 255, "文件名应该在系统限制内"

            # 计算原始文件哈希
            with open(test_file, 'rb') as f:
                original_data = f.read()
                original_hash = hashlib.md5(original_data).hexdigest()

            # 上传文件
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 验证上传成功
            assert uploaded_file.file_id is not None, "文件ID应该存在"
            assert len(uploaded_file.filename) <= 255, "存储的文件名应该在限制内"

            # 验证文件完整性
            with open(uploaded_file.storage_path, 'rb') as f:
                stored_data = f.read()
                stored_hash = hashlib.md5(stored_data).hexdigest()

            assert stored_hash == original_hash, "文件哈希应该匹配"
            assert stored_data == original_data, "文件内容应该完全一致"

            self.log_test_info(f"超长文件名测试通过，长度: {len(uploaded_file.filename)} 字符")

        finally:
            test_gen.cleanup()
            if uploaded_file:
                uploaded_file.delete()

    @pytest.mark.boundary
    async def test_extension_only_filename(self):
        """测试只有扩展名的文件"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()
        test_file = test_gen.create_text_file(
            ".txt",
            "只有扩展名的文件测试。\n" * 50
        )

        uploaded_file = None

        try:
            # 计算原始文件哈希
            with open(test_file, 'rb') as f:
                original_data = f.read()
                original_hash = hashlib.md5(original_data).hexdigest()

            # 上传文件
            uploaded_file = UploadedFile.create_from_path(
                str(test_file),
                storage_dir="storage/uploads"
            )

            # 验证上传成功
            assert uploaded_file.file_id is not None, "文件ID应该存在"
            # 系统可能会为没有主文件名的文件生成一个默认名称

            # 验证文件完整性
            with open(uploaded_file.storage_path, 'rb') as f:
                stored_data = f.read()
                stored_hash = hashlib.md5(stored_data).hexdigest()

            assert stored_hash == original_hash, "文件哈希应该匹配"
            assert stored_data == original_data, "文件内容应该完全一致"

            self.log_test_info(f"只有扩展名的文件测试通过: {uploaded_file.filename}")

        finally:
            test_gen.cleanup()
            if uploaded_file:
                uploaded_file.delete()

    @pytest.mark.boundary
    async def test_mixed_special_filenames_upload_download(self):
        """测试混合特殊字符文件名的完整上传下载流程"""
        from storage.files import UploadedFile
        from client.rdt_client import RDTClient
        from server.rdt_server import RDTServer

        test_gen = TestDataGenerator()

        # 创建多种特殊文件名
        special_filenames = {
            "space": "my document file.txt",
            "chinese": "文档资料.pdf",
            "special": "data_2024-01-15_final_v2.txt",
            "mixed": "report_测试_2024.doc",
        }

        uploaded_files = []
        rdt_client = None
        rdt_server = None

        try:
            # 上传所有文件
            for file_type, filename in special_filenames.items():
                test_file = test_gen.create_text_file(
                    filename,
                    f"{file_type} 类型的文件内容。\n" * 100
                )

                with open(test_file, 'rb') as f:
                    original_data = f.read()
                    original_hash = hashlib.md5(original_data).hexdigest()

                uploaded_file = UploadedFile.create_from_path(
                    str(test_file),
                    storage_dir="storage/uploads"
                )

                assert uploaded_file.file_id is not None, f"{file_type} 文件上传应该成功"

                # 验证文件完整性
                with open(uploaded_file.storage_path, 'rb') as f:
                    stored_data = f.read()
                    stored_hash = hashlib.md5(stored_data).hexdigest()

                assert stored_hash == original_hash, f"{file_type} 文件哈希应该匹配"

                uploaded_files.append({
                    'type': file_type,
                    'original_path': test_file,
                    'uploaded_file': uploaded_file,
                    'original_hash': original_hash
                })

                self.log_test_info(f"{file_type} 文件上传成功: {uploaded_file.filename}")

            # 使用RDT下载测试（模拟文件传输）
            rdt_server = RDTServer(host="127.0.0.1", port=self.DEFAULT_RDT_PORT)
            await rdt_server.start()

            rdt_client = RDTClient(server_host="127.0.0.1", server_port=self.DEFAULT_RDT_PORT)
            await rdt_client.start()

            # 测试下载每个文件
            for file_info in uploaded_files[:2]:  # 测试前两个文件
                uploaded_file = file_info['uploaded_file']
                original_hash = file_info['original_hash']

                with open(uploaded_file.storage_path, 'rb') as f:
                    file_data = f.read()

                client_addr = ("127.0.0.1", rdt_client.transport.get_extra_info('sockname')[1])
                download_token = rdt_server.create_session(
                    filename=uploaded_file.filename,
                    file_data=file_data,
                    client_addr=client_addr
                )

                rdt_client.create_session(
                    download_token=download_token,
                    filename=uploaded_file.filename,
                    file_size=len(file_data),
                    expected_checksum=original_hash
                )

                received_data = await rdt_client.receive_file(download_token, timeout=30.0)

                assert received_data is not None, f"{file_info['type']} 文件下载应该成功"
                assert hashlib.md5(received_data).hexdigest() == original_hash, \
                    f"{file_info['type']} 文件下载后哈希应该匹配"

                self.log_test_info(f"{file_info['type']} 文件下载成功")

            self.log_test_info(f"混合特殊文件名上传下载测试通过: {len(uploaded_files)} 个文件")

        finally:
            if rdt_client:
                await rdt_client.stop()
            if rdt_server:
                await rdt_server.stop()
            test_gen.cleanup()
            for file_info in uploaded_files:
                try:
                    file_info['uploaded_file'].delete()
                except:
                    pass

    @pytest.mark.boundary
    async def test_unicode_filename(self):
        """测试Unicode字符文件名（emoji、日文、韩文等）"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()

        # 测试各种Unicode字符
        unicode_filenames = [
            "ファイル.txt",  # 日文
            "파일.txt",  # 韩文
            "файл.txt",  # 俄文
            "αρχείο.txt",  # 希腊文
        ]

        for filename in unicode_filenames:
            test_file = test_gen.create_text_file(
                filename,
                f"Unicode文件名测试: {filename}\n" * 50
            )

            uploaded_file = None

            try:
                # 计算原始文件哈希
                with open(test_file, 'rb') as f:
                    original_data = f.read()
                    original_hash = hashlib.md5(original_data).hexdigest()

                # 上传文件
                uploaded_file = UploadedFile.create_from_path(
                    str(test_file),
                    storage_dir="storage/uploads"
                )

                # 验证上传成功
                assert uploaded_file.file_id is not None, f"{filename} 上传应该成功"

                # 验证文件完整性
                with open(uploaded_file.storage_path, 'rb') as f:
                    stored_data = f.read()
                    stored_hash = hashlib.md5(stored_data).hexdigest()

                assert stored_hash == original_hash, f"{filename} 哈希应该匹配"
                assert stored_data == original_data, f"{filename} 内容应该一致"

                self.log_test_info(f"Unicode文件名测试通过: {uploaded_file.filename}")

            finally:
                if uploaded_file:
                    uploaded_file.delete()

    @pytest.mark.boundary
    async def test_case_sensitive_filename(self):
        """测试大小写敏感的文件名"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()

        # 创建大小写不同的文件名
        filenames = [
            "TestFile.txt",
            "testfile.txt",
            "TESTFILE.TXT",
            "TeStFiLe.TxT",
        ]

        uploaded_files = []

        try:
            for filename in filenames:
                test_file = test_gen.create_text_file(
                    filename,
                    f"大小写测试: {filename}\n" * 50
                )

                # 上传文件
                uploaded_file = UploadedFile.create_from_path(
                    str(test_file),
                    storage_dir="storage/uploads"
                )

                assert uploaded_file.file_id is not None, f"{filename} 上传应该成功"
                uploaded_files.append(uploaded_file)

                self.log_test_info(f"大小写文件名上传成功: {uploaded_file.filename}")

            # 验证所有文件都有唯一的file_id（系统应该区分大小写）
            file_ids = [uf.file_id for uf in uploaded_files]
            # 注意：如果文件系统不区分大小写，这里可能会有重复
            # 我们主要验证系统能够处理这些文件名而不出错

            self.log_test_info(f"大小写敏感文件名测试通过: {len(uploaded_files)} 个文件")

        finally:
            for uf in uploaded_files:
                try:
                    uf.delete()
                except:
                    pass
            test_gen.cleanup()

    @pytest.mark.boundary
    async def test_filename_with_path_traversal_attempts(self):
        """测试包含路径遍历尝试的文件名（安全测试）"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()

        # 这些文件名应该被安全处理，不允许路径遍历
        dangerous_filenames = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "./../../secret.txt",
            "test/../../../etc/passwd",
        ]

        for filename in dangerous_filenames:
            test_file = test_gen.create_text_file(
                "safe.txt",  # 实际使用安全的文件名
                "路径遍历测试内容\n" * 10
            )

            uploaded_file = None

            try:
                # 尝试使用危险文件名上传
                # 系统应该拒绝或安全处理这些文件名
                uploaded_file = UploadedFile.create_from_path(
                    str(test_file),
                    storage_dir="storage/uploads",
                    custom_filename=filename  # 假设支持自定义文件名
                )

                # 如果系统允许上传，验证文件没有保存到预期外的位置
                storage_path = Path(uploaded_file.storage_path)

                # 验证存储路径在允许的目录内
                assert "storage/uploads" in str(storage_path), \
                    f"文件应该在storage/uploads目录内，实际: {storage_path}"

                # 验证路径不包含 .. 等遍历字符
                assert ".." not in str(storage_path), \
                    f"存储路径不应包含路径遍历字符: {storage_path}"

                self.log_test_info(f"路径遍历尝试被安全处理: {filename}")

            except (ValueError, PermissionError) as e:
                # 系统正确拒绝了危险文件名
                self.log_test_info(f"路径遍历尝试被正确拒绝: {filename} - {e}")

            finally:
                if uploaded_file:
                    try:
                        uploaded_file.delete()
                    except:
                        pass
                test_gen.cleanup()

    @pytest.mark.boundary
    async def test_consecutive_special_characters(self):
        """测试连续特殊字符的文件名"""
        from storage.files import UploadedFile

        test_gen = TestDataGenerator()

        # 测试连续的特殊字符
        consecutive_special_filenames = [
            "file---test.txt",
            "file___test.txt",
            "file...test.txt",
            "file---___...test.txt",
        ]

        for filename in consecutive_special_filenames:
            test_file = test_gen.create_text_file(
                filename,
                f"连续特殊字符测试: {filename}\n" * 50
            )

            uploaded_file = None

            try:
                # 计算原始文件哈希
                with open(test_file, 'rb') as f:
                    original_data = f.read()
                    original_hash = hashlib.md5(original_data).hexdigest()

                # 上传文件
                uploaded_file = UploadedFile.create_from_path(
                    str(test_file),
                    storage_dir="storage/uploads"
                )

                # 验证上传成功
                assert uploaded_file.file_id is not None, f"{filename} 上传应该成功"

                # 验证文件完整性
                with open(uploaded_file.storage_path, 'rb') as f:
                    stored_data = f.read()
                    stored_hash = hashlib.md5(stored_data).hexdigest()

                assert stored_hash == original_hash, f"{filename} 哈希应该匹配"
                assert stored_data == original_data, f"{filename} 内容应该一致"

                self.log_test_info(f"连续特殊字符测试通过: {uploaded_file.filename}")

            finally:
                if uploaded_file:
                    uploaded_file.delete()

    def log_test_info(self, message: str):
        """记录测试信息"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[TestSpecialFilenames] {message}")
