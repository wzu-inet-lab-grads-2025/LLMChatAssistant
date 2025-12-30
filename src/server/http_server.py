"""
HTTP 文件服务器模块

提供HTTP接口用于Web客户端文件下载。
遵循章程：真实实现，支持多客户端架构（方案A）
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from aiohttp import web
from ..storage.files import UploadedFile


# 配置日志
logger = logging.getLogger('http_server')


class HTTPFileServer:
    """HTTP文件服务器

    为Web客户端提供文件下载接口。
    与NPLT/RDT协议并存，作为Web客户端的下载通道。
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        storage_dir: str = "storage/uploads"
    ):
        """初始化HTTP文件服务器

        Args:
            host: 监听地址
            port: 监听端口
            storage_dir: 文件存储目录
        """
        self.host = host
        self.port = port
        self.storage_dir = Path(storage_dir)
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.running = False

        # 确保存储目录存在
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def start(self):
        """启动HTTP服务器"""
        # 创建应用
        self.app = web.Application()

        # 注册路由
        self.app.router.add_get('/api/files/download/{file_id}', self.handle_download)
        self.app.router.add_get('/api/health', self.handle_health)

        # 创建Runner
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        # 创建站点
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        self.running = True
        logger.info(f"[HTTP] 服务器启动在 http://{self.host}:{self.port}")
        print(f"[INFO] [HTTP] 文件下载服务器启动在 http://{self.host}:{self.port}")

    async def stop(self):
        """停止HTTP服务器"""
        self.running = False

        if self.runner:
            await self.runner.cleanup()
            logger.info("[HTTP] 服务器已停止")
            print("[INFO] [HTTP] 文件下载服务器已停止")

    async def handle_download(self, request: web.Request) -> web.Response:
        """处理文件下载请求

        Args:
            request: HTTP请求

        Returns:
            HTTP响应
        """
        try:
            file_id = request.match_info['file_id']

            logger.info(f"[HTTP] 下载请求: file_id={file_id}")

            # 构建文件路径
            file_path = self.storage_dir / file_id

            # 检查文件目录是否存在
            if not file_path.exists():
                logger.warning(f"[HTTP] 文件不存在: {file_path}")
                return web.json_response(
                    {"error": "文件不存在", "file_id": file_id},
                    status=404
                )

            # 查找文件（file_id目录下可能有多个文件）
            files = list(file_path.glob("*"))
            if not files:
                logger.warning(f"[HTTP] 文件目录为空: {file_path}")
                return web.json_response(
                    {"error": "文件不存在", "file_id": file_id},
                    status=404
                )

            # 取第一个文件
            actual_file = files[0]

            # 检查文件是否为常规文件
            if not actual_file.is_file():
                logger.warning(f"[HTTP] 不是常规文件: {actual_file}")
                return web.json_response(
                    {"error": "无效文件", "file_id": file_id},
                    status=400
                )

            filename = actual_file.name
            file_size = actual_file.stat().st_size

            logger.info(f"[HTTP] 发送文件: {filename} ({file_size} 字节)")

            # 返回文件
            response = web.FileResponse(actual_file)

            # 设置Content-Disposition头（触发浏览器下载）
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

            # 设置CORS头（允许跨域请求）
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET'
            response.headers['Access-Control-Allow-Headers'] = '*'

            return response

        except Exception as e:
            logger.error(f"[HTTP] 下载失败: {str(e)}")
            return web.json_response(
                {"error": f"下载失败: {str(e)}", "file_id": file_id},
                status=500
            )

    async def handle_health(self, request: web.Request) -> web.Response:
        """健康检查接口

        Args:
            request: HTTP请求

        Returns:
            HTTP响应
        """
        return web.json_response({
            "status": "healthy",
            "service": "http_file_server",
            "storage_dir": str(self.storage_dir)
        })

    def get_base_url(self) -> str:
        """获取基础URL

        Returns:
            基础URL（如 http://localhost:8080）
        """
        return f"http://{self.host}:{self.port}"


# 便捷函数
async def create_http_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    storage_dir: str = "storage/uploads"
) -> HTTPFileServer:
    """创建并启动HTTP文件服务器

    Args:
        host: 监听地址
        port: 监听端口
        storage_dir: 文件存储目录

    Returns:
        HTTPFileServer实例
    """
    server = HTTPFileServer(host=host, port=port, storage_dir=storage_dir)
    await server.start()
    return server
