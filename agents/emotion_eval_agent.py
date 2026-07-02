"""
情绪评估智能体 (Emotion Eval Agent)
批量流程的第一步，先于所有疗愈 Agent 执行

职责：
- 接收用户情感描述
- 输出结构化情绪评估报告（固定键值对格式）
- 结果存入 SessionStore，供后续 4 个 Agent 动态适配
"""

from agno.agent import Agent
from .base import BaseAgent, create_model
from prompts.system_prompts import get_system_prompt


class EmotionEvalAgent(BaseAgent):
    """
    情绪评估智能体：分析用户情绪状态，输出结构化评估报告

    特性：
    - 不面向用户直接展示，只做评估
    - 固定键值对输出格式（情绪类型 / 情绪烈度 / 核心痛点 / 分手类型 / 适配建议）
    - 评估结果持久化存储，供后续所有疗愈 Agent 参考
    """

    AGENT_TYPE = "emotion_eval"

    def __init__(self, api_key: str = None, base_url: str = None, model_id: str = None):
        model = create_model(api_key, base_url, model_id)

        # 从系统提示词模块获取指令
        instructions = get_system_prompt(self.AGENT_TYPE)

        # markdown=False，避免在纯文本键值对中引入 Markdown 干扰解析
        agent = Agent(
            model=model,
            name="情绪评估师",
            instructions=instructions,
            markdown=False,
        )
        super().__init__(agent, "情绪评估师", self.AGENT_TYPE)
