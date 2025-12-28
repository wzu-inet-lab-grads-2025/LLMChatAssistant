"""
RAG 检索工具模块

提供基于向量索引的语义检索功能。
遵循章程：真实实现，使用真实智谱 API 计算 Embedding
"""

from dataclasses import dataclass
from typing import List

from ..llm.base import LLMProvider
from ..storage.vector_store import VectorStore, SearchResult
from .base import Tool, ToolExecutionResult


@dataclass
class RAGTool(Tool):
    """RAG 检索工具"""

    name: str = "rag_search"
    description: str = "基于向量索引的语义检索"
    timeout: int = 5

    def __init__(self, llm_provider: LLMProvider, vector_store: VectorStore):
        """初始化 RAG 工具

        Args:
            llm_provider: LLM Provider（用于计算 Embedding）
            vector_store: 向量存储
        """
        super().__init__()
        self.llm_provider = llm_provider
        self.vector_store = vector_store

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

    def execute(self, query: str, top_k: int = 3, **kwargs) -> ToolExecutionResult:
        """执行检索

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
                    output="当前没有已索引的文件。请先上传文件。",
                )

            # 计算查询向量
            query_embedding = self.llm_provider.embed(query)

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

                output_parts.append(
                    f"{i}. [{filename}] (相似度: {result.similarity:.2f})\n"
                    f"   位置: {position}\n"
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
