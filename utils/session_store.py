"""
st.session_state 封装、对话历史持久化、状态管理
新增：情绪评估结果存取（emotion_eval_result）
     批量流程顺序（BATCH_AGENT_ORDER，共 5 步）
"""

import logging
from datetime import datetime

import streamlit as st
from typing import List, Dict, Any, Optional

from config.settings import get_db_path

logger = logging.getLogger(__name__)


class SessionStore:
    """
    Session State 管理器：封装 Streamlit 的 session_state 操作

    所有状态读写必须通过此类完成，禁止直接操作 st.session_state
    """

    # ─────────────────────────────────────────
    # Tab 顺序（仅 4 个疗愈 Tab，不含情绪评估）
    # ─────────────────────────────────────────
    AGENT_ORDER = ["therapist", "closure", "routine", "honesty"]

    # ─────────────────────────────────────────
    # 批量生成顺序（5 步：情绪评估 → 4 个疗愈 Agent）
    # ─────────────────────────────────────────
    BATCH_AGENT_ORDER = ["emotion_eval", "therapist", "closure", "routine", "honesty"]

    # Agent 对话历史的 key 映射（仅 4 个疗愈 Agent 有 Tab 对话历史）
    HISTORY_KEYS = {
        "therapist": "therapist_chat_history",
        "closure":   "closure_chat_history",
        "routine":   "routine_chat_history",
        "honesty":   "honesty_chat_history",
    }

    # Agent 生成完成标记的 key 映射
    READY_KEYS = {
        "therapist": "therapist_ready",
        "closure":   "closure_ready",
        "routine":   "routine_ready",
        "honesty":   "honesty_ready",
    }

    # Agent 生成中状态的 key 映射
    GENERATING_KEYS = {
        "therapist": "therapist_generating",
        "closure":   "closure_generating",
        "routine":   "routine_generating",
        "honesty":   "honesty_generating",
    }

    # Agent 流式输出内容的 key 映射
    STREAMING_KEYS = {
        "therapist": "therapist_streaming",
        "closure":   "closure_streaming",
        "routine":   "routine_streaming",
        "honesty":   "honesty_streaming",
    }

    # Agent 待处理输入的 key 映射
    PENDING_INPUT_KEYS = {
        "therapist": "therapist_pending_input",
        "closure":   "closure_pending_input",
        "routine":   "routine_pending_input",
        "honesty":   "honesty_pending_input",
    }

    # 批量生成状态 key
    BATCH_STATE_KEY         = "batch_state"
    BATCH_CURRENT_INDEX_KEY = "batch_current_index"
    BATCH_INITIAL_PROMPT_KEY = "batch_initial_prompt"

    # 批量生成状态常量
    BATCH_STATE_IDLE       = "idle"
    BATCH_STATE_GENERATING = "generating"
    BATCH_STATE_COMPLETED  = "completed"

    # 情绪评估结果 key
    EMOTION_EVAL_RESULT_KEY = "emotion_eval_result"

    # 结构化恢复计划 key（List[Dict] | None）
    ROUTINE_TASKS_KEY = "routine_tasks"

    # 任务打卡状态 key（Dict[str, bool]，格式 "天-序号" 如 "1-0"）
    TASK_CHECKED_KEY = "task_checked"

    # 庆祝特效触发标记
    BATCH_CELEBRATED_KEY  = "batch_celebrated"   # 一键生成完成气球
    TASKS_CELEBRATED_KEY  = "tasks_celebrated"   # 任务全部完成气球

    # 治愈歌单 key（List[Dict] | None，解析自 routine agent 回复）
    SONG_LIST_KEY = "routine_song_list"

    # SQLite 当前会话 ID（跨 rerun 保持；页面关闭后由 SQLite 恢复）
    DB_SESSION_ID_KEY = "db_session_id"

    # ─────────────────────────────────────────
    # 初始化
    # ─────────────────────────────────────────

    # ─────────────────────────────────────────
    # SQLite 会话辅助
    # ─────────────────────────────────────────

    @staticmethod
    def _init_db() -> None:
        """
        初始化 SQLite 数据库单例（幂等，安全重复调用）

        异常静默降级：DB 初始化失败不影响页面正常运行
        """
        try:
            from db.sqlite_store import get_db
            get_db(get_db_path())
        except Exception as exc:
            logger.error("[SessionStore] SQLite 初始化失败（降级为纯内存模式）: %s", exc)

    @staticmethod
    def get_current_session_id() -> Optional[str]:
        """获取当前 SQLite 会话 ID（可能为 None，表示尚未开启会话）"""
        return st.session_state.get(SessionStore.DB_SESSION_ID_KEY)

    @staticmethod
    def _set_session_id(session_id: str) -> None:
        """设置当前 SQLite 会话 ID（内部使用）"""
        st.session_state[SessionStore.DB_SESSION_ID_KEY] = session_id

    @staticmethod
    def _restore_from_db() -> None:
        """
        从 SQLite 恢复最近一次活跃会话的数据到 session_state

        触发时机：页面刷新/重新打开时，DB_SESSION_ID_KEY 为空
        若数据库中无活跃会话，则静默跳过（全新开始）
        """
        try:
            from db.sqlite_store import get_db
            db = get_db()

            # 查找最近活跃 session
            session_id = db.get_latest_active_session_id()
            if not session_id:
                return

            # 恢复会话 ID
            SessionStore._set_session_id(session_id)
            logger.info("[SessionStore] 从 SQLite 恢复会话: %s", session_id)

            # 恢复对话历史（仅 4 个疗愈 Agent）
            for agent_type, key in SessionStore.HISTORY_KEYS.items():
                history = db.load_chat_history(session_id, agent_type)
                if history:
                    st.session_state[key] = history
                    # 有历史则标记为已完成，让输入框显现
                    ready_key = SessionStore.READY_KEYS.get(agent_type)
                    if ready_key:
                        st.session_state[ready_key] = True

            # 恢复情绪评估结果
            emotion = db.load_emotion_eval(session_id)
            if emotion:
                st.session_state[SessionStore.EMOTION_EVAL_RESULT_KEY] = emotion

            # 恢复 7 天恢复计划
            tasks = db.load_routine_tasks(session_id)
            if tasks:
                st.session_state[SessionStore.ROUTINE_TASKS_KEY] = tasks

            # 恢复打卡状态
            checkins = db.load_task_checkins(session_id)
            if checkins:
                st.session_state[SessionStore.TASK_CHECKED_KEY] = checkins

            # 恢复治愈歌单
            songs = db.load_song_list(session_id)
            if songs:
                st.session_state[SessionStore.SONG_LIST_KEY] = songs

        except Exception as exc:
            logger.error("[SessionStore] 从 SQLite 恢复失败（降级为空白状态）: %s", exc)

    @staticmethod
    def init_session_state():
        """初始化所有 session_state 变量，并尝试从 SQLite 恢复上次会话"""

        # ── 初始化 SQLite（幂等）──
        SessionStore._init_db()

        # 对话历史
        for key in SessionStore.HISTORY_KEYS.values():
            if key not in st.session_state:
                st.session_state[key] = []

        # 生成完成标记
        for key in SessionStore.READY_KEYS.values():
            if key not in st.session_state:
                st.session_state[key] = False

        # 生成中状态
        for key in SessionStore.GENERATING_KEYS.values():
            if key not in st.session_state:
                st.session_state[key] = False

        # 流式输出内容
        for key in SessionStore.STREAMING_KEYS.values():
            if key not in st.session_state:
                st.session_state[key] = ""

        # 待处理输入
        for key in SessionStore.PENDING_INPUT_KEYS.values():
            if key not in st.session_state:
                st.session_state[key] = None

        # 批量生成状态
        if SessionStore.BATCH_STATE_KEY not in st.session_state:
            st.session_state[SessionStore.BATCH_STATE_KEY] = SessionStore.BATCH_STATE_IDLE
        if SessionStore.BATCH_CURRENT_INDEX_KEY not in st.session_state:
            st.session_state[SessionStore.BATCH_CURRENT_INDEX_KEY] = 0
        if SessionStore.BATCH_INITIAL_PROMPT_KEY not in st.session_state:
            st.session_state[SessionStore.BATCH_INITIAL_PROMPT_KEY] = ""

        # 情绪评估结果（None 表示未评估）
        if SessionStore.EMOTION_EVAL_RESULT_KEY not in st.session_state:
            st.session_state[SessionStore.EMOTION_EVAL_RESULT_KEY] = None

        # 结构化恢复计划任务
        if SessionStore.ROUTINE_TASKS_KEY not in st.session_state:
            st.session_state[SessionStore.ROUTINE_TASKS_KEY] = None

        # 任务打卡状态
        if SessionStore.TASK_CHECKED_KEY not in st.session_state:
            st.session_state[SessionStore.TASK_CHECKED_KEY] = {}

        # 庆祝特效标记
        if SessionStore.BATCH_CELEBRATED_KEY not in st.session_state:
            st.session_state[SessionStore.BATCH_CELEBRATED_KEY] = False
        if SessionStore.TASKS_CELEBRATED_KEY not in st.session_state:
            st.session_state[SessionStore.TASKS_CELEBRATED_KEY] = False

        # 治愈歌单
        if SessionStore.SONG_LIST_KEY not in st.session_state:
            st.session_state[SessionStore.SONG_LIST_KEY] = None

        # Agent 实例缓存
        if "agents_initialized" not in st.session_state:
            st.session_state.agents_initialized = False

        # API Key 输入
        if "api_key_input" not in st.session_state:
            st.session_state.api_key_input = ""

        # SQLite 会话 ID（首次进入页面时尝试从数据库恢复）
        if SessionStore.DB_SESSION_ID_KEY not in st.session_state:
            st.session_state[SessionStore.DB_SESSION_ID_KEY] = None
            # 仅在全新 Streamlit session（非 rerun）时才恢复数据
            SessionStore._restore_from_db()

    # ─────────────────────────────────────────
    # 对话历史操作
    # ─────────────────────────────────────────

    @staticmethod
    def get_chat_history(agent_type: str) -> List[Dict[str, str]]:
        """
        获取指定 Agent 的对话历史

        参数:
            agent_type: Agent 类型

        返回:
            对话历史列表
        """
        key = SessionStore.HISTORY_KEYS.get(agent_type)
        if key and key in st.session_state:
            return st.session_state[key]
        return []

    @staticmethod
    def append_to_history(agent_type: str, role: str, content: str):
        """
        向指定 Agent 的对话历史追加消息，并同步写入 SQLite

        参数:
            agent_type: Agent 类型
            role: 消息角色（"user" 或 "assistant"）
            content: 消息内容
        """
        key = SessionStore.HISTORY_KEYS.get(agent_type)
        if key:
            if key not in st.session_state:
                st.session_state[key] = []
            st.session_state[key].append({"role": role, "content": content})

        # ── 同步持久化到 SQLite ──
        session_id = SessionStore.get_current_session_id()
        if session_id:
            try:
                from db.sqlite_store import get_db
                get_db().save_chat_message(session_id, agent_type, role, content)
            except Exception as exc:
                logger.warning("[SessionStore] append_to_history SQLite 写入失败: %s", exc)

    @staticmethod
    def clear_all_history():
        """
        清空所有 Agent 的对话历史，并重置所有状态标记（含情绪评估结果）
        同时将当前 SQLite 会话标记为已归档（软删除，保留历史数据）
        """
        # ── 先归档 SQLite 会话（清空前执行，session_id 还在）──
        session_id = SessionStore.get_current_session_id()
        if session_id:
            try:
                from db.sqlite_store import get_db
                get_db().archive_session(session_id)
                logger.info("[SessionStore] SQLite 会话已归档: %s", session_id)
            except Exception as exc:
                logger.warning("[SessionStore] clear_all_history SQLite 归档失败: %s", exc)
        # 重置 session_id（下次一键生成时创建新会话）
        st.session_state[SessionStore.DB_SESSION_ID_KEY] = None

        for key in SessionStore.HISTORY_KEYS.values():
            st.session_state[key] = []

        for key in SessionStore.READY_KEYS.values():
            st.session_state[key] = False

        for key in SessionStore.GENERATING_KEYS.values():
            st.session_state[key] = False

        for key in SessionStore.STREAMING_KEYS.values():
            st.session_state[key] = ""

        for key in SessionStore.PENDING_INPUT_KEYS.values():
            st.session_state[key] = None

        # 重置批量状态
        st.session_state[SessionStore.BATCH_STATE_KEY]          = SessionStore.BATCH_STATE_IDLE
        st.session_state[SessionStore.BATCH_CURRENT_INDEX_KEY]  = 0
        st.session_state[SessionStore.BATCH_INITIAL_PROMPT_KEY] = ""

        # 清空情绪评估结果
        st.session_state[SessionStore.EMOTION_EVAL_RESULT_KEY]  = None

        # 清空恢复计划任务与打卡状态
        st.session_state[SessionStore.ROUTINE_TASKS_KEY]  = None
        st.session_state[SessionStore.TASK_CHECKED_KEY]   = {}

        # 重置庆祝标记（清空后下次生成可重新触发）
        st.session_state[SessionStore.BATCH_CELEBRATED_KEY]  = False
        st.session_state[SessionStore.TASKS_CELEBRATED_KEY]  = False

        # 清空治愈歌单
        st.session_state[SessionStore.SONG_LIST_KEY] = None

    @staticmethod
    def clear_history(agent_type: str):
        """清空指定 Agent 的对话历史"""
        key = SessionStore.HISTORY_KEYS.get(agent_type)
        if key:
            st.session_state[key] = []

    # ─────────────────────────────────────────
    # Agent 基础状态操作
    # ─────────────────────────────────────────

    @staticmethod
    def get_api_key() -> str:
        """获取用户输入的 API Key"""
        return st.session_state.get("api_key_input", "")

    @staticmethod
    def set_api_key(api_key: str):
        """设置用户输入的 API Key"""
        st.session_state.api_key_input = api_key

    @staticmethod
    def is_agents_initialized() -> bool:
        """检查 Agent 是否已初始化"""
        return st.session_state.get("agents_initialized", False)

    @staticmethod
    def set_agents_initialized(initialized: bool):
        """设置 Agent 初始化状态"""
        st.session_state.agents_initialized = initialized

    @staticmethod
    def is_agent_ready(agent_type: str) -> bool:
        """检查指定 Agent 是否已生成完成"""
        key = SessionStore.READY_KEYS.get(agent_type)
        return st.session_state.get(key, False) if key else False

    @staticmethod
    def set_agent_ready(agent_type: str, ready: bool = True):
        """设置指定 Agent 的生成完成标记"""
        key = SessionStore.READY_KEYS.get(agent_type)
        if key:
            st.session_state[key] = ready

    @staticmethod
    def is_agent_generating(agent_type: str) -> bool:
        """检查指定 Agent 是否正在生成中"""
        key = SessionStore.GENERATING_KEYS.get(agent_type)
        return st.session_state.get(key, False) if key else False

    @staticmethod
    def set_agent_generating(agent_type: str, generating: bool = True):
        """设置指定 Agent 的生成中状态"""
        key = SessionStore.GENERATING_KEYS.get(agent_type)
        if key:
            st.session_state[key] = generating

    @staticmethod
    def get_agent_streaming_content(agent_type: str) -> str:
        """获取指定 Agent 的流式输出内容"""
        key = SessionStore.STREAMING_KEYS.get(agent_type)
        return st.session_state.get(key, "") if key else ""

    @staticmethod
    def set_agent_streaming_content(agent_type: str, content: str):
        """设置指定 Agent 的流式输出内容"""
        key = SessionStore.STREAMING_KEYS.get(agent_type)
        if key:
            st.session_state[key] = content

    @staticmethod
    def clear_agent_streaming_content(agent_type: str):
        """清空指定 Agent 的流式输出内容"""
        SessionStore.set_agent_streaming_content(agent_type, "")

    @staticmethod
    def get_pending_input(agent_type: str) -> Optional[str]:
        """获取指定 Agent 的待处理输入"""
        key = SessionStore.PENDING_INPUT_KEYS.get(agent_type)
        return st.session_state.get(key, None) if key else None

    @staticmethod
    def set_pending_input(agent_type: str, user_input: Optional[str]):
        """设置指定 Agent 的待处理输入"""
        key = SessionStore.PENDING_INPUT_KEYS.get(agent_type)
        if key:
            st.session_state[key] = user_input

    @staticmethod
    def clear_pending_input(agent_type: str):
        """清除指定 Agent 的待处理输入"""
        SessionStore.set_pending_input(agent_type, None)

    # ─────────────────────────────────────────
    # 情绪评估结果操作
    # ─────────────────────────────────────────

    @staticmethod
    def get_emotion_eval_result() -> Optional[Dict[str, Any]]:
        """
        获取情绪评估结果

        返回:
            评估结果字典，包含以下字段（若未评估则返回 None）：
            - emotion_type: str  情绪类型（悲伤/愤怒/不甘/释然/焦虑）
            - intensity: int     情绪烈度（1-10）
            - core_pain: str     核心痛点
            - breakup_type: str  分手类型（被分手/主动分手/和平分手/暧昧拉扯）
            - suggestion: str    适配建议（给后续 Agent 的调整方向）
        """
        return st.session_state.get(SessionStore.EMOTION_EVAL_RESULT_KEY, None)

    @staticmethod
    def set_emotion_eval_result(result: Dict[str, Any]):
        """
        存储情绪评估结果，并同步写入 SQLite

        参数:
            result: 包含 emotion_type/intensity/core_pain/breakup_type/suggestion 的字典
        """
        st.session_state[SessionStore.EMOTION_EVAL_RESULT_KEY] = result

        # ── 同步持久化到 SQLite ──
        session_id = SessionStore.get_current_session_id()
        if session_id:
            try:
                from db.sqlite_store import get_db
                get_db().save_emotion_eval(session_id, result)
            except Exception as exc:
                logger.warning("[SessionStore] set_emotion_eval_result SQLite 写入失败: %s", exc)

    @staticmethod
    def has_emotion_eval_result() -> bool:
        """是否已有情绪评估结果"""
        result = SessionStore.get_emotion_eval_result()
        return result is not None and bool(result)

    # ─────────────────────────────────────────
    # 批量生成状态操作
    # ─────────────────────────────────────────

    @staticmethod
    def get_batch_state() -> str:
        """获取批量生成状态"""
        return st.session_state.get(SessionStore.BATCH_STATE_KEY, SessionStore.BATCH_STATE_IDLE)

    @staticmethod
    def set_batch_state(state: str):
        """设置批量生成状态"""
        st.session_state[SessionStore.BATCH_STATE_KEY] = state

    @staticmethod
    def is_batch_generating() -> bool:
        """是否正在批量生成"""
        return SessionStore.get_batch_state() == SessionStore.BATCH_STATE_GENERATING

    @staticmethod
    def is_batch_completed() -> bool:
        """批量生成是否已完成"""
        return SessionStore.get_batch_state() == SessionStore.BATCH_STATE_COMPLETED

    @staticmethod
    def get_batch_current_index() -> int:
        """获取批量生成当前索引（对应 BATCH_AGENT_ORDER）"""
        return st.session_state.get(SessionStore.BATCH_CURRENT_INDEX_KEY, 0)

    @staticmethod
    def set_batch_current_index(index: int):
        """设置批量生成当前索引"""
        st.session_state[SessionStore.BATCH_CURRENT_INDEX_KEY] = index

    @staticmethod
    def get_batch_initial_prompt() -> str:
        """获取批量生成初始用户输入"""
        return st.session_state.get(SessionStore.BATCH_INITIAL_PROMPT_KEY, "")

    @staticmethod
    def set_batch_initial_prompt(prompt: str):
        """设置批量生成初始用户输入"""
        st.session_state[SessionStore.BATCH_INITIAL_PROMPT_KEY] = prompt

    @staticmethod
    def get_batch_current_agent_type() -> Optional[str]:
        """获取批量生成当前 Agent 类型（从 BATCH_AGENT_ORDER 取）"""
        index = SessionStore.get_batch_current_index()
        if index < len(SessionStore.BATCH_AGENT_ORDER):
            return SessionStore.BATCH_AGENT_ORDER[index]
        return None

    @staticmethod
    def get_batch_agent_status(agent_type: str) -> str:
        """
        获取批量生成中指定 Agent（仅 4 疗愈 Agent）的状态

        返回:
            "completed" / "generating" / "waiting"
        """
        if not SessionStore.is_batch_generating():
            return "completed" if SessionStore.is_batch_completed() else "waiting"

        current_idx  = SessionStore.get_batch_current_index()

        try:
            # 在 BATCH_AGENT_ORDER 中查找位置
            batch_idx = SessionStore.BATCH_AGENT_ORDER.index(agent_type)
        except ValueError:
            return "waiting"

        if batch_idx < current_idx:
            return "completed"
        elif batch_idx == current_idx:
            return "generating"
        else:
            return "waiting"

    @staticmethod
    def start_batch(user_input: str):
        """
        启动批量生成（清空历史 + 重置状态机到第 0 步：情绪评估）
        同时在 SQLite 中创建新的会话记录，实现跨会话持久化。

        参数:
            user_input: 用户输入
        """
        SessionStore.clear_all_history()
        SessionStore.set_batch_state(SessionStore.BATCH_STATE_GENERATING)
        SessionStore.set_batch_current_index(0)
        SessionStore.set_batch_initial_prompt(user_input)

        # ── 在 SQLite 中创建新会话（每次一键生成产生独立 session 记录）──
        session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        SessionStore._set_session_id(session_id)
        try:
            from db.sqlite_store import get_db
            get_db().upsert_session(session_id, initial_prompt=user_input)
            logger.info("[SessionStore] 新建 SQLite 会话: %s", session_id)
        except Exception as exc:
            logger.warning("[SessionStore] start_batch SQLite 建会话失败: %s", exc)

    @staticmethod
    def advance_batch():
        """推进批量生成到下一步（自动检测是否全部完成）"""
        current_index = SessionStore.get_batch_current_index()
        next_index = current_index + 1

        if next_index >= len(SessionStore.BATCH_AGENT_ORDER):
            SessionStore.set_batch_state(SessionStore.BATCH_STATE_COMPLETED)
        else:
            SessionStore.set_batch_current_index(next_index)

    @staticmethod
    def reset_batch():
        """重置批量生成状态（不清空历史和情绪评估结果）"""
        SessionStore.set_batch_state(SessionStore.BATCH_STATE_IDLE)
        SessionStore.set_batch_current_index(0)
        SessionStore.set_batch_initial_prompt("")

    # ─────────────────────────────────────────
    # Agent 状态综合判断
    # ─────────────────────────────────────────

    @staticmethod
    def get_agent_status(agent_type: str) -> str:
        """
        获取指定 Agent 的综合状态

        返回:
            "completed" - 已完成（可显示输入框）
            "generating" - 正在生成中
            "waiting"   - 等待中（未开始）
        """
        if SessionStore.is_batch_generating():
            return SessionStore.get_batch_agent_status(agent_type)

        if SessionStore.is_batch_completed():
            return "completed"

        if SessionStore.is_agent_generating(agent_type):
            return "generating"

        if SessionStore.is_agent_ready(agent_type):
            return "completed"

        return "waiting"

    @staticmethod
    def should_show_input(agent_type: str) -> bool:
        """
        判断是否应该显示输入框

        条件：Agent 状态为 completed 且当前不在生成中
        """
        status = SessionStore.get_agent_status(agent_type)
        is_generating = SessionStore.is_agent_generating(agent_type)
        return status == "completed" and not is_generating

    # ─────────────────────────────────────────
    # 治愈歌单操作
    # ─────────────────────────────────────────

    @staticmethod
    def get_song_list() -> Optional[list]:
        """
        获取治愈歌单

        返回:
            [{"title": str, "artist": str, "url": str}, ...] 或 None
        """
        return st.session_state.get(SessionStore.SONG_LIST_KEY, None)

    @staticmethod
    def set_song_list(songs: list):
        """存储治愈歌单（由 music_mapper.parse_song_list 解析后写入），并同步写入 SQLite"""
        st.session_state[SessionStore.SONG_LIST_KEY] = songs

        # ── 同步持久化到 SQLite ──
        session_id = SessionStore.get_current_session_id()
        if session_id:
            try:
                from db.sqlite_store import get_db
                get_db().save_song_list(session_id, songs)
            except Exception as exc:
                logger.warning("[SessionStore] set_song_list SQLite 写入失败: %s", exc)

    @staticmethod
    def has_song_list() -> bool:
        """是否已有歌单数据"""
        songs = SessionStore.get_song_list()
        return songs is not None and len(songs) > 0

    # ─────────────────────────────────────────
    # 结构化恢复计划操作
    # ─────────────────────────────────────────

    @staticmethod
    def get_routine_tasks() -> Optional[list]:
        """
        获取结构化7天恢复计划

        返回:
            [{"day": int, "theme": str, "tasks": [str, str, str]}, ...] 共7项，
            或 None（尚未生成）
        """
        return st.session_state.get(SessionStore.ROUTINE_TASKS_KEY, None)

    @staticmethod
    def set_routine_tasks(tasks: list):
        """
        存储结构化7天恢复计划，并同步写入 SQLite

        参数:
            tasks: parse_7day_plan() 返回的列表
        """
        st.session_state[SessionStore.ROUTINE_TASKS_KEY] = tasks

        # ── 同步持久化到 SQLite ──
        session_id = SessionStore.get_current_session_id()
        if session_id:
            try:
                from db.sqlite_store import get_db
                get_db().save_routine_tasks(session_id, tasks)
            except Exception as exc:
                logger.warning("[SessionStore] set_routine_tasks SQLite 写入失败: %s", exc)

    @staticmethod
    def has_routine_tasks() -> bool:
        """是否已有结构化恢复计划"""
        tasks = SessionStore.get_routine_tasks()
        return tasks is not None and len(tasks) > 0

    # ─────────────────────────────────────────
    # 任务打卡状态操作
    # ─────────────────────────────────────────

    @staticmethod
    def get_task_checked() -> Dict[str, bool]:
        """
        获取全部任务的打卡状态

        返回:
            {"1-0": True, "1-1": False, ...}，键格式为 "{天}-{任务序号(0-2)}"
        """
        return st.session_state.get(SessionStore.TASK_CHECKED_KEY, {})

    @staticmethod
    def set_task_checked(task_key: str, checked: bool):
        """
        设置单个任务的打卡状态，并同步写入 SQLite

        参数:
            task_key: 如 "1-0"（第1天第1个任务）
            checked:  是否已完成
        """
        state = st.session_state.get(SessionStore.TASK_CHECKED_KEY, {})
        state[task_key] = checked
        st.session_state[SessionStore.TASK_CHECKED_KEY] = state

        # ── 同步持久化到 SQLite ──
        session_id = SessionStore.get_current_session_id()
        if session_id:
            try:
                from db.sqlite_store import get_db
                get_db().save_task_checkin(session_id, task_key, checked)
            except Exception as exc:
                logger.warning("[SessionStore] set_task_checked SQLite 写入失败: %s", exc)

    @staticmethod
    def get_task_progress() -> tuple[int, int]:
        """
        计算任务完成进度

        返回:
            (已完成数, 总任务数) — 总任务数 = 天数 × 3
        """
        tasks = SessionStore.get_routine_tasks()
        if not tasks:
            return 0, 0
        total = len(tasks) * 3
        checked = SessionStore.get_task_checked()
        done = sum(1 for v in checked.values() if v)
        return done, total

    # ─────────────────────────────────────────
    # 庆祝特效标记操作
    # ─────────────────────────────────────────

    @staticmethod
    def is_batch_celebrated() -> bool:
        """一键生成完成气球是否已触发过"""
        return st.session_state.get(SessionStore.BATCH_CELEBRATED_KEY, False)

    @staticmethod
    def set_batch_celebrated(v: bool):
        """标记一键生成完成气球已触发"""
        st.session_state[SessionStore.BATCH_CELEBRATED_KEY] = v

    @staticmethod
    def is_tasks_celebrated() -> bool:
        """任务全部完成气球是否已触发过"""
        return st.session_state.get(SessionStore.TASKS_CELEBRATED_KEY, False)

    @staticmethod
    def set_tasks_celebrated(v: bool):
        """标记任务全部完成气球已触发"""
        st.session_state[SessionStore.TASKS_CELEBRATED_KEY] = v
