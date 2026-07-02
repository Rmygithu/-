"""
智能体统一调度、批量执行管理器
含情绪评估 Agent 的注册与管理
"""

from typing import Dict, Optional, List
import logging

from .emotion_eval_agent import EmotionEvalAgent
from .therapist_agent import TherapistAgent
from .closure_agent import ClosureAgent
from .routine_agent import RoutineAgent
from .honesty_agent import HonestyAgent
from .base import BaseAgent

logger = logging.getLogger(__name__)


class AgentManager:
    """
    智能体管理器：统一初始化、调度和管理所有 Agent
    包含情绪评估 Agent（共 5 个）
    """

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._initialized = False

    def initialize(
        self,
        api_key: str = None,
        base_url: str = None,
        model_id: str = None,
    ) -> bool:
        """
        初始化所有 Agent（含情绪评估 Agent）

        参数:
            api_key: API 密钥
            base_url: API 基础 URL
            model_id: 模型 ID

        返回:
            初始化是否成功
        """
        try:
            # 情绪评估 Agent（批量流程第一步）
            self.agents["emotion_eval"] = EmotionEvalAgent(api_key, base_url, model_id)
            # 四个疗愈 Agent
            self.agents["therapist"] = TherapistAgent(api_key, base_url, model_id)
            self.agents["closure"] = ClosureAgent(api_key, base_url, model_id)
            self.agents["routine"] = RoutineAgent(api_key, base_url, model_id)
            self.agents["honesty"] = HonestyAgent(api_key, base_url, model_id)
            self._initialized = True
            logger.info("所有智能体（含情绪评估）初始化成功")
            return True
        except Exception as e:
            logger.error(f"初始化智能体时出错: {str(e)}")
            return False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        获取指定的 Agent

        参数:
            name: Agent 名称（"emotion_eval"/"therapist"/"closure"/"routine"/"honesty"）

        返回:
            Agent 实例，如果不存在返回 None
        """
        return self.agents.get(name)

    def get_all_agents(self) -> Dict[str, BaseAgent]:
        """获取所有 Agent"""
        return self.agents.copy()

    def run_agent(
        self,
        agent_name: str,
        user_message: str,
        chat_history: list,
        images: Optional[List] = None,
    ) -> Optional[str]:
        """
        执行指定 Agent 的对话

        参数:
            agent_name: Agent 名称
            user_message: 用户消息
            chat_history: 对话历史
            images: 可选图片列表

        返回:
            Agent 回复，不存在返回 None
        """
        agent = self.get_agent(agent_name)
        if agent is None:
            logger.error(f"智能体 '{agent_name}' 未找到")
            return None
        return agent.run(user_message, images)

    def run_agent_once(
        self,
        agent_name: str,
        prompt: str,
        images: Optional[List] = None,
    ) -> Optional[str]:
        """
        单次执行指定 Agent

        参数:
            agent_name: Agent 名称
            prompt: 完整提示词
            images: 可选图片列表

        返回:
            Agent 回复，不存在返回 None
        """
        agent = self.get_agent(agent_name)
        if agent is None:
            logger.error(f"智能体 '{agent_name}' 未找到")
            return None
        return agent.run_once(prompt, images)
