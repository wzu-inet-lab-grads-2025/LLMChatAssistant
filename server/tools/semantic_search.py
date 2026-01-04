"""
语义检索工具模块（统一的文件搜索）

提供基于混合检索策略的语义检索功能（精确匹配→模糊匹配→语义检索）。
遵循章程 v1.5.1：工具职责单一原则、混合检索策略原则（强制性）。

合并自：RAGTool + FileSemanticSearchTool
消除代码重复：90% → 0%
"""

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import List, Optional

from .base import Tool, ToolExecutionResult
from server.llm.base import LLMProvider
from server.storage.vector_store import VectorStore
from server.storage.index_manager import IndexManager
from shared.utils.path_validator import PathValidator


# 配置日志
logger = logging.getLogger('file_operations')


@dataclass
class SemanticSearchTool(Tool):
    """统一的语义检索工具（混合检索策略）

    遵循章程 v1.5.1 - 混合检索策略原则（强制性）：
    1. 精确匹配（1st priority）：如"config.yaml" → similarity=1.0
    2. 模糊匹配（2nd priority）：如"config" → config.yaml, config.json, config.yml
    3. 语义检索（3rd priority）：如"数据库配置在哪里" → 向量检索
    """

    name: str = "semantic_search"
    description: str = """通过自然语言描述检索文件（基于向量索引和混合检索策略）

    功能：
    1. 搜索系统文档（README、API文档、配置说明）
    2. 检索用户上传的文件（storage/uploads/）
    3. 定位文件路径后，配合 command_executor 使用 cat/grep 查看内容

    适用场景：
    - 用户想"找"、"搜索"、"定位"某个文件 → 使用此工具定位文件路径
    - "搜索配置说明" → 定位README.md → 使用command_executor查看内容
    - "找一下日志文件" → 定位app.log → 使用command_executor的cat/tail查看
    - "config.yaml在哪里" → 定位config.yaml → 使用command_executor的cat查看

    注意：
    - 此工具用于定位文件，不是直接读取文件内容
    - 定位到文件后，使用 command_executor 的 cat/head/tail/grep 查看内容
    - 如果用户知道具体文件名，直接用 command_executor 更快

    参数：
    - query: 自然语言查询（必需）
    - top_k: 返回结果数量（可选，默认3，范围1-10）
    - scope: 检索范围（可选，默认"all"）
      - "all": 全部文件（系统文档 + 用户上传）
      - "system": 仅系统文档
      - "uploads": 仅用户上传文件
    """
    timeout: int = 5

    llm_provider: Optional[LLMProvider] = None
    vector_store: Optional[VectorStore] = None
    index_manager: Optional[IndexManager] = None
    path_validator: Optional[PathValidator] = None
    auto_index: bool = True

    def validate_args(
        self,
        query: str,
        top_k: int = 3,
        scope: str = "all",
        **kwargs
    ) -> tuple[bool, str]:
        """验证参数

        Args:
            query: 查询文本
            top_k: 返回结果数量
            scope: 检索范围 (all/system/uploads)

        Returns:
            (是否有效, 错误消息)
        """
        # 1. 查询非空
        if not query or not query.strip():
            return False, "查询文本不能为空"

        # 2. top_k 范围验证（允许 1-100 以支持更多结果）
        if top_k < 1 or top_k > 100:
            return False, "top_k 必须在 1-100 之间"

        # 3. scope 参数验证
        valid_scopes = ["all", "system", "uploads"]
        if scope not in valid_scopes:
            return False, f"scope 必须是以下之一: {', '.join(valid_scopes)}"

        return True, ""

    def _is_exact_filename(self, query: str) -> bool:
        """判断查询是否为精确文件名

        精确文件名特征：
        - 包含文件扩展名（如 .yaml, .py, .log）
        - 不包含空格或特殊词（如"在"、"哪里"、"的"）

        Args:
            query: 查询文本

        Returns:
            是否为精确文件名
        """
        # 常见文件扩展名
        extensions = {
            '.txt', '.log', '.md', '.py', '.js', '.json', '.yaml', '.yml',
            '.xml', '.html', '.css', '.sh', '.conf', '.cfg', '.ini', '.toml',
            '.pdf', '.png', '.jpg', '.jpeg'
        }

        # 提取文件名（去除路径）
        filename = os.path.basename(query.strip())

        # 检查是否有文件扩展名
        has_extension = any(filename.endswith(ext) for ext in extensions)

        # 检查是否包含自然语言词汇
        natural_lang_keywords = ['在', '哪里', '的', '是什么', '如何', '怎么', '为什么']
        has_natural_lang = any(keyword in query for keyword in natural_lang_keywords)

        # 检查是否包含空格（自然语言查询通常有空格）
        has_spaces = ' ' in query.strip()

        return has_extension and not has_natural_lang and not has_spaces

    def _search_exact_filename(
        self,
        query: str,
        scope: str,
        top_k: int
    ) -> List[dict]:
        """精确文件名匹配

        Args:
            query: 查询文本（文件名）
            scope: 检索范围
            top_k: 返回结果数量

        Returns:
            匹配结果列表 [{filepath, filename, similarity=1.0, match_type, chunk}]
        """
        results = []
        target_filename = os.path.basename(query.strip())

        # 获取已索引文件
        indexed_files = self.vector_store.list_files()

        for file_id in indexed_files:
            index = self.vector_store.get_index(file_id)
            if not index:
                continue

            # scope 过滤
            filepath = index.chunk_metadata[0].get('filepath', '') if index.chunk_metadata else ''
            if scope == "uploads" and not filepath.startswith("storage/uploads"):
                continue
            if scope == "system" and filepath.startswith("storage/uploads"):
                continue

            # 精确匹配文件名
            if index.filename == target_filename or os.path.basename(filepath) == target_filename:
                results.append({
                    'filepath': filepath,
                    'filename': index.filename,
                    'similarity': 1.0,  # 精确匹配，相似度=1.0
                    'match_type': 'exact_filename',
                    'chunk': index.chunks[0] if index.chunk_metadata else '',
                    'metadata': index.chunk_metadata[0] if index.chunks else {}
                })

                if len(results) >= top_k:
                    break

        return results

    def _search_fuzzy_filename(
        self,
        query: str,
        scope: str,
        top_k: int
    ) -> List[dict]:
        """模糊文件名匹配（关键词、前缀、通配符）

        Args:
            query: 查询文本
            scope: 检索范围
            top_k: 返回结果数量

        Returns:
            匹配结果列表
        """
        results = []
        query_lower = query.strip().lower()
        indexed_files = self.vector_store.list_files()

        for file_id in indexed_files:
            index = self.vector_store.get_index(file_id)
            if not index:
                continue

            # scope 过滤
            filepath = index.chunk_metadata[0].get('filepath', '') if index.chunk_metadata else ''
            if scope == "uploads" and not filepath.startswith("storage/uploads"):
                continue
            if scope == "system" and filepath.startswith("storage/uploads"):
                continue

            filename = index.filename.lower()
            basename = os.path.basename(filepath).lower()

            # 模糊匹配策略
            match = False
            similarity = 0.0

            # 1. 前缀匹配（如 "config" → "config.yaml"）
            if filename.startswith(query_lower) or basename.startswith(query_lower):
                match = True
                similarity = 0.9

            # 2. 包含匹配（如 "config" → "my.config.yaml"）
            elif query_lower in filename or query_lower in basename:
                match = True
                similarity = 0.8

            # 3. 通配符匹配（如 "*.log"）
            elif '*' in query or '?' in query:
                import fnmatch
                if fnmatch.fnmatch(filename, query_lower) or fnmatch.fnmatch(basename, query_lower):
                    match = True
                    similarity = 0.85

            if match:
                results.append({
                    'filepath': filepath,
                    'filename': index.filename,
                    'similarity': similarity,
                    'match_type': 'fuzzy_filename',
                    'chunk': index.chunks[0] if index.chunk_metadata else '',
                    'metadata': index.chunk_metadata[0] if index.chunks else {}
                })

        # 按相似度排序
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

    async def _search_semantic(
        self,
        query: str,
        scope: str,
        top_k: int
    ) -> List[dict]:
        """向量语义检索（兜底策略）

        Args:
            query: 查询文本
            scope: 检索范围
            top_k: 返回结果数量

        Returns:
            匹配结果列表
        """
        # 计算查询向量
        query_embedding = await self.llm_provider.embed([query])
        if isinstance(query_embedding, list):
            query_embedding = query_embedding[0]

        # 执行向量检索
        vector_results = self.vector_store.search_all(query_embedding, top_k * 2)  # 多检索一些，后续过滤

        # scope 过滤
        results = []
        for result in vector_results:
            filepath = result.metadata.get('filepath', '')

            if scope == "uploads" and not filepath.startswith("storage/uploads"):
                continue
            if scope == "system" and filepath.startswith("storage/uploads"):
                continue

            results.append({
                'filepath': filepath,
                'filename': result.metadata.get('filename', ''),
                'similarity': result.similarity,
                'match_type': 'semantic',
                'chunk': result.chunk,
                'metadata': result.metadata
            })

            if len(results) >= top_k:
                break

        return results

    def _merge_and_deduplicate(
        self,
        exact_results: List[dict],
        fuzzy_results: List[dict],
        semantic_results: List[dict],
        top_k: int
    ) -> List[dict]:
        """合并多层检索结果并去重

        Args:
            exact_results: 精确匹配结果
            fuzzy_results: 模糊匹配结果
            semantic_results: 语义检索结果
            top_k: 返回结果数量

        Returns:
            合并去重后的结果
        """
        # 按优先级合并：精确 > 模糊 > 语义
        all_results = []

        # 1. 添加精确匹配结果（最高优先级）
        seen_paths = set()
        for result in exact_results:
            filepath = result['filepath']
            if filepath and filepath not in seen_paths:
                all_results.append(result)
                seen_paths.add(filepath)

        # 2. 添加模糊匹配结果（次优先级）
        for result in fuzzy_results:
            filepath = result['filepath']
            if filepath and filepath not in seen_paths:
                all_results.append(result)
                seen_paths.add(filepath)

        # 3. 添加语义检索结果（兜底）
        for result in semantic_results:
            filepath = result['filepath']
            if filepath and filepath not in seen_paths:
                all_results.append(result)
                seen_paths.add(filepath)

        # 按相似度排序并限制数量
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        return all_results[:top_k]

    def execute(
        self,
        query: str,
        top_k: int = 3,
        scope: str = "all",
        **kwargs
    ) -> ToolExecutionResult:
        """执行语义检索（混合检索策略）

        Args:
            query: 查询文本
            top_k: 返回前 k 个结果
            scope: 检索范围 (all/system/uploads)

        Returns:
            ToolExecutionResult: 检索结果
        """
        start_time = time.time()

        try:
            # 验证参数
            is_valid, error_msg = self.validate_args(query=query, top_k=top_k, scope=scope)
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

            # 检查 LLM 提供者
            if not self.llm_provider:
                return ToolExecutionResult(
                    success=False,
                    output="",
                    error="LLM提供者未初始化",
                    duration=time.time() - start_time
                )

            # ===== 混合检索策略（constitution v1.5.1 强制性要求） =====

            # 第1层：精确文件名匹配（优先级最高）
            exact_results = []
            if self._is_exact_filename(query):
                exact_results = self._search_exact_filename(query, scope, top_k)
                logger.info(f"[SEARCH] query=\"{query}\" exact_match={len(exact_results)}")

            # 第2层：模糊文件名匹配（如果精确匹配未满）
            fuzzy_results = []
            if len(exact_results) < top_k:
                fuzzy_results = self._search_fuzzy_filename(query, scope, top_k - len(exact_results))
                logger.info(f"[SEARCH] query=\"{query}\" fuzzy_match={len(fuzzy_results)}")

            # 第3层：向量语义检索（兜底策略，如果前两层未满）
            semantic_results = []
            if len(exact_results) + len(fuzzy_results) < top_k:
                # 需要异步执行语义检索
                try:
                    # 尝试在当前事件循环中运行
                    loop = asyncio.get_running_loop()
                    # 如果已经在运行中，使用asyncio.run_coroutine_threadsafe或直接在当前循环中调度
                    # 但execute()是同步方法，无法使用await
                    # 所以需要在新线程中运行协程
                    import concurrent.futures
                    import threading

                    result = [None]
                    exception = [None]

                    def run_in_new_loop():
                        try:
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            result[0] = new_loop.run_until_complete(
                                self._search_semantic(query, scope, top_k - len(exact_results) - len(fuzzy_results))
                            )
                            new_loop.close()
                        except Exception as e:
                            exception[0] = e

                    thread = threading.Thread(target=run_in_new_loop)
                    thread.start()
                    thread.join(timeout=10)  # 最多等待10秒

                    if exception[0]:
                        raise exception[0]
                    semantic_results = result[0] if result[0] is not None else []

                except RuntimeError:
                    # 没有运行中的事件循环，使用asyncio.run()
                    semantic_results = asyncio.run(
                        self._search_semantic(query, scope, top_k - len(exact_results) - len(fuzzy_results))
                    )
                logger.info(f"[SEARCH] query=\"{query}\" semantic_match={len(semantic_results)}")

            # 合并并去重结果
            final_results = self._merge_and_deduplicate(exact_results, fuzzy_results, semantic_results, top_k)

            if not final_results:
                duration = time.time() - start_time
                logger.info(f"[SEARCH] query=\"{query}\" scope={scope} results=0 duration={duration:.2f}s")
                return ToolExecutionResult(
                    success=True,
                    output=f"在 {len(indexed_files)} 个已索引文件中没有找到相关内容。",
                    error=None,
                    duration=duration
                )

            # 格式化结果
            output_parts = [
                f"在 {len(indexed_files)} 个已索引文件中找到 {len(final_results)} 个相关结果:\n"
            ]

            for i, result in enumerate(final_results, 1):
                match_type = result['match_type']
                match_type_zh = {
                    'exact_filename': '精确文件名',
                    'fuzzy_filename': '模糊文件名',
                    'semantic': '语义检索'
                }.get(match_type, match_type)

                output_parts.append(
                    f"{i}. [{result['filename']}] "
                    f"(相似度: {result['similarity']:.2f}, 匹配方式: {match_type_zh})\n"
                )

                if result.get('filepath'):
                    output_parts.append(f"   路径: {result['filepath']}\n")

                chunk_preview = result['chunk'][:200] if result.get('chunk') else ''
                if chunk_preview:
                    output_parts.append(f"   内容: {chunk_preview}{'...' if len(result['chunk']) > 200 else ''}\n")

            duration = time.time() - start_time
            logger.info(
                f"[SEARCH] query=\"{query}\" scope={scope} results={len(final_results)} "
                f"exact={len(exact_results)} fuzzy={len(fuzzy_results)} semantic={len(semantic_results)} "
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
