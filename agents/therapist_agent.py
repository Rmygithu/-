"""
共情疗愈智能体 (Therapist Agent)
支持多轮对话，使用 Agno 原生记忆
"""

from agno.agent import Agent
from .base import BaseAgent, create_model
from prompts.system_prompts import get_system_prompt


class TherapistAgent(BaseAgent):
    """
    共情疗愈智能体：提供情感支持、倾听和安慰

    特性：
    - 多轮对话记忆
    - 正念呼吸引导
    - 情绪拆解
    - 认知调整
    """

    AGENT_TYPE = "therapist"

    def __init__(self, api_key: str = None, base_url: str = None, model_id: str = None):
        model = create_model(api_key, base_url, model_id)

        # 从系统提示词模块获取指令
        instructions = get_system_prompt(self.AGENT_TYPE)

        agent = Agent(
            model=model,
            name="共情疗愈师",
            instructions=instructions,
            markdown=True,
        )
        super().__init__(agent, "共情疗愈师", self.AGENT_TYPE)
