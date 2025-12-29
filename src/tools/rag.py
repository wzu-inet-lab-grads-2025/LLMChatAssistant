"""
RAG 检索工具模块

提供基于向量索引的语义检索功能，支持路径白名单和自动索引。
遵循章程：真实实现，使用真实智谱 API 计算 Embedding
"""

from dataclasses import dataclass, field
from typing import List, Optional

from ..llm.base import LLMProvider
from ..storage.vector_store import VectorStore, SearchResult
from ..storage.index_manager import IndexManager
from ..utils.path_validator import PathValidator
from .base import Tool, ToolExecutionResult


@dataclass
class RAGTool(Tool):
    """RAG 检索工具"""

    name: str = "rag_search"
    description: str = "基于向量索引的语义检索，支持白名单路径自动索引"
    timeout: int = 5

    llm_provider: LLMProvider = field(default=None)
    vector_store: VectorStore = field(default=None)
    index_manager: Optional[IndexManager] = field(default=None)
    path_validator: Optional[PathValidator] = field(default=None)
    auto_index: bool = True

    def __post_init__(self):
        """初始化后处理"""
        super().__init__()
        # 如果没有提供 index_manager 但有必要的组件，则自动创建
        if self.index_manager is None and self.llm_provider and self.vector_store and self.path_validator:
            from ..utils.config import get_config
            config = get_config()
            self.index_manager = IndexManager(
                vector_store=self.vector_store,
                llm_provider=self.llm_provider,
                path_validator=self.path_validator,
                config=config.file_access
            )

    def validate_args(self, query: str, top_k: int = 3) -> tuple[bool, str]:
        """验证参数

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            (是否有效, 错误消息)
        """
        if not query or not query.strip():
            return False, "查询文本不能为空"

        if top_k < 1 or top_k > 10:
            return False, "top_k 必须在 1-10 之间"

        return True, ""

    async def execute_async(self, query: str, top_k: int = 3, **kwargs) -> ToolExecutionResult:
        """执行检索（异步版本，支持自动索引）

        Args:
            query: 查询文本
            top_k: 返回前 k 个结果
            **kwargs: 其他参数（支持 file_path 参数用于单文件检索）

        Returns:
            ToolExecutionResult: 检索结果
        """
        # 验证参数
        is_valid, error_msg = self.validate_args(query, top_k)
        if not is_valid:
            return ToolExecutionResult(
                success=False,
                output="",
                error=error_msg
            )

        try:
            # 如果指定了文件路径，先确保该文件已索引
            file_path = kwargs.get('file_path')
            if file_path and self.auto_index and self.index_manager:
                success, msg = await self.index_manager.ensure_indexed(file_path)
                if not success:
                    return ToolExecutionResult(
                        success=False,
                        output="",
                        error=f"文件索引失败: {msg}"
                    )

            # 检查是否有向量索引
            indexed_files = self.vector_store.list_files()
            if not indexed_files:
                return ToolExecutionResult(
                    success=True,
                    output="当前没有已索引的文件。请确保白名单目录中有可索引的文件。",
                )

            # 计算查询向量
            query_embedding = await self.llm_provider.embed([query])[0] if isinstance(await self.llm_provider.embed([query]), list) else (await self.llm_provider.embed([query]))[0]

            # 执行检索
            results = self.vector_store.search_all(query_embedding, top_k)

            if not results:
                return ToolExecutionResult(
                    success=True,
                    output=f"在 {len(indexed_files)} 个已索引文件中没有找到相关内容。",
                )

            # 格式化结果
            output_parts = [
                f"在 {len(indexed_files)} 个已索引文件中找到 {len(results)} 个相关结果:\n"
            ]

            for i, result in enumerate(results, 1):
                metadata = result.metadata
                filename = metadata.get('filename', '未知文件')
                position = metadata.get('position', '未知位置')
                filepath = metadata.get('filepath', '')

                output_parts.append(
                    f"{i}. [{filename}] (相似度: {result.similarity:.2f})\n"
                    f"   位置: {position}\n"
                )

                if filepath:
                    output_parts.append(f"   路径: {filepath}\n")

                output_parts.append(
                    f"   内容: {result.chunk[:200]}{'...' if len(result.chunk) > 200 else ''}\n"
                )

            return ToolExecutionResult(
                success=True,
                output='\n'.join(output_parts)
            )

        except Exception as e:
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"检索失败: {str(e)}"
            )

    def execute(self, query: str, top_k: int = 3, **kwargs) -> ToolExecutionResult:
        """执行检索（同步版本，保持向后兼容）

        Args:
            query: 查询文本
            top_k: 返回前 k 个结果
            **kwargs: 其他参数

        Returns:
            ToolExecutionResult: 检索结果
        """
        # 验证参数
        is_valid, error_msg = self.validate_args(query, top_k)
        if not is_valid:
            return ToolExecutionResult(
                success=False,
                output="",
                error=error_msg
            )

        try:
            # 检查是否有向量索引
            indexed_files = self.vector_store.list_files()
            if not indexed_files:
                return ToolExecutionResult(
                    success=True,
                    output="当前没有已索引的文件。请确保白名单目录中有可索引的文件，或使用 execute_async() 支持自动索引。",
                )

            # 计算查询向量（简化版本，不支持自动索引）
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            query_embedding = loop.run_until_complete(
                asyncio.ensure_future(self.llm_provider.embed([query]))
            )[0]

            # 执行检索
            results = self.vector_store.search_all(query_embedding, top_k)

            if not results:
                return ToolExecutionResult(
                    success=True,
                    output=f"在 {len(indexed_files)} 个已索引文件中没有找到相关内容。",
                )

            # 格式化结果
            output_parts = [
                f"在 {len(indexed_files)} 个已索引文件中找到 {len(results)} 个相关结果:\n"
            ]

            for i, result in enumerate(results, 1):
                metadata = result.metadata
                filename = metadata.get('filename', '未知文件')
                position = metadata.get('position', '未知位置')
                filepath = metadata.get('filepath', '')

                output_parts.append(
                    f"{i}. [{filename}] (相似度: {result.similarity:.2f})\n"
                    f"   位置: {position}\n"
                )

                if filepath:
                    output_parts.append(f"   路径: {filepath}\n")

                output_parts.append(
                    f"   内容: {result.chunk[:200]}{'...' if len(result.chunk) > 200 else ''}\n"
                )

            return ToolExecutionResult(
                success=True,
                output='\n'.join(output_parts)
            )

        except Exception as e:
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"检索失败: {str(e)}"
            )

    def get_help(self) -> str:
        """获取帮助信息"""
        indexed_count = len(self.vector_store.list_files())
        return f"""
RAG 语义检索工具

当前状态:
  • 已索引文件数: {indexed_count}

功能说明:
  根据查询文本，在已索引的文件中进行语义检索，
  返回最相关的文本片段。

使用示例:
  - 基础检索: {{'query': '数据库配置是什么？'}}
  - 指定返回数量: {{'query': '错误日志', 'top_k': 5}}

注意事项:
  • 需要先上传文件并建立索引
  • 查询文本应为完整的问题或关键词
  • 相似度阈值: 0.3
  • 最大返回数量: 10
"""
