"""
流式输出工具
封装 Agno Agent 的流式迭代逻辑，实现打字机效果
"""

import streamlit as st
from typing import Optional
from agno.agent import Agent


def stream_agent_response(
    agent: Agent,
    prompt: str,
    container: st.delta_generator.DeltaGenerator,
    *,
    session_key: Optional[str] = None,
) -> str:
    """
    流式执行 Agent 并实时渲染到 Streamlit 容器

    参数:
        agent: Agno Agent 实例
        prompt: 用户输入
        container: st.empty() 占位容器
        session_key: session_state 中对话历史的 key（可选，传入则自动保存）

    返回:
        完整的响应文本
    """
    full_response = ""

    # 使用 Agno 原生流式接口
    run_response = agent.run(prompt, stream=True)

    for chunk in run_response:
        # 检查 chunk 是否有 content 属性且不为空
        content = getattr(chunk, 'content', None)
        if content:
            full_response += content
            # 增量更新 Markdown 内容
            container.markdown(full_response)

    # 保存到对话历史
    if session_key and session_key in st.session_state:
        st.session_state[session_key].append({
            "role": "assistant",
            "content": full_response
        })

    return full_response


def stream_agent_with_context(
    agent: Agent,
    prompt: str,
    container: st.delta_generator.DeltaGenerator,
    *,
    session_key: Optional[str] = None,
    history: list = None,
) -> str:
    """
    带上下文的流式执行

    参数:
        agent: Agno Agent 实例
        prompt: 用户输入（不含历史上下文）
        container: st.empty() 占位容器
        session_key: session_state 中对话历史的 key（可选）
        history: 对话历史列表

    返回:
        完整的响应文本
    """
    # 构建带历史上下文的完整 prompt
    if history and len(history) > 0:
        context_parts = []
        for msg in history[-10:]:  # 最近 10 条
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg.get("content", "")
            if content:
                context_parts.append(f"{role}: {content}")

        full_prompt = f"""之前的对话：
{chr(10).join(context_parts)}

用户的当前消息：{prompt}
请基于以上对话历史，回应用户的当前消息。使用中文回复。"""
    else:
        full_prompt = prompt

    return stream_agent_response(
        agent=agent,
        prompt=full_prompt,
        container=container,
        session_key=session_key,
    )
