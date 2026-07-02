"""
恢复规划智能体 (Routine Planner Agent)
支持多轮对话，使用 Agno 原生记忆
"""

from agno.agent import Agent
from .base import BaseAgent, create_model
from prompts.system_prompts import get_system_prompt


class RoutineAgent(BaseAgent):
    """
    恢复规划智能体：设计 7 天恢复计划、提供实用建议

    特性：
    - 多轮对话记忆
    - 任务细化
    - 活动替换
    - 歌单影单定制
    """

    AGENT_TYPE = "routine"

    def __init__(self, api_key: str = None, base_url: str = None, model_id: str = None):
        model = create_model(api_key, base_url, model_id)

        # 从系统提示词模块获取指令
        instructions = get_system_prompt(self.AGENT_TYPE)

        agent = Agent(
            model=model,
            name="恢复规划师",
            instructions=instructions,
            markdown=True,
        )
        super().__init__(agent, "恢复规划师", self.AGENT_TYPE)
