"""
数据持久化层
提供基于 SQLite 的轻量数据库支持，解决页面关闭数据丢失问题。

导出：
    SQLiteStore — 单例数据库存取类
    get_db       — 获取全局单例
"""

from .sqlite_store import SQLiteStore, get_db

__all__ = ["SQLiteStore", "get_db"]
