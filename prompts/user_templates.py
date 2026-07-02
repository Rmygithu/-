"""
用户输入组装模板、一键生成提示词
支持多轮对话场景，支持情绪评估上下文注入
"""

from typing import Optional, Dict, Any


# ─────────────────────────────────────────────────────────────────────────────
# 情绪上下文注入工具函数
# ─────────────────────────────────────────────────────────────────────────────

def _build_emotion_context_block(emotion_eval_result: Optional[Dict[str, Any]]) -> str:
    """
    将情绪评估结果组装为可注入提示词的上下文块

    参数:
        emotion_eval_result: SessionStore.get_emotion_eval_result() 的返回值

    返回:
        格式化的上下文字符串，若无评估结果则返回空字符串
    """
    if not emotion_eval_result:
        return ""

    emotion_type  = emotion_eval_result.get("emotion_type",  "")
    intensity     = emotion_eval_result.get("intensity",     "")
    core_pain     = emotion_eval_result.get("core_pain",     "")
    breakup_type  = emotion_eval_result.get("breakup_type",  "")
    suggestion    = emotion_eval_result.get("suggestion",    "")

    # 只有字段完整才注入，避免半成品干扰 Agent
    if not all([emotion_type, intensity, core_pain, breakup_type]):
        return ""

    intensity_label = _get_intensity_label(int(intensity) if str(intensity).isdigit() else 5)

    block = f"""
---
**【情绪评估上下文 — 请严格参考，不要对用户重复这段描述】**
- 当前主导情绪：**{emotion_type}**（烈度 {intensity}/10，属于{intensity_label}）
- 核心痛点：{core_pain}
- 分手类型：{breakup_type}
- 适配建议：{suggestion}
---
"""
    return block.strip()


def _get_intensity_label(intensity: int) -> str:
    """
    将情绪烈度数值转换为可读标签

    参数:
        intensity: 1-10 的整数

    返回:
        如 "高强度"、"中等强度"、"低强度"
    """
    if intensity >= 8:
        return "高强度，需要更多包容与稳定支持"
    elif intensity >= 5:
        return "中等强度，可适当引导理性思考"
    else:
        return "低强度，可更直接地讨论恢复与成长"


# ─────────────────────────────────────────────────────────────────────────────
# 一键生成主提示词
# ─────────────────────────────────────────────────────────────────────────────

def get_generate_prompt(
    agent_type: str,
    user_input: str,
    emotion_eval_result: Optional[Dict[str, Any]] = None,
) -> str:
    """
    获取一键生成场景的提示词

    所有 Agent 统一风格：结构化输出、Markdown 格式、内容饱满、末尾引导提问。
    当传入情绪评估结果时，自动注入上下文块，让 Agent 的回复更贴合用户实际状态。

    参数:
        agent_type:          Agent 类型（therapist / closure / routine / honesty）
        user_input:          用户原始输入
        emotion_eval_result: 情绪评估结果字典（可选），来自 SessionStore.get_emotion_eval_result()

    返回:
        完整的提示词字符串
    """
    emotion_ctx = _build_emotion_context_block(emotion_eval_result)
    # 若有评估上下文，在用户描述之后换行附加
    ctx_suffix = f"\n\n{emotion_ctx}" if emotion_ctx else ""

    prompts = {
        "therapist": f"""
用户的情感描述：{user_input}{ctx_suffix}

请作为共情疗愈师，给予用户温暖的支持和理解。

**输出要求（必须严格遵守）：**
1. 使用标准 Markdown 格式排版，关键内容**加粗**，合理使用小标题、分点列表
2. 回复内容必须饱满有深度，至少 3-4 个段落
3. 可适当使用 emoji 点缀标题和重点
4. 每轮回复的末尾，必须自然提出 1 个开放式引导问题
5. 若有情绪评估上下文，请据此调整共情力度与回复重心，但**不要对用户念出评估结论**

**内容结构：**
1. 先对用户的感受表示理解和验证（2-3 句话）
2. 分享一个相关的情感共鸣点或专业见解
3. 给予具体的安慰和鼓励
4. 最后用一个温和的问题引导用户继续倾诉

请使用中文回复。
""",
        "closure": f"""
用户的情感描述：{user_input}{ctx_suffix}

请作为释怀专家，帮助用户开始释怀的过程。

**输出要求（必须严格遵守）：**
1. 使用标准 Markdown 格式排版，关键内容**加粗**，合理使用小标题、分点列表
2. 回复内容必须饱满有深度，至少 3-4 个段落
3. 可适当使用 emoji 点缀标题和重点
4. 每轮回复的末尾，必须自然提出 1 个开放式引导问题
5. 若有情绪评估上下文，请据此调整信件基调（如愤怒型应引导宣泄，悲伤型应引导接受），但**不要对用户念出评估结论**

**内容结构：**
1. 先理解用户想表达的核心情感（2-3 句话）
2. 提供一个「未发送的信」的开头模板（3-4 句）
3. 分享一些释怀的方法或建议
4. 最后用一个问题引导用户继续完善这封信

请使用中文回复。
""",
        "routine": f"""
用户的情感状态：{user_input}{ctx_suffix}

请作为恢复规划师，为用户生成一套完整的 **7 天恢复计划**，帮助他重建生活节奏。

**输出要求（必须严格遵守）：**
1. 先用 2-3 句话肯定用户想要改变的意愿，给予温暖的开场
2. 若有情绪评估上下文，请据此调整任务难度（高烈度用户给更轻量的任务，低烈度可适当进阶），但**不要对用户念出评估结论**
3. 输出完整的 7 天恢复计划，**严格按照以下固定格式**，每天包含标题和 3 项任务：

**第1天 · 主题名称**
- 任务1：具体可执行的任务描述
- 任务2：具体可执行的任务描述
- 任务3：具体可执行的任务描述

**第2天 · 主题名称**
- 任务1：...
- 任务2：...
- 任务3：...

（第3天到第7天，格式完全一致，共7天，一天不少）

4. 7天计划全部输出完后，**紧接着**输出一份治愈歌单，格式如下（严格遵守，不可缺少）：

🎵 治愈歌单
1. 歌曲名称 - 歌手名
2. 歌曲名称 - 歌手名
3. 歌曲名称 - 歌手名
4. 歌曲名称 - 歌手名
5. 歌曲名称 - 歌手名

（推荐轻钢琴、氛围音乐、治愈系华语流行；只输出歌名和歌手，不输出链接或HTML）

5. 歌单之后，补充 2-3 句温暖的鼓励语，并以一个开放式引导问题收尾
6. 可适当使用 emoji 点缀标题，提升可读性

请使用中文回复。
""",
        "honesty": f"""
用户的情况：{user_input}{ctx_suffix}

请作为清醒分析师，帮用户理性看待这段关系。

**输出要求（必须严格遵守）：**
1. 使用标准 Markdown 格式排版，关键内容**加粗**，合理使用小标题、分点列表
2. 回复内容必须饱满有深度，至少 3-4 个段落
3. 可适当使用 emoji 点缀标题和重点
4. 每轮回复的末尾，必须自然提出 1 个开放式引导问题
5. 若有情绪评估上下文，请据此选择切入角度（如"被分手"侧重自我价值，"主动分手"侧重决策确认），但**不要对用户念出评估结论**

**内容结构：**
1. 先简要分析用户描述中的关键点（2-3 句话）
2. 指出 1-2 个值得思考的角度
3. 给出一些理性的建议或观点
4. 最后问用户想深入聊哪个方面

请使用中文回复。
""",
    }
    return prompts.get(agent_type, user_input)


# ─────────────────────────────────────────────────────────────────────────────
# 情绪评估专用提示词（step 0，不面向用户展示）
# ─────────────────────────────────────────────────────────────────────────────

def get_emotion_eval_prompt(user_input: str) -> str:
    """
    构建情绪评估的请求提示词

    输出必须是固定键值对，BatchController 会解析它写入 SessionStore。

    参数:
        user_input: 用户原始输入

    返回:
        完整的评估请求提示词
    """
    return f"""请分析以下分手描述，输出结构化情绪评估报告。

用户描述：{user_input}

输出格式要求（必须严格遵守，每行一个键值对，键名固定，不要多余解释）：
情绪类型: <悲伤|愤怒|不甘|释然|焦虑 中选一个>
情绪烈度: <1-10 的整数>
核心痛点: <一句话描述>
分手类型: <被分手|主动分手|和平分手|暧昧拉扯 中选一个>
适配建议: <给后续 Agent 的一句调整方向>
"""


# ─────────────────────────────────────────────────────────────────────────────
# 多轮对话上下文构建（单 Tab 聊天场景）
# ─────────────────────────────────────────────────────────────────────────────

def get_chat_context_prompt(chat_history: list, user_message: str) -> str:
    """
    构建包含历史上下文的对话提示词

    参数:
        chat_history: 对话历史列表
        user_message: 用户当前消息

    返回:
        完整的提示词
    """
    context_parts = []
    for msg in chat_history:
        role = "用户" if msg["role"] == "user" else "助手"
        context_parts.append(f"{role}: {msg['content']}")

    if context_parts:
        return f"""之前的对话：
{chr(10).join(context_parts)}

用户的当前消息：{user_message}

请基于以上对话历史，回应用户的当前消息。使用中文回复。"""
    else:
        return user_message
