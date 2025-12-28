"""
向量存储模块

提供向量索引管理、语义搜索和持久化功能。
遵循章程：数据持久化到 storage/vectors/ 目录
"""

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

import numpy as np


@dataclass
class SearchResult:
    """检索结果"""
    chunk: str              # 匹配的文本片段
    similarity: float       # 相似度 (0-1)
    metadata: dict          # 元数据（文件名、位置等）


@dataclass
class VectorIndex:
    """向量索引"""
    file_id: str                    # 文件唯一标识
    filename: str                   # 文件名
    chunks: List[str]               # 文本分块
    embeddings: List[List[float]]   # 嵌入向量
    chunk_metadata: List[dict]      # 分块元数据
    created_at: datetime            # 创建时间

    def __post_init__(self):
        """初始化验证"""
        # 确保 embeddings 是 numpy 数组
        if self.embeddings and not isinstance(self.embeddings[0], np.ndarray):
            self.embeddings = [np.array(emb) for emb in self.embeddings]

    def search(self, query_embedding: List[float], top_k: int = 3) -> List[SearchResult]:
        """向量检索

        Args:
            query_embedding: 查询向量
            top_k: 返回前 k 个结果

        Returns:
            检索结果列表
        """
        if not self.embeddings:
            return []

        query_emb = np.array(query_embedding)

        # 计算余弦相似度
        similarities = []
        for emb in self.embeddings:
            emb_array = np.array(emb)
            # 余弦相似度 = (A · B) / (||A|| * ||B||)
            similarity = np.dot(query_emb, emb_array) / (
                np.linalg.norm(query_emb) * np.linalg.norm(emb_array)
            )
            similarities.append(similarity)

        similarities = np.array(similarities)

        # 获取 top_k 索引（按相似度降序）
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        # 过滤低于阈值的结果
        threshold = 0.3
        results = []
        for i in top_indices:
            if similarities[i] >= threshold:
                results.append(SearchResult(
                    chunk=self.chunks[i],
                    similarity=float(similarities[i]),
                    metadata=self.chunk_metadata[i]
                ))

        return results

    def save(self, storage_dir: str = "storage/vectors"):
        """保存向量索引到磁盘

        Args:
            storage_dir: 存储目录
        """
        os.makedirs(storage_dir, exist_ok=True)

        # 保存向量数据
        data = {
            "file_id": self.file_id,
            "filename": self.filename,
            "chunks": self.chunks,
            "embeddings": [emb.tolist() if isinstance(emb, np.ndarray) else emb
                          for emb in self.embeddings],
            "chunk_metadata": self.chunk_metadata,
            "created_at": self.created_at.isoformat()
        }

        filepath = os.path.join(storage_dir, f"{self.file_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, file_id: str, storage_dir: str = "storage/vectors") -> 'VectorIndex':
        """从磁盘加载向量索引

        Args:
            file_id: 文件 ID
            storage_dir: 存储目录

        Returns:
            VectorIndex 实例
        """
        filepath = os.path.join(storage_dir, f"{file_id}.json")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"向量索引不存在：{filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return cls(
            file_id=data["file_id"],
            filename=data["filename"],
            chunks=data["chunks"],
            embeddings=data["embeddings"],
            chunk_metadata=data["chunk_metadata"],
            created_at=datetime.fromisoformat(data["created_at"])
        )


class VectorStore:
    """向量存储管理器"""

    def __init__(self, storage_dir: str = "storage/vectors"):
        """初始化向量存储

        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = storage_dir
        self.indices: dict[str, VectorIndex] = {}
        self._load_all_indices()

    def _load_all_indices(self):
        """加载所有已保存的向量索引"""
        os.makedirs(self.storage_dir, exist_ok=True)

        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                file_id = filename[:-5]  # 移除 .json
                try:
                    index = VectorIndex.load(file_id, self.storage_dir)
                    self.indices[file_id] = index
                except Exception as e:
                    print(f"警告：加载向量索引失败 {filename}: {e}")

        print(f"向量索引加载完成：{len(self.indices)} 个文件")

    def add_index(self, index: VectorIndex):
        """添加向量索引

        Args:
            index: 向量索引
        """
        self.indices[index.file_id] = index
        index.save(self.storage_dir)

    def get_index(self, file_id: str) -> VectorIndex | None:
        """获取向量索引

        Args:
            file_id: 文件 ID

        Returns:
            VectorIndex 实例或 None
        """
        return self.indices.get(file_id)

    def search_all(self, query_embedding: List[float], top_k: int = 3) -> List[SearchResult]:
        """在所有向量索引中搜索

        Args:
            query_embedding: 查询向量
            top_k: 每个索引返回前 k 个结果

        Returns:
            所有检索结果列表（按相似度降序）
        """
        all_results = []

        for index in self.indices.values():
            results = index.search(query_embedding, top_k)
            all_results.extend(results)

        # 按相似度降序排序
        all_results.sort(key=lambda r: r.similarity, reverse=True)

        return all_results[:top_k]

    def delete_index(self, file_id: str):
        """删除向量索引

        Args:
            file_id: 文件 ID
        """
        if file_id in self.indices:
            del self.indices[file_id]

        filepath = os.path.join(self.storage_dir, f"{file_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)

    def list_files(self) -> List[str]:
        """列出所有已索引的文件

        Returns:
            文件 ID 列表
        """
        return list(self.indices.keys())
