"""
SQLite 轻量持久化层
解决 Streamlit 页面关闭后数据全部丢失的问题。

设计原则：
1. 单例模式 —— 整个进程共享同一个连接池，避免重复打开文件
2. 异常静默降级 —— 任何 DB 异常都不能崩溃 UI，只记日志
3. 零额外依赖 —— sqlite3 是 Python 标准库，无需 requirements.txt 变动
4. 会话隔离 —— 每次"一键生成"产生一条独立 session 记录，支持历史追溯

数据库表：
    user_sessions       — 会话元数据（初始 prompt、时间戳、是否归档）
    chat_messages       — 每个 Agent 的对话消息（支持多轮）
    emotion_eval_results— 情绪评估结果（JSON 扁平化存储）
    routine_tasks       — 7 天恢复计划（JSON 列表）
    task_checkins       — 任务打卡状态（key-value）
    song_lists          — 治愈歌单（JSON 列表）
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# DDL：建表 SQL
# ─────────────────────────────────────────────────────────────

_DDL = """
-- 会话元数据
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id   TEXT PRIMARY KEY,
    initial_prompt TEXT,
    archived     INTEGER NOT NULL DEFAULT 0,  -- 0=活跃  1=已归档
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

-- 对话消息
CREATE TABLE IF NOT EXISTS chat_messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    agent_type   TEXT NOT NULL,
    role         TEXT NOT NULL CHECK(role IN ('user','assistant')),
    content      TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session
    ON chat_messages(session_id, agent_type);

-- 情绪评估结果
CREATE TABLE IF NOT EXISTS emotion_eval_results (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    emotion_type TEXT,
    intensity    INTEGER,
    core_pain    TEXT,
    breakup_type TEXT,
    suggestion   TEXT,
    raw_json     TEXT,            -- 完整 JSON 备份，兼容未来字段扩展
    created_at   TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
);

-- 7 天恢复计划
CREATE TABLE IF NOT EXISTS routine_tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    tasks_json   TEXT NOT NULL,   -- List[{day, theme, tasks}] 序列化
    created_at   TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
);

-- 任务打卡状态
CREATE TABLE IF NOT EXISTS task_checkins (
    session_id   TEXT NOT NULL,
    task_key     TEXT NOT NULL,   -- 格式 "{天}-{序号}"，如 "1-0"
    checked      INTEGER NOT NULL DEFAULT 0,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (session_id, task_key),
    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
);

-- 治愈歌单
CREATE TABLE IF NOT EXISTS song_lists (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    songs_json   TEXT NOT NULL,   -- List[{title, artist, url}] 序列化
    created_at   TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
);
"""


# ─────────────────────────────────────────────────────────────
# SQLiteStore
# ─────────────────────────────────────────────────────────────

class SQLiteStore:
    """
    轻量 SQLite 存取封装（线程安全单例）

    使用方式：
        db = get_db()
        db.upsert_session("sess_001", "我和他分手了三个月……")
        db.save_chat_message("sess_001", "therapist", "user", "我很难过")
    """

    _instance: Optional["SQLiteStore"] = None
    _lock = threading.Lock()

    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()   # 每线程独立连接（Streamlit 多线程安全）
        self._init_db()

    # ── 单例工厂 ──────────────────────────────────────────────

    @classmethod
    def get_instance(cls, db_path: str | Path) -> "SQLiteStore":
        """
        获取单例（惰性初始化，线程安全）

        参数:
            db_path: 数据库文件路径
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    # ── 连接管理 ──────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """获取当前线程的 SQLite 连接（按需创建）"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")   # 写时复制，减少锁争用
            conn.execute("PRAGMA foreign_keys=ON;")
            self._local.conn = conn
        return self._local.conn

    @contextmanager
    def _tx(self) -> Generator[sqlite3.Connection, None, None]:
        """上下文管理器：提供带自动提交/回滚的事务"""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error("[SQLiteStore] 事务回滚: %s", exc, exc_info=True)
            raise

    def _init_db(self) -> None:
        """执行 DDL，确保所有表和索引存在"""
        try:
            with self._tx() as conn:
                conn.executescript(_DDL)
            logger.info("[SQLiteStore] 数据库初始化完成: %s", self._db_path)
        except Exception as exc:
            logger.error("[SQLiteStore] 初始化失败: %s", exc)

    # ── 静默降级装饰器（防止 DB 异常崩溃 UI）─────────────────

    @staticmethod
    def _safe(func):
        """
        装饰器：捕获所有数据库异常，记录日志后返回默认值。
        被装饰函数签名中的返回类型注解会被保留，实际返回 None 或 []。
        """
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                logger.error(
                    "[SQLiteStore] %s 失败: %s", func.__name__, exc, exc_info=True
                )
                return None
        return wrapper

    # ─────────────────────────────────────────────────────────
    # 会话操作
    # ─────────────────────────────────────────────────────────

    @_safe
    def upsert_session(
        self,
        session_id: str,
        initial_prompt: str = "",
        archived: bool = False,
    ) -> None:
        """
        新建或更新会话记录

        参数:
            session_id:     会话唯一标识（如 "sess_20260702_143000"）
            initial_prompt: 触发一键生成时用户的原始输入
            archived:       是否标记为已归档（清空后调用）
        """
        now = _now()
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO user_sessions (session_id, initial_prompt, archived, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    initial_prompt = excluded.initial_prompt,
                    archived       = excluded.archived,
                    updated_at     = excluded.updated_at
                """,
                (session_id, initial_prompt, int(archived), now, now),
            )

    @_safe
    def archive_session(self, session_id: str) -> None:
        """
        将指定会话标记为已归档（软删除，保留历史数据）

        参数:
            session_id: 会话唯一标识
        """
        with self._tx() as conn:
            conn.execute(
                "UPDATE user_sessions SET archived=1, updated_at=? WHERE session_id=?",
                (_now(), session_id),
            )

    @_safe
    def get_latest_active_session_id(self) -> Optional[str]:
        """
        获取最近一条活跃（未归档）会话 ID

        返回:
            session_id 字符串，若不存在返回 None
        """
        conn = self._get_conn()
        row = conn.execute(
            "SELECT session_id FROM user_sessions WHERE archived=0 ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        return row["session_id"] if row else None

    # ─────────────────────────────────────────────────────────
    # 对话消息操作
    # ─────────────────────────────────────────────────────────

    @_safe
    def save_chat_message(
        self,
        session_id: str,
        agent_type: str,
        role: str,
        content: str,
    ) -> None:
        """
        追加一条对话消息

        参数:
            session_id: 会话唯一标识
            agent_type: Agent 类型（therapist/closure/routine/honesty）
            role:       消息角色（"user" 或 "assistant"）
            content:    消息内容
        """
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (session_id, agent_type, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, agent_type, role, content, _now()),
            )

    @_safe
    def load_chat_history(
        self,
        session_id: str,
        agent_type: str,
    ) -> List[Dict[str, str]]:
        """
        加载指定会话、指定 Agent 的全部对话历史

        参数:
            session_id: 会话唯一标识
            agent_type: Agent 类型

        返回:
            [{"role": "user"|"assistant", "content": str}, ...]
        """
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT role, content FROM chat_messages
            WHERE session_id=? AND agent_type=?
            ORDER BY id ASC
            """,
            (session_id, agent_type),
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    @_safe
    def clear_chat_history(self, session_id: str) -> None:
        """
        删除指定会话的全部对话消息（配合 clear_all_history 使用）

        参数:
            session_id: 会话唯一标识
        """
        with self._tx() as conn:
            conn.execute(
                "DELETE FROM chat_messages WHERE session_id=?",
                (session_id,),
            )

    # ─────────────────────────────────────────────────────────
    # 情绪评估结果操作
    # ─────────────────────────────────────────────────────────

    @_safe
    def save_emotion_eval(
        self,
        session_id: str,
        result: Dict[str, Any],
    ) -> None:
        """
        保存情绪评估结果

        参数:
            session_id: 会话唯一标识
            result: 包含 emotion_type/intensity/core_pain/breakup_type/suggestion 的字典
        """
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO emotion_eval_results
                    (session_id, emotion_type, intensity, core_pain, breakup_type, suggestion, raw_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    result.get("emotion_type"),
                    result.get("intensity"),
                    result.get("core_pain"),
                    result.get("breakup_type"),
                    result.get("suggestion"),
                    json.dumps(result, ensure_ascii=False),
                    _now(),
                ),
            )

    @_safe
    def load_emotion_eval(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        加载最新一条情绪评估结果

        参数:
            session_id: 会话唯一标识

        返回:
            结果字典，若不存在返回 None
        """
        conn = self._get_conn()
        row = conn.execute(
            """
            SELECT raw_json FROM emotion_eval_results
            WHERE session_id=?
            ORDER BY id DESC LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if row and row["raw_json"]:
            return json.loads(row["raw_json"])
        return None

    # ─────────────────────────────────────────────────────────
    # 7 天恢复计划操作
    # ─────────────────────────────────────────────────────────

    @_safe
    def save_routine_tasks(
        self,
        session_id: str,
        tasks: List[Dict],
    ) -> None:
        """
        保存 7 天恢复计划

        参数:
            session_id: 会话唯一标识
            tasks: parse_7day_plan() 返回的列表
        """
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO routine_tasks (session_id, tasks_json, created_at)
                VALUES (?, ?, ?)
                """,
                (session_id, json.dumps(tasks, ensure_ascii=False), _now()),
            )

    @_safe
    def load_routine_tasks(self, session_id: str) -> Optional[List[Dict]]:
        """
        加载最新一条恢复计划

        参数:
            session_id: 会话唯一标识

        返回:
            任务列表，若不存在返回 None
        """
        conn = self._get_conn()
        row = conn.execute(
            """
            SELECT tasks_json FROM routine_tasks
            WHERE session_id=?
            ORDER BY id DESC LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if row and row["tasks_json"]:
            return json.loads(row["tasks_json"])
        return None

    # ─────────────────────────────────────────────────────────
    # 任务打卡操作
    # ─────────────────────────────────────────────────────────

    @_safe
    def save_task_checkin(
        self,
        session_id: str,
        task_key: str,
        checked: bool,
    ) -> None:
        """
        更新单个任务的打卡状态

        参数:
            session_id: 会话唯一标识
            task_key:   如 "1-0"（第1天第1个任务）
            checked:    是否已完成
        """
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO task_checkins (session_id, task_key, checked, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id, task_key) DO UPDATE SET
                    checked    = excluded.checked,
                    updated_at = excluded.updated_at
                """,
                (session_id, task_key, int(checked), _now()),
            )

    @_safe
    def load_task_checkins(self, session_id: str) -> Dict[str, bool]:
        """
        加载指定会话的全部打卡状态

        参数:
            session_id: 会话唯一标识

        返回:
            {"1-0": True, "1-1": False, ...}
        """
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT task_key, checked FROM task_checkins WHERE session_id=?",
            (session_id,),
        ).fetchall()
        return {r["task_key"]: bool(r["checked"]) for r in rows}

    # ─────────────────────────────────────────────────────────
    # 治愈歌单操作
    # ─────────────────────────────────────────────────────────

    @_safe
    def save_song_list(
        self,
        session_id: str,
        songs: List[Dict],
    ) -> None:
        """
        保存治愈歌单

        参数:
            session_id: 会话唯一标识
            songs: [{"title": str, "artist": str, "url": str}, ...]
        """
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO song_lists (session_id, songs_json, created_at)
                VALUES (?, ?, ?)
                """,
                (session_id, json.dumps(songs, ensure_ascii=False), _now()),
            )

    @_safe
    def load_song_list(self, session_id: str) -> Optional[List[Dict]]:
        """
        加载最新歌单

        参数:
            session_id: 会话唯一标识

        返回:
            歌单列表，若不存在返回 None
        """
        conn = self._get_conn()
        row = conn.execute(
            """
            SELECT songs_json FROM song_lists
            WHERE session_id=?
            ORDER BY id DESC LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if row and row["songs_json"]:
            return json.loads(row["songs_json"])
        return None

    # ─────────────────────────────────────────────────────────
    # 统计辅助（课设展示用）
    # ─────────────────────────────────────────────────────────

    @_safe
    def get_session_stats(self) -> Dict[str, int]:
        """
        获取数据库统计数据（用于课设演示展示持久化效果）

        返回:
            {
                "total_sessions": int,    # 历史会话总数
                "total_messages": int,    # 全部消息总条数
                "total_checkins": int,    # 全部打卡记录数
            }
        """
        conn = self._get_conn()
        sessions = conn.execute("SELECT COUNT(*) FROM user_sessions").fetchone()[0]
        messages = conn.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
        checkins = conn.execute("SELECT COUNT(*) FROM task_checkins WHERE checked=1").fetchone()[0]
        return {
            "total_sessions": sessions or 0,
            "total_messages": messages or 0,
            "total_checkins": checkins or 0,
        }


# ─────────────────────────────────────────────────────────────
# 模块级单例入口
# ─────────────────────────────────────────────────────────────

_global_store: Optional[SQLiteStore] = None


def get_db(db_path: Optional[str | Path] = None) -> SQLiteStore:
    """
    获取全局 SQLiteStore 单例

    首次调用需传入 db_path；后续调用无需传参，返回同一实例。

    参数:
        db_path: 数据库文件路径（首次调用必填）

    返回:
        SQLiteStore 实例
    """
    global _global_store
    if _global_store is None:
        if db_path is None:
            raise ValueError(
                "首次调用 get_db() 必须传入 db_path，"
                "请在 SessionStore.init_session_state() 中完成初始化。"
            )
        _global_store = SQLiteStore.get_instance(db_path)
    return _global_store


# ─────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────

def _now() -> str:
    """返回 ISO 8601 格式的当前时间戳（本地时区）"""
    return datetime.now().isoformat(timespec="seconds")
