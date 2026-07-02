"""
清醒真话智能体 (Brutal Honesty Agent)
支持多轮对话，使用 Agno 原生记忆
"""

from agno.agent import Agent
from .base import BaseAgent, create_model
from prompts.system_prompts import get_system_prompt


class HonestyAgent(BaseAgent):
    """
    清醒真话智能体：提供直接、客观的反馈和分析

    特性：
    - 多轮对话记忆
    - 具体事件分析
    - 行为动机拆解
    - 观点辩论
    """

    AGENT_TYPE = "honesty"

    def __init__(self, api_key: str = None, base_url: str = None, model_id: str = None):
        model = create_model(api_key, base_url, model_id)

        # 从系统提示词模块获取指令
        instructions = get_system_prompt(self.AGENT_TYPE)

        agent = Agent(
            model=model,
            name="清醒分析师",
            instructions=instructions,
            markdown=True,
        )
        super().__init__(agent, "清醒分析师", self.AGENT_TYPE)
