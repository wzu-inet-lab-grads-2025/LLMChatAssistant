"""
文件语义检索工具模块

提供基于向量索引的语义检索功能，支持自然语言查询。
遵循章程：真实实现，使用真实智谱API计算Embedding
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

from .base import Tool, ToolExecutionResult
from ..llm.base import LLMProvider
from ..storage.vector_store import VectorStore
from ..storage.index_manager import IndexManager


# 配置日志
logger = logging.getLogger('file_operations')


@dataclass
class FileSemanticSearchTool(Tool):
    """文件语义检索工具"""

    name: str = "file_semantic_search"
    description: str = "通过自然语言描述语义检索文件"
    timeout: int = 5  # 检索超时时间（秒）

    llm_provider: Optional[LLMProvider] = None
    vector_store: Optional[VectorStore] = None
    index_manager: Optional[IndexManager] = None

    def validate_args(
        self,
        query: str,
        top_k: int = 3,
        **kwargs
    ) -> tuple[bool, str]:
        """验证参数

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            (是否有效, 错误消息)
        """
        # 1. 查询非空
        if not query or not query.strip():
            return False, "查询文本不能为空"

        # 2. top_k 范围验证
        if top_k < 1 or top_k > 10:
            return False, "top_k 必须在 1-10 之间"

        return True, ""

    def execute(
        self,
        query: str,
        top_k: int = 3,
        **kwargs
    ) -> ToolExecutionResult:
        """执行语义检索

        Args:
            query: 查询文本
            top_k: 返回前 k 个结果

        Returns:
            ToolExecutionResult: 检索结果
        """
        start_time = time.time()

        try:
            # 验证参数
            is_valid, error_msg = self.validate_args(query=query, top_k=top_k)
            if not is_valid:
                return ToolExecutionResult(
                    success=False,
                    output="",
                    error=error_msg,
                    duration=time.time() - start_time
                )

            # 检查是否有向量索引
            if not self.vector_store:
                return ToolExecutionResult(
                    success=True,
                    output="向量存储未初始化",
                    error=None,
                    duration=time.time() - start_time
                )

            indexed_files = self.vector_store.list_files()
            if not indexed_files:
                return ToolExecutionResult(
                    success=True,
                    output="当前没有已索引的文件。请确保白名单目录中有可索引的文件。",
                    error=None,
                    duration=time.time() - start_time
                )

            # 计算查询向量
            if not self.llm_provider:
                return ToolExecutionResult(
                    success=False,
                    output="",
                    error="LLM提供者未初始化",
                    duration=time.time() - start_time
                )

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
                duration = time.time() - start_time
                logger.info(f"[SEARCH] query=\"{query}\" results=0 duration={duration:.2f}s")
                return ToolExecutionResult(
                    success=True,
                    output=f"在 {len(indexed_files)} 个已索引文件中没有找到相关内容。",
                    error=None,
                    duration=duration
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

            duration = time.time() - start_time
            logger.info(
                f"[SEARCH] query=\"{query}\" results={len(results)} "
                f"duration={duration:.2f}s"
            )

            return ToolExecutionResult(
                success=True,
                output='\n'.join(output_parts),
                error=None,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[SEARCH] query=\"{query}\" status=failed error={str(e)}")
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"语义检索失败: {str(e)}",
                duration=duration
            )
