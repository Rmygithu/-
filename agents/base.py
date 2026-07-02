"""
智能体基类与通用模型初始化逻辑
支持 Agno 原生多轮对话记忆
"""

import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.in_memory import InMemoryDb
from typing import Optional, Generator, List, Dict

from config.constants import MIMO_BASE_URL, MIMO_MODEL_ID
from utils.logger import log_agent_start, log_agent_success, log_agent_error

# RAG 向量检索（延迟导入，chromadb 未安装时静默降级）
try:
    from rag import retrieve as _rag_retrieve
    _RAG_ENABLED = True
except Exception:
    _RAG_ENABLED = False
    _rag_retrieve = None


# 对话历史滑动窗口大小（轮数）
MAX_HISTORY_ROUNDS = 10

# 全局数据库实例（所有 Agent 共享同一个内存数据库）
_db_instance = None


def get_db_instance() -> InMemoryDb:
    """
    获取全局内存数据库实例（单例模式）

    使用 InMemoryDb 作为内存数据库，支持 Agno 原生记忆功能

    返回:
        InMemoryDb 实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = InMemoryDb()
    return _db_instance


def create_model(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_id: Optional[str] = None,
):
    """
    创建 MiMo LLM 模型实例

    参数:
        api_key: API 密钥（优先使用传入值，否则从环境变量读取）
        base_url: API 基础 URL
        model_id: 模型 ID

    返回:
        模型实例

    异常:
        ValueError: 未提供 API Key 且环境变量中也未配置时抛出
    """
    # 优先使用传入的 api_key，否则从环境变量读取
    final_api_key = api_key or os.getenv("MIMO_API_KEY")
    if not final_api_key:
        raise ValueError(
            "❌ 未提供 API Key！请通过以下方式之一配置：\n"
            "1. 在侧边栏输入 API Key\n"
            "2. 在 .env 文件中设置 MIMO_API_KEY\n"
            "3. 设置系统环境变量 MIMO_API_KEY"
        )

    return OpenAIChat(
        id=model_id or MIMO_MODEL_ID,
        api_key=final_api_key,
        base_url=base_url or MIMO_BASE_URL,
    )


class BaseAgent:
    """
    智能体基类，封装基于 Agno 原生记忆的对话逻辑

    特性：
    1. 每个 Agent 拥有独立的 session_id，实现对话隔离
    2. 使用 InMemoryDb 作为记忆存储后端
    3. 使用 Agno 的 add_history_to_context 自动管理上下文
    4. 支持流式和非流式输出
    """

    def __init__(self, agent: Agent, name: str, agent_type: str):
        """
        初始化基类

        参数:
            agent: Agno Agent 实例
            name: Agent 显示名称
            agent_type: Agent 类型标识 (therapist/closure/routine/honesty)
        """
        self.agent = agent
        self.name = name
        self.agent_type = agent_type
        self._session_id = f"breakup_{agent_type}"

        # 配置 Agent 的记忆参数
        self.agent.session_id = self._session_id
        self.agent.add_history_to_context = True
        self.agent.num_history_messages = MAX_HISTORY_ROUNDS * 2  # 每轮包含用户和助手消息
        self.agent.store_history_messages = True

        # 配置内存数据库（启用历史记录功能）
        self.agent.db = get_db_instance()

    @property
    def session_id(self) -> str:
        """获取会话 ID"""
        return self._session_id

    @staticmethod
    def _rag_augment(message: str) -> str:
        """
        为用户消息注入 RAG 检索到的心理学知识（可选增强）

        参数:
            message: 原始用户消息

        返回:
            增强后的消息（检索失败时返回原消息）
        """
        if not _RAG_ENABLED or not _rag_retrieve:
            return message

        context = _rag_retrieve(message, k=3)
        if context:
            return f"{context}\n\n[用户消息]\n{message}"
        return message

    def stream_chat(self, user_message: str, images: Optional[List] = None) -> Generator:
        """
        带原生记忆的流式对话，自动注入 RAG 心理学参考资料

        参数:
            user_message: 用户消息
            images: 可选的图片列表

        返回:
            流式迭代器，每个 chunk 包含 content 字段
        """
        log_agent_start(self.name)

        try:
            # RAG 增强：检索相关心理学知识并注入到消息前缀
            augmented = self._rag_augment(user_message)

            # 使用 Agno 原生记忆的流式调用
            response = self.agent.run(
                augmented,
                stream=True,
                images=images,
            )
            return response

        except Exception as e:
            log_agent_error(self.name, str(e))
            raise

    def run(self, user_message: str, images: Optional[List] = None) -> str:
        """
        带原生记忆的同步对话

        参数:
            user_message: 用户消息
            images: 可选的图片列表

        返回:
            助手回复内容
        """
        log_agent_start(self.name)

        try:
            # 使用 Agno 原生记忆的同步调用
            response = self.agent.run(
                user_message,
                images=images,
            )
            log_agent_success(self.name)
            return response.content

        except Exception as e:
            log_agent_error(self.name, str(e))
            raise

    def run_once_stream(self, prompt: str) -> Generator:
        """
        单次流式执行（用于一键生成场景），自动注入 RAG 心理学参考资料

        注意：此方法也会写入 Agent 记忆，确保后续对话能承接上下文

        参数:
            prompt: 完整的提示词

        返回:
            流式迭代器
        """
        log_agent_start(self.name)

        try:
            # RAG 增强：为一键生成也注入专业参考资料
            augmented = self._rag_augment(prompt)

            # 使用 Agno 原生记忆的流式调用
            response = self.agent.run(
                augmented,
                stream=True,
            )
            return response

        except Exception as e:
            log_agent_error(self.name, str(e))
            raise

    def run_once(self, prompt: str) -> str:
        """
        单次同步执行（用于一键生成场景）

        注意：此方法也会写入 Agent 记忆，确保后续对话能承接上下文

        参数:
            prompt: 完整的提示词

        返回:
            Agent 的回复内容
        """
        log_agent_start(self.name)

        try:
            # 使用 Agno 原生记忆的同步调用
            response = self.agent.run(prompt)
            log_agent_success(self.name)
            return response.content

        except Exception as e:
            log_agent_error(self.name, str(e))
            raise

    def clear_memory(self) -> None:
        """
        清除 Agent 的对话记忆
        """
        try:
            # 通过删除 session 来清除记忆
            if hasattr(self.agent, 'delete_session'):
                self.agent.delete_session()
        except Exception as e:
            log_agent_error(self.name, f"清除记忆失败: {str(e)}")

    def get_memory_summary(self) -> str:
        """
        获取对话记忆摘要（用于调试）

        返回:
            记忆摘要字符串
        """
        try:
            messages = self.agent.get_session_messages()
            if messages:
                return f"Agent '{self.name}' 有 {len(messages)} 条历史消息"
            return f"Agent '{self.name}' 无历史消息"
        except Exception:
            return f"Agent '{self.name}' 记忆状态未知"
