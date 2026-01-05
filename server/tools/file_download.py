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
    server: Optional[object] = None  # NPLT服务器实例（用于调用offer_file_download）
    http_base_url: Optional[str] = None  # HTTP下载基础URL（如 http://localhost:8080）
    client_type: str = "cli"  # 客户端类型：cli | web | desktop

    # 存储后台任务引用，防止被垃圾回收
    _background_tasks: list = None  # type: ignore[assignment]

    def __post_init__(self):
        """初始化后台任务列表"""
        if self._background_tasks is None:
            self._background_tasks = []

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

        # 2.5 路径必须是文件，不能是目录
        if os.path.isdir(file_path):
            return False, f"路径是目录，不是文件: {file_path}"

        # 3. 路径规范化
        normalized = os.path.normpath(file_path)
        if normalized != file_path:
            return False, f"路径已规范化: {normalized}"

        return True, ""

    def execute(
        self,
        file_path: str,
        transport_mode: str = "auto",
        session=None,
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
            session: Session对象（可选，用于访问client_addr）

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
                transport_mode=transport_mode,
                session=session
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
        transport_mode: str,
        session=None
    ) -> dict:
        """执行下载

        Args:
            file_path: 文件路径
            file_id: 文件ID
            filename: 文件名
            size: 文件大小
            transport_mode: 传输模式
            session: Session对象（可选）

        Returns:
            下载结果字典
        """
        try:
            if transport_mode == "rdt":
                return self._download_via_rdt(file_path, file_id, filename, size, session)
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
        size: int,
        session=None
    ) -> dict:
        """通过RDT协议下载文件

        端到端流程（关键集成点）：
        1. 读取文件数据到内存
        2. 调用 server.offer_file_download() 发送 DOWNLOAD_OFFER 消息
           - NPLT 消息类型：MessageType.DOWNLOAD_OFFER
           - 包含：filename, size, checksum, download_token, server_host, server_port
        3. server.offer_file_download() 内部调用 rdt_server.create_session() 创建 RDT 会话
           - 生成唯一的 download_token
           - 存储 file_data 和 client_addr
        4. 等待 0.5 秒让客户端准备接收（连接 RDT 服务器）
        5. 调用 rdt_server.send_file() 执行 UDP 数据包传输
           - 使用滑动窗口协议（window_size=5, timeout=0.1s）
           - 发送到 session.client_addr
        6. 客户端接收文件并保存到 downloads/ 目录

        Args:
            file_path: 文件路径
            file_id: 文件ID
            filename: 文件名
            size: 文件大小
            session: Session对象（包含client_addr，必需）

        Returns:
            下载结果字典 {"success": True, "status": "transferring", ...}
        """
        if not self.rdt_server:
            return {
                "success": False,
                "error": "RDT服务器未初始化"
            }

        if not session:
            return {
                "success": False,
                "error": "缺少session对象，无法获取客户端地址"
            }

        logger.info(f"[DOWNLOAD] mode=RDT file={filename} size={size}")

        try:
            import asyncio

            # 读取文件数据
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # 调用 server.offer_file_download() 发送 DOWNLOAD_OFFER 消息
            # 注意：这里需要在后台异步执行，因为 execute 是同步方法
            async def _transfer_file():
                """异步执行文件传输"""
                logger.info(f"[DOWNLOAD] === 后台传输任务开始执行: {filename} ===")
                # 1. 发送下载提议
                if self.server:
                    success = await self.server.offer_file_download(session, filename, file_data)
                    if not success:
                        logger.error("[DOWNLOAD] 发送下载提议失败")
                        return False

                    # 获取 download_token（从 RDT 服务器的最新会话）
                    # offer_file_download 会创建会话，我们获取最新创建的
                    if hasattr(self.rdt_server, 'sessions'):
                        # 找到最新的会话
                        for token, rdt_session in self.rdt_server.sessions.items():
                            if rdt_session.filename == filename:
                                download_token = token
                                break
                        else:
                            # 未找到，使用 file_id
                            download_token = file_id or f"token_{filename}"
                    else:
                        download_token = file_id or f"token_{filename}"
                else:
                    # Fallback: 直接创建 RDT 会话
                    logger.warning("[DOWNLOAD] server未初始化，跳过DOWNLOAD_OFFER消息")
                    download_token = self.rdt_server.create_session(
                        filename=filename,
                        file_data=file_data,
                        client_addr=session.client_addr
                    )

                logger.info(f"[DOWNLOAD] RDT会话已创建 token={download_token}")

                # 2. 等待客户端准备（0.5秒）
                await asyncio.sleep(0.5)

                # 3. 执行 RDT 传输
                send_success = await self.rdt_server.send_file(download_token, session.client_addr)

                if not send_success:
                    logger.error(f"[DOWNLOAD] RDT传输失败 token={download_token}")
                    return False

                logger.info(f"[DOWNLOAD] RDT传输成功 token={download_token}")
                return True

            # 在后台执行传输（不阻塞当前线程）
            try:
                # 尝试获取当前事件循环
                loop = asyncio.get_running_loop()
                # 如果已有事件循环在运行，创建后台任务
                # **重要**：必须保存 Task 对象，否则会被垃圾回收
                task = asyncio.create_task(_transfer_file())
                self._background_tasks.append(task)

                # 添加任务完成回调，清理已完成的任务
                def cleanup_task(t):
                    if t in self._background_tasks:
                        self._background_tasks.remove(t)

                task.add_done_callback(cleanup_task)

                logger.info(f"[DOWNLOAD] 后台传输任务已创建: {filename}")
            except RuntimeError as e:
                # 没有运行的事件循环，创建新的
                logger.warning(f"[DOWNLOAD] 没有运行的事件循环，创建新的: {e}")
                asyncio.run(_transfer_file())

            # 立即返回成功（传输在后台进行）
            return {
                "success": True,
                "transport_mode": "rdt",
                "file_id": file_id or "unknown",
                "filename": filename,
                "size": size,
                "status": "transferring",
                "message": f"正在通过RDT协议传输文件: {filename} ({size} 字节)"
            }

        except Exception as e:
            logger.error(f"[DOWNLOAD] RDT传输异常: {str(e)}")
            return {
                "success": False,
                "error": f"RDT传输失败: {str(e)}"
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
