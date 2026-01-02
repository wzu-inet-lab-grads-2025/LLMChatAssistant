"""
文件索引管理工具模块

提供文件索引和上下文管理功能，支持代词引用（"这个文件"、"之前上传的"）。
遵循章程 v1.5.1 - 协议层分离原则：
- Agent工具不处理实际文件上传（协议层处理）
- file_upload负责文件索引和上下文管理
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .base import Tool, ToolExecutionResult


# 配置日志
logger = logging.getLogger('file_operations')


@dataclass
class FileUploadTool(Tool):
    """文件索引和上下文管理工具

    注意：此工具不处理文件上传，文件上传由协议层完成

    功能：
    1. 记录已上传文件的元数据到对话历史
    2. 在历史记录中建立文件索引（便于后续引用）
    3. 支持自然语言提及文件时的检索定位

    适用场景：
    - 用户: "这个文件里数据库端口是多少？"
      → list_files(reference="this") → 找到刚上传的文件

    - 用户: "对比这两个配置文件"
      → list_files(reference="these", count=2) → 找到最近2个文件

    - 用户: "我之前上传的日志文件"
      → list_files(reference="previous", file_type="log") → 找到之前的日志

    - 用户: "查看我上传的所有文件"
      → list_files() → 列出当前会话所有上传文件

    关键词：这个、那个、这两个、之前上传的、我上传的、所有文件
    """

    name: str = "file_upload"
    description: str = """管理已上传文件的索引和上下文（不执行文件传输）

    注意：此工具不处理文件上传，文件上传由协议层完成

    功能：
    1. 记录已上传文件的元数据到对话历史
    2. 在历史记录中建立文件索引（便于后续引用）
    3. 支持自然语言提及文件时的检索定位

    适用场景：
    - 用户: "这个文件里数据库端口是多少？"
      → list_files(reference="this") → 找到刚上传的文件

    - 用户: "对比这两个配置文件"
      → list_files(reference="these", count=2) → 找到最近2个文件

    - 用户: "我之前上传的日志文件"
      → list_files(reference="previous", file_type="log") → 找到之前的日志

    - 用户: "查看我上传的所有文件"
      → list_files() → 列出当前会话所有上传文件

    关键词：这个、那个、这两个、之前上传的、我上传的、所有文件
    """
    timeout: int = 5

    # Session对象（由Agent注入）
    session: Optional[object] = None

    def validate_args(
        self,
        action: str = "list",
        reference: str = "all",
        file_type: Optional[str] = None,
        count: Optional[int] = None,
        time_range: Optional[str] = None,
        **kwargs
    ) -> tuple[bool, str]:
        """验证参数

        Args:
            action: 操作类型 (list/get/search)
            reference: 引用代词 ("this"/"these"/"previous"/"all")
            file_type: 文件类型过滤 (如 "log", "yaml")
            count: 数量限制
            time_range: 时间范围 ("recent"/"before"/"today")

        Returns:
            (是否有效, 错误消息)
        """
        # action 验证
        valid_actions = ["list", "get", "search"]
        if action not in valid_actions:
            return False, f"action 必须是以下之一: {', '.join(valid_actions)}"

        # reference 验证
        valid_references = ["this", "these", "previous", "all"]
        if reference not in valid_references:
            return False, f"reference 必须是以下之一: {', '.join(valid_references)}"

        # count 验证
        if count is not None and count < 1:
            return False, "count 必须大于0"

        # time_range 验证
        if time_range is not None:
            valid_time_ranges = ["recent", "before", "today"]
            if time_range not in valid_time_ranges:
                return False, f"time_range 必须是以下之一: {', '.join(valid_time_ranges)}"

        return True, ""

    def _parse_reference(
        self,
        reference: str,
        count: Optional[int] = None
    ) -> int:
        """解析代词引用，返回要获取的文件数量

        Args:
            reference: 引用代词
            count: 数量限制

        Returns:
            文件数量
        """
        if reference == "this":
            return 1
        elif reference == "these":
            return count if count else 2
        elif reference == "previous":
            # 排除最新的一个，返回其余的
            return -1  # 特殊标记：排除第一个
        else:  # "all"
            return 0  # 0 表示返回全部

    def _filter_by_time_range(
        self,
        files: List[dict],
        time_range: str
    ) -> List[dict]:
        """按时间范围过滤文件

        Args:
            files: 文件列表
            time_range: 时间范围

        Returns:
            过滤后的文件列表
        """
        if not files:
            return files

        from datetime import timedelta

        now = datetime.now()

        if time_range == "recent":
            # 最近5分钟
            cutoff = now - timedelta(minutes=5)
            return [f for f in files if f.get("uploaded_at", now) >= cutoff]

        elif time_range == "before":
            # 排除最新的一个
            if len(files) > 1:
                return files[:-1]
            return []

        elif time_range == "today":
            # 今天
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return [f for f in files if f.get("uploaded_at", now) >= today_start]

        return files

    def _filter_by_file_type(
        self,
        files: List[dict],
        file_type: str
    ) -> List[dict]:
        """按文件类型过滤

        Args:
            files: 文件列表
            file_type: 文件类型（如 "log", "yaml"）

        Returns:
            过滤后的文件列表
        """
        if not files or not file_type:
            return files

        # 标准化文件类型（去除点号，转小写）
        file_type = file_type.lower().lstrip('.')

        return [
            f for f in files
            if f.get("filename", "").lower().endswith(f".{file_type}")
        ]

    def execute(
        self,
        action: str = "list",
        reference: str = "all",
        file_type: Optional[str] = None,
        count: Optional[int] = None,
        time_range: Optional[str] = None,
        **kwargs
    ) -> ToolExecutionResult:
        """管理文件索引

        Args:
            action: 操作类型 (list/get/search)
            reference: 引用代词 ("this"/"these"/"previous"/"all")
            file_type: 文件类型过滤
            count: 数量限制
            time_range: 时间范围过滤

        Returns:
            ToolExecutionResult: 执行结果
        """
        start_time = time.time()

        try:
            # 验证参数
            is_valid, error_msg = self.validate_args(
                action=action,
                reference=reference,
                file_type=file_type,
                count=count,
                time_range=time_range
            )
            if not is_valid:
                return ToolExecutionResult(
                    success=False,
                    output="",
                    error=error_msg,
                    duration=time.time() - start_time
                )

            # 获取Session对象
            if not self.session:
                return ToolExecutionResult(
                    success=False,
                    output="",
                    error="Session对象未初始化",
                    duration=time.time() - start_time
                )

            # 获取已上传文件列表
            uploaded_files = getattr(self.session, 'uploaded_files', [])

            if not uploaded_files:
                return ToolExecutionResult(
                    success=True,
                    output="当前会话没有上传的文件",
                    error=None,
                    duration=time.time() - start_time
                )

            # 复制列表避免修改原数据
            files = list(uploaded_files)

            # 按时间顺序排序（最新的在后面）
            files.sort(key=lambda f: f.get("uploaded_at", datetime.now()))

            # 解析引用代词
            requested_count = self._parse_reference(reference, count)

            # 应用引用过滤
            if reference == "this":
                # 返回最新1个
                files = files[-1:] if files else []
            elif reference == "these":
                # 返回最新N个
                limit = requested_count if requested_count > 0 else 2
                files = files[-limit:] if len(files) >= limit else files
            elif reference == "previous":
                # 排除最新的一个
                files = files[:-1] if len(files) > 1 else []
            # "all" 不做过滤

            # 应用时间范围过滤
            if time_range:
                files = self._filter_by_time_range(files, time_range)

            # 应用文件类型过滤
            if file_type:
                files = self._filter_by_file_type(files, file_type)

            if not files:
                return ToolExecutionResult(
                    success=True,
                    output="未找到符合条件的文件",
                    error=None,
                    duration=time.time() - start_time
                )

            # 格式化输出
            output_parts = [
                f"找到 {len(files)} 个文件:\n"
            ]

            for i, file_info in enumerate(files, 1):
                output_parts.append(
                    f"{i}. {file_info.get('filename', '未知文件')}\n"
                    f"   文件ID: {file_info.get('file_id', 'N/A')}\n"
                    f"   大小: {file_info.get('size', 0)} 字节\n"
                    f"   路径: {file_info.get('file_path', 'N/A')}\n"
                    f"   已索引: {'是' if file_info.get('indexed', False) else '否'}\n"
                )

            duration = time.time() - start_time
            logger.info(
                f"[FILE_INDEX] action={action} reference={reference} "
                f"file_type={file_type} results={len(files)} duration={duration:.2f}s"
            )

            return ToolExecutionResult(
                success=True,
                output='\n'.join(output_parts),
                error=None,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[FILE_INDEX] status=failed error={str(e)}")
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"文件索引查询失败: {str(e)}",
                duration=duration
            )
