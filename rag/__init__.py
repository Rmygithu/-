"""
RAG 向量检索层
基于 ChromaDB 本地向量库，为 Agent 提供心理学知识库检索能力

导出：
    retrieve — 根据用户查询检索最相关的心理学知识片段
"""

from .vector_store import retrieve

__all__ = ["retrieve"]
