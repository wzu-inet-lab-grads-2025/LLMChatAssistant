"""
文件管理模块

提供上传文件的管理和验证功能。
遵循章程：数据持久化到 storage/uploads/ 目录，文件大小限制 10MB
"""

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UploadedFile:
    """上传文件"""
    file_id: str          # 文件唯一标识 (UUID)
    filename: str         # 原始文件名
    size: int             # 文件大小（字节）
    content_type: str     # 内容类型 (text/plain, etc.)
    storage_path: str     # 存储路径
    uploaded_at: datetime # 上传时间
    vector_index_id: Optional[str] = None  # 关联的向量索引 ID

    MAX_SIZE = 10 * 1024 * 1024  # 10MB

    def validate_size(self, max_size: int = None) -> bool:
        """验证文件大小

        Args:
            max_size: 最大文件大小（字节），默认 10MB

        Returns:
            是否在大小限制内
        """
        if max_size is None:
            max_size = self.MAX_SIZE
        return self.size <= max_size

    def validate_filename(self) -> bool:
        """验证文件名安全性

        Returns:
            文件名是否安全（不包含路径遍历字符）
        """
        # 检查路径遍历字符
        dangerous_patterns = ['../', '..\\', '/', '\\']
        for pattern in dangerous_patterns:
            if pattern in self.filename:
                return False
        return True

    def validate_content_type(self) -> bool:
        """验证内容类型

        Returns:
            是否为支持的纯文本类型
        """
        # 支持的纯文本类型
        supported_types = [
            'text/plain',
            'text/html',
            'text/css',
            'text/javascript',
            'application/json',
            'application/xml',
            'application/yaml',
            'application/x-yaml',
            '',
            None  # 允许未知类型
        ]
        return self.content_type in supported_types or self.content_type.startswith('text/')

    def validate(self) -> tuple[bool, str]:
        """完整验证

        Returns:
            (是否有效, 错误消息)
        """
        if not self.validate_size():
            return False, f"文件大小超过限制 ({self.size} > {self.MAX_SIZE} 字节)"

        if not self.validate_filename():
            return False, f"文件名包含非法字符: {self.filename}"

        if not self.validate_content_type():
            return False, f"不支持的内容类型: {self.content_type}（仅支持纯文本文件）"

        return True, ""

    def save_metadata(self, storage_dir: str = "storage/uploads"):
        """保存文件元数据

        Args:
            storage_dir: 存储目录
        """
        os.makedirs(storage_dir, exist_ok=True)

        metadata_path = os.path.join(storage_dir, self.file_id, "metadata.json")

        data = {
            "file_id": self.file_id,
            "filename": self.filename,
            "size": self.size,
            "content_type": self.content_type,
            "storage_path": self.storage_path,
            "uploaded_at": self.uploaded_at.isoformat(),
            "vector_index_id": self.vector_index_id
        }

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_metadata(cls, file_id: str, storage_dir: str = "storage/uploads") -> Optional['UploadedFile']:
        """加载文件元数据

        Args:
            file_id: 文件 ID
            storage_dir: 存储目录

        Returns:
            UploadedFile 实例或 None
        """
        metadata_path = os.path.join(storage_dir, file_id, "metadata.json")

        if not os.path.exists(metadata_path):
            return None

        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return cls(
            file_id=data["file_id"],
            filename=data["filename"],
            size=data["size"],
            content_type=data["content_type"],
            storage_path=data["storage_path"],
            uploaded_at=datetime.fromisoformat(data["uploaded_at"]),
            vector_index_id=data.get("vector_index_id")
        )

    @classmethod
    def create_from_path(cls, file_path: str, filename: str = None, storage_dir: str = "storage/uploads") -> 'UploadedFile':
        """从文件路径创建 UploadedFile 实例

        Args:
            file_path: 文件路径
            filename: 文件名（可选，默认使用原文件名）
            storage_dir: 存储目录

        Returns:
            UploadedFile 实例

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件验证失败
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在：{file_path}")

        if filename is None:
            filename = os.path.basename(file_path)

        size = os.path.getsize(file_path)

        # 创建新实例
        file_id = str(uuid.uuid4())
        uploaded_file = cls(
            file_id=file_id,
            filename=filename,
            size=size,
            content_type='text/plain',  # 简化处理，默认为纯文本
            storage_path=file_path,
            uploaded_at=datetime.now()
        )

        # 验证文件
        is_valid, error_msg = uploaded_file.validate()
        if not is_valid:
            raise ValueError(f"文件验证失败：{error_msg}")

        # 创建存储目录
        target_dir = os.path.join(storage_dir, file_id)
        os.makedirs(target_dir, exist_ok=True)

        # 复制文件到存储目录
        target_path = os.path.join(target_dir, filename)
        import shutil
        shutil.copy2(file_path, target_path)

        # 更新 storage_path
        uploaded_file.storage_path = target_path

        # 保存元数据
        uploaded_file.save_metadata(storage_dir)

        return uploaded_file

    @classmethod
    def create_from_content(cls, content: str, filename: str, storage_dir: str = "storage/uploads") -> 'UploadedFile':
        """从内容创建 UploadedFile 实例

        Args:
            content: 文件内容
            filename: 文件名
            storage_dir: 存储目录

        Returns:
            UploadedFile 实例

        Raises:
            ValueError: 文件验证失败
        """
        # 创建新实例
        file_id = str(uuid.uuid4())
        size = len(content.encode('utf-8'))

        uploaded_file = cls(
            file_id=file_id,
            filename=filename,
            size=size,
            content_type='text/plain',
            storage_path="",  # 稍后设置
            uploaded_at=datetime.now()
        )

        # 验证文件
        is_valid, error_msg = uploaded_file.validate()
        if not is_valid:
            raise ValueError(f"文件验证失败：{error_msg}")

        # 创建存储目录
        target_dir = os.path.join(storage_dir, file_id)
        os.makedirs(target_dir, exist_ok=True)

        # 写入文件
        target_path = os.path.join(target_dir, filename)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 更新 storage_path
        uploaded_file.storage_path = target_path

        # 保存元数据
        uploaded_file.save_metadata(storage_dir)

        return uploaded_file

    def read_content(self) -> str:
        """读取文件内容

        Returns:
            文件内容
        """
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            return f.read()

    def delete(self, storage_dir: str = "storage/uploads"):
        """删除文件及其元数据

        Args:
            storage_dir: 存储目录
        """
        # 删除文件
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)

        # 删除元数据
        metadata_path = os.path.join(storage_dir, self.file_id, "metadata.json")
        if os.path.exists(metadata_path):
            os.remove(metadata_path)

        # 尝试删除空目录
        dir_path = os.path.join(storage_dir, self.file_id)
        if os.path.exists(dir_path) and not os.listdir(dir_path):
            os.rmdir(dir_path)
