"""
文件上传工具模块

提供文件上传功能，支持文件类型验证、大小限制和自动索引。
遵循章程：数据持久化到 storage/uploads/ 目录，文件大小限制 10MB
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .base import Tool, ToolExecutionResult
from ..storage.files import UploadedFile
from ..storage.index_manager import IndexManager


# 配置日志
logger = logging.getLogger('file_operations')


@dataclass
class FileUploadTool(Tool):
    """文件上传工具"""

    name: str = "file_upload"
    description: str = "接收并保存用户上传的文件，支持自动索引"
    timeout: int = 30  # 上传+索引超时时间（秒）

    index_manager: Optional[IndexManager] = None
    storage_dir: str = "storage/uploads"

    def validate_args(
        self,
        filename: str,
        content: str,
        content_type: str = "text/plain",
        **kwargs
    ) -> tuple[bool, str]:
        """验证参数

        Args:
            filename: 文件名
            content: 文件内容
            content_type: MIME类型

        Returns:
            (是否有效, 错误消息)
        """
        # 1. 文件名验证（无路径遍历字符）
        dangerous_patterns = ['../', '..\\', '/', '\\']
        for pattern in dangerous_patterns:
            if pattern in filename:
                return False, f"文件名包含非法字符: {pattern}"

        # 2. 内容大小验证
        content_bytes = content.encode('utf-8') if isinstance(content, str) else content
        if len(content_bytes) > 10 * 1024 * 1024:
            return False, f"文件大小超过限制 ({len(content_bytes)} > 10485760 字节)"

        # 3. 内容类型验证
        supported_types = [
            'text/plain', 'text/html', 'text/css', 'text/javascript',
            'application/json', 'application/xml', 'application/yaml',
            'application/x-yaml'
        ]
        if content_type not in supported_types and not content_type.startswith('text/'):
            return False, f"不支持的文件类型: {content_type}（仅支持文本文件）"

        return True, ""

    def execute(
        self,
        filename: str,
        content: str,
        content_type: str = "text/plain",
        **kwargs
    ) -> ToolExecutionResult:
        """执行文件上传

        Args:
            filename: 文件名
            content: 文件内容
            content_type: MIME类型

        Returns:
            ToolExecutionResult: 执行结果
        """
        start_time = time.time()

        try:
            # 验证参数
            is_valid, error_msg = self.validate_args(
                filename=filename,
                content=content,
                content_type=content_type
            )
            if not is_valid:
                return ToolExecutionResult(
                    success=False,
                    output="",
                    error=error_msg,
                    duration=time.time() - start_time
                )

            # 创建UploadedFile实例
            uploaded_file = UploadedFile.create_from_content(
                content=content,
                filename=filename,
                storage_dir=self.storage_dir
            )

            # 自动索引
            indexed = False
            if self.index_manager:
                try:
                    success, msg = self.index_manager.ensure_indexed(
                        uploaded_file.storage_path
                    )
                    indexed = success
                    if not success:
                        logger.warning(f"文件索引失败: {msg}")
                except Exception as e:
                    logger.warning(f"文件索引异常: {str(e)}")
                    indexed = False

            # 记录日志
            logger.info(
                f"[UPLOAD] file_id={uploaded_file.file_id} "
                f"filename={filename} size={uploaded_file.size} "
                f"indexed={indexed} status=success"
            )

            # 返回结果
            result = {
                "file_id": uploaded_file.file_id,
                "filename": filename,
                "size": uploaded_file.size,
                "storage_path": uploaded_file.storage_path,
                "indexed": indexed,
                "message": "文件已上传并建立索引" if indexed else "文件已上传（索引未建立）"
            }

            duration = time.time() - start_time
            return ToolExecutionResult(
                success=True,
                output=json.dumps(result, ensure_ascii=False),
                error=None,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[UPLOAD] filename={filename} status=failed error={str(e)}")
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"文件上传失败: {str(e)}",
                duration=duration
            )
