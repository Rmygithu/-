"""
告别释怀智能体 (Closure Agent)
支持多轮对话，使用 Agno 原生记忆
"""

from agno.agent import Agent
from .base import BaseAgent, create_model
from prompts.system_prompts import get_system_prompt


class ClosureAgent(BaseAgent):
    """
    告别释怀智能体：帮助用户表达未发送的情感、获得 closure

    特性：
    - 多轮对话记忆
    - 多版本信件修改
    - 语气调整
    - 断联话术生成
    """

    AGENT_TYPE = "closure"

    def __init__(self, api_key: str = None, base_url: str = None, model_id: str = None):
        model = create_model(api_key, base_url, model_id)

        # 从系统提示词模块获取指令
        instructions = get_system_prompt(self.AGENT_TYPE)

        agent = Agent(
            model=model,
            name="释怀专家",
            instructions=instructions,
            markdown=True,
        )
        super().__init__(agent, "释怀专家", self.AGENT_TYPE)
