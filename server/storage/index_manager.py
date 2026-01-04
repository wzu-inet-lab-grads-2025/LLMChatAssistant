"""
自动索引管理模块

提供文件自动索引功能，支持按需索引和懒加载。
"""

import asyncio
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from shared.utils.path_validator import PathValidator


class IndexManager:
    """自动索引管理器"""

    def __init__(self, vector_store, llm_provider, path_validator: PathValidator, config):
        """初始化索引管理器

        Args:
            vector_store: 向量存储实例
            llm_provider: LLM Provider
            path_validator: 路径验证器
            config: 文件访问配置
        """
        self.vector_store = vector_store
        self.llm_provider = llm_provider
        self.path_validator = path_validator
        self.config = config
        self._index_lock = asyncio.Lock()

    async def ensure_indexed(self, file_path: str) -> tuple[bool, str]:
        """确保文件已索引，如果未索引则自动创建索引

        Args:
            file_path: 文件路径

        Returns:
            (是否成功, 消息)
        """
        # 1. 验证路径
        allowed, msg = self.path_validator.is_allowed(file_path)
        if not allowed:
            return False, f"文件访问被拒绝: {msg}"

        # 2. 生成文件唯一标识（基于路径的 hash）
        file_id = self._generate_file_id(file_path)

        # 3. 检查是否已索引
        if file_id in self.vector_store.list_files():
            return True, f"文件已索引: {file_path}"

        # 4. 创建索引
        async with self._index_lock:
            # 双重检查（防止并发重复索引）
            if file_id in self.vector_store.list_files():
                return True, f"文件已索引: {file_path}"

            try:
                return await self._create_index(file_path, file_id)
            except Exception as e:
                return False, f"索引创建失败: {str(e)}"

    def _generate_file_id(self, file_path: str) -> str:
        """基于文件路径生成唯一标识

        Args:
            file_path: 文件路径

        Returns:
            文件 ID (hash 值)
        """
        # 使用路径的 SHA256 哈希作为 ID
        normalized_path = str(Path(file_path).resolve())
        return hashlib.sha256(normalized_path.encode()).hexdigest()[:32]

    async def _create_index(self, file_path: str, file_id: str) -> tuple[bool, str]:
        """为文件创建向量索引

        Args:
            file_path: 文件路径
            file_id: 文件 ID

        Returns:
            (是否成功, 消息)
        """
        from .vector_store import VectorIndex

        # 1. 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return False, f"读取文件失败: {str(e)}"

        # 2. 验证内容类型
        if not self.path_validator.validate_content_type(file_path):
            return False, f"不支持的文件类型（仅支持文本文件）: {file_path}"

        # 3. 文本分块
        chunks = self.vector_store.chunk_text(
            content,
            chunk_size=self.config.chunk_size,
            overlap=self.config.chunk_overlap
        )

        if not chunks:
            return False, f"文件内容为空或分块失败: {file_path}"

        # 4. 计算嵌入向量
        try:
            embeddings = await self.llm_provider.embed(chunks)
        except Exception as e:
            return False, f"嵌入向量计算失败: {str(e)}"

        # 5. 创建向量索引
        index = VectorIndex(
            file_id=file_id,
            filename=str(Path(file_path).name),
            chunks=chunks,
            embeddings=embeddings,
            chunk_metadata=[
                {
                    "filename": str(Path(file_path).name),
                    "filepath": file_path,
                    "position": i,
                    "timestamp": datetime.now().isoformat()
                }
                for i in range(len(chunks))
            ],
            created_at=datetime.now()
        )

        # 6. 保存索引
        self.vector_store.add_index(index)

        return True, f"索引创建成功: {file_path} ({len(chunks)} 个分块)"

    async def batch_index(self, directory: str, pattern: str = "*") -> dict[str, tuple[bool, str]]:
        """批量索引目录中的文件

        Args:
            directory: 目录路径
            pattern: 文件匹配模式

        Returns:
            {文件路径: (是否成功, 消息)}
        """
        import glob

        results = {}
        glob_pattern = str(Path(directory) / pattern)
        files = glob.glob(glob_pattern, recursive=True)

        for file_path in files:
            if Path(file_path).is_file():
                success, msg = await self.ensure_indexed(file_path)
                results[file_path] = (success, msg)

        return results

    def index_file(self, file_path: str, file_id: Optional[str] = None) -> dict:
        """同步索引文件（用于非异步上下文）

        注意：此方法会阻塞直到索引完成。如果在异步上下文中，请使用 ensure_indexed()。

        Args:
            file_path: 文件路径
            file_id: 文件 ID（可选，如果不提供则自动生成）

        Returns:
            {"success": bool, "message": str, "file_id": str}
        """
        try:
            # 1. 验证路径
            allowed, msg = self.path_validator.is_allowed(file_path)
            if not allowed:
                return {"success": False, "error": f"文件访问被拒绝: {msg}", "file_id": file_id or ""}

            # 2. 生成或使用提供的 file_id
            if file_id is None:
                file_id = self._generate_file_id(file_path)

            # 3. 检查是否已索引
            if file_id in self.vector_store.list_files():
                return {"success": True, "message": "文件已索引", "file_id": file_id}

            # 4. 同步运行异步索引函数
            import asyncio
            try:
                # 尝试获取当前事件循环
                loop = asyncio.get_running_loop()
                # 如果已经在运行的事件循环中，无法使用 run_until_complete
                # 这种情况应该使用 ensure_indexed() 而不是此方法
                return {
                    "success": False,
                    "error": "不能在异步上下文中调用 index_file()，请使用 await ensure_indexed()",
                    "file_id": file_id
                }
            except RuntimeError:
                # 没有运行的事件循环，创建新的并运行
                pass

            # 创建新的事件循环并运行异步函数
            success, msg = asyncio.run(self._create_index(file_path, file_id))
            return {"success": success, "message": msg, "file_id": file_id}

        except Exception as e:
            return {"success": False, "error": f"索引创建失败: {str(e)}", "file_id": file_id or ""}

    def get_index_status(self, file_path: str) -> dict:
        """获取文件的索引状态

        Args:
            file_path: 文件路径

        Returns:
            状态信息字典
        """
        file_id = self._generate_file_id(file_path)
        indexed = file_id in self.vector_store.list_files()

        status = {
            "file_path": file_path,
            "file_id": file_id,
            "indexed": indexed,
            "allowed": False
        }

        # 检查是否在白名单中
        allowed, _ = self.path_validator.is_allowed(file_path)
        status["allowed"] = allowed

        if indexed:
            index = self.vector_store.get_index(file_id)
            if index:
                status.update({
                    "chunks_count": len(index.chunks),
                    "created_at": index.created_at.isoformat()
                })

        return status

    def list_allowed_files(self, directory: str = None) -> list[str]:
        """列出允许访问的文件

        Args:
            directory: 目录路径（None 表示所有白名单路径）

        Returns:
            文件路径列表
        """
        import glob

        files = []
        paths_to_check = [directory] if directory else self.path_validator.allowed_paths

        for path_pattern in paths_to_check:
            # 处理 glob 模式
            if '*' in path_pattern or '?' in path_pattern:
                matches = glob.glob(path_pattern, recursive=True)
                files.extend([f for f in matches if Path(f).is_file()])
            else:
                # 处理普通目录
                path_obj = Path(path_pattern)
                if path_obj.is_dir():
                    files.extend([str(f) for f in path_obj.rglob('*') if f.is_file()])
                elif path_obj.is_file():
                    files.append(str(path_obj))

        return files

    def clear_index(self, file_path: str) -> bool:
        """清除文件的索引

        Args:
            file_path: 文件路径

        Returns:
            是否成功
        """
        file_id = self._generate_file_id(file_path)
        if file_id in self.vector_store.list_files():
            self.vector_store.delete_index(file_id)
            return True
        return False
