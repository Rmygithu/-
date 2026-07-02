# prompts 包初始化
# 提示词模板模块

from .system_prompts import get_system_prompt
from .user_templates import get_generate_prompt, get_chat_context_prompt

__all__ = [
    "get_system_prompt",
    "get_generate_prompt",
    "get_chat_context_prompt",
]
