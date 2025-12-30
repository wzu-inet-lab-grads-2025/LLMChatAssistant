"""
文件下载工具模块

提供文件下载功能，支持多协议传输（RDT/HTTP/NPLT）。
遵循章程：安全第一原则，路径白名单控制
支持架构：混合传输架构（方案A）
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from .base import Tool, ToolExecutionResult


# 配置日志
logger = logging.getLogger('file_operations')


@dataclass
class FileDownloadTool(Tool):
    """文件下载工具

    支持三种传输模式：
    - RDT: UDP可靠传输（CLI客户端，高速）
    - HTTP: Web下载（Web客户端）
    - NPLT: TCP流式传输（兼容模式）
    """

    name: str = "file_download"
    description: str = "将服务器文件发送给用户下载，支持RDT/HTTP/NPLT三种传输模式"
    timeout: int = 20  # 下载超时时间（秒）

    path_validator: Optional[object] = None  # 路径验证器
    rdt_server: Optional[object] = None  # RDT服务器实例
    http_base_url: Optional[str] = None  # HTTP下载基础URL（如 http://localhost:8080）
    client_type: str = "cli"  # 客户端类型：cli | web | desktop

    def validate_args(
        self,
        file_path: str,
        **kwargs
    ) -> tuple[bool, str]:
        """验证参数

        Args:
            file_path: 文件路径

        Returns:
            (是否有效, 错误消息)
        """
        # 1. 路径白名单验证
        if self.path_validator:
            allowed, msg = self.path_validator.is_allowed(file_path)
            if not allowed:
                return False, msg

        # 2. 文件存在性验证
        if not os.path.exists(file_path):
            return False, f"文件不存在: {file_path}"

        # 3. 路径规范化
        normalized = os.path.normpath(file_path)
        if normalized != file_path:
            return False, f"路径已规范化: {normalized}"

        return True, ""

    def execute(
        self,
        file_path: str,
        transport_mode: str = "auto",
        **kwargs
    ) -> ToolExecutionResult:
        """执行文件下载

        Args:
            file_path: 文件路径
            transport_mode: 传输模式
                - "auto": 自动选择（基于client_type）
                - "rdt": 强制使用RDT UDP传输
                - "http": 强制使用HTTP下载
                - "nplt": 强制使用NPLT TCP传输

        Returns:
            ToolExecutionResult: 执行结果
        """
        start_time = time.time()

        try:
            # 验证参数
            is_valid, error_msg = self.validate_args(file_path=file_path)
            if not is_valid:
                logger.warning(f"[DOWNLOAD] path={file_path} status=denied reason={error_msg}")
                return ToolExecutionResult(
                    success=False,
                    output="",
                    error=error_msg,
                    duration=time.time() - start_time
                )

            # 获取文件信息
            filename = os.path.basename(file_path)
            size = os.path.getsize(file_path)

            # 提取file_id（如果路径是storage/uploads/{file_id}/{filename}格式）
            file_id = None
            if "/storage/uploads/" in file_path:
                parts = file_path.split("/storage/uploads/")
                if len(parts) > 1:
                    file_id = parts[1].split("/")[0]

            # 智能选择传输模式
            if transport_mode == "auto":
                transport_mode = self._select_transport_mode()

            # 执行下载
            result = self._execute_download(
                file_path=file_path,
                file_id=file_id,
                filename=filename,
                size=size,
                transport_mode=transport_mode
            )

            duration = time.time() - start_time
            return ToolExecutionResult(
                success=result["success"],
                output=json.dumps(result, ensure_ascii=False),
                error=result.get("error"),
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[DOWNLOAD] path={file_path} status=failed error={str(e)}")
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"文件下载失败: {str(e)}",
                duration=duration
            )

    def _select_transport_mode(self) -> str:
        """智能选择传输模式

        优先级：
        1. CLI/Desktop客户端 → RDT（高速UDP传输）
        2. Web客户端 → HTTP（浏览器原生支持）
        3. 其他 → NPLT（TCP兼容模式）

        Returns:
            传输模式: rdt | http | nplt
        """
        # Web客户端使用HTTP
        if self.client_type == "web":
            if self.http_base_url:
                return "http"
            else:
                logger.warning("[DOWNLOAD] Web客户端但未配置HTTP URL，降级到NPLT")
                return "nplt"

        # CLI和Desktop客户端优先使用RDT
        if self.client_type in ("cli", "desktop"):
            if self.rdt_server:
                return "rdt"
            else:
                logger.warning(f"[DOWNLOAD] {self.client_type.upper()}客户端但RDT服务器未初始化，降级到NPLT")
                return "nplt"

        # 默认使用NPLT
        return "nplt"

    def _execute_download(
        self,
        file_path: str,
        file_id: Optional[str],
        filename: str,
        size: int,
        transport_mode: str
    ) -> dict:
        """执行下载

        Args:
            file_path: 文件路径
            file_id: 文件ID
            filename: 文件名
            size: 文件大小
            transport_mode: 传输模式

        Returns:
            下载结果字典
        """
        try:
            if transport_mode == "rdt":
                return self._download_via_rdt(file_path, file_id, filename, size)
            elif transport_mode == "http":
                return self._download_via_http(file_path, file_id, filename, size)
            elif transport_mode == "nplt":
                return self._download_via_nplt(file_path, file_id, filename, size)
            else:
                return {
                    "success": False,
                    "error": f"不支持的传输模式: {transport_mode}"
                }
        except Exception as e:
            logger.error(f"[DOWNLOAD] transport={transport_mode} error={str(e)}")
            return {
                "success": False,
                "error": f"{transport_mode.upper()}传输失败: {str(e)}"
            }

    def _download_via_rdt(
        self,
        file_path: str,
        file_id: Optional[str],
        filename: str,
        size: int
    ) -> dict:
        """通过RDT协议下载文件

        Args:
            file_path: 文件路径
            file_id: 文件ID
            filename: 文件名
            size: 文件大小

        Returns:
            下载结果
        """
        if not self.rdt_server:
            return {
                "success": False,
                "error": "RDT服务器未初始化"
            }

        logger.info(f"[DOWNLOAD] mode=RDT file={filename} size={size}")

        # 读取文件数据
        with open(file_path, 'rb') as f:
            file_data = f.read()

        # 创建RDT会话（注意：这里需要client_addr，实际应该从Session获取）
        # 这里暂时返回下载令牌，实际传输由Agent协调
        download_token = f"token_{file_id or 'unknown'}"

        logger.info(f"[DOWNLOAD] RDT会话已创建 token={download_token}")

        return {
            "success": True,
            "transport_mode": "rdt",
            "file_id": file_id or "unknown",
            "filename": filename,
            "size": size,
            "download_token": download_token,
            "status": "rdt_ready",
            "message": f"文件已准备通过RDT协议传输: {filename} ({size} 字节)"
        }

    def _download_via_http(
        self,
        file_path: str,
        file_id: Optional[str],
        filename: str,
        size: int
    ) -> dict:
        """通过HTTP下载文件

        Args:
            file_path: 文件路径
            file_id: 文件ID
            filename: 文件名
            size: 文件大小

        Returns:
            下载结果
        """
        if not self.http_base_url:
            return {
                "success": False,
                "error": "HTTP服务未配置"
            }

        logger.info(f"[DOWNLOAD] mode=HTTP file={filename} size={size}")

        # 生成HTTP下载URL
        download_url = f"{self.http_base_url}/api/files/download/{file_id or 'unknown'}"

        logger.info(f"[DOWNLOAD] HTTP URL={download_url}")

        return {
            "success": True,
            "transport_mode": "http",
            "file_id": file_id or "unknown",
            "filename": filename,
            "size": size,
            "download_url": download_url,
            "status": "http_ready",
            "message": f"文件可通过HTTP下载: {filename}\n下载地址: {download_url}"
        }

    def _download_via_nplt(
        self,
        file_path: str,
        file_id: Optional[str],
        filename: str,
        size: int
    ) -> dict:
        """通过NPLT协议下载文件（兼容模式）

        Args:
            file_path: 文件路径
            file_id: 文件ID
            filename: 文件名
            size: 文件大小

        Returns:
            下载结果
        """
        logger.info(f"[DOWNLOAD] mode=NPLT file={filename} size={size}")

        return {
            "success": True,
            "transport_mode": "nplt",
            "file_id": file_id or "unknown",
            "filename": filename,
            "size": size,
            "status": "offered",
            "message": f"已向用户发送下载提议（NPLT协议）: {filename}"
        }
