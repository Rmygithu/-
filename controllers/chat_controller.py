"""
对话控制器
负责单 Tab 对话的业务逻辑：状态准备、记忆同步、收尾写入
"""

import streamlit as st
from typing import Generator, Optional

from utils.session_store import SessionStore
from utils.logger import log_info, log_error


class ChatController:
    """
    对话控制器

    职责：
    1. 准备阶段：追加用户消息到历史，标记 generating，保留 pending_input 供 UI 流式消费
    2. 收尾阶段：写入助手回复、清除中间状态、标记就绪
    3. UI 层在渲染阶段消费 pending_input，流式完成后调用 finalize_response

    注意：流式执行本身（for chunk in stream）在 UI 的 _render_streaming_placeholder 中完成，
    不在此处执行，原因是 st.rerun() 不能在 generator 循环中调用（会立刻中断迭代器）。
    """

    @staticmethod
    def prepare_pending_input(agent_type: str) -> bool:
        """
        准备单轮对话的生成状态（不执行流式，只变更状态）

        流程：
        1. 读取 pending_input（若无则直接返回 False）
        2. 将用户消息追加到对话历史
        3. 标记该 Agent 为 generating=True
        4. 保留 pending_input 不清除（UI 层流式时需要读取）

        参数:
            agent_type: Agent 类型

        返回:
            是否有需要处理的待输入
        """
        pending_input = SessionStore.get_pending_input(agent_type)
        if pending_input is None:
            return False

        # 防止重复追加：若历史末尾已是同一条用户消息则跳过
        history = SessionStore.get_chat_history(agent_type)
        if not history or history[-1].get("role") != "user" or history[-1].get("content") != pending_input:
            SessionStore.append_to_history(agent_type, "user", pending_input)

        # 标记生成中（UI 渲染依据此状态决定是否渲染流式占位）
        SessionStore.set_agent_generating(agent_type, True)

        log_info(f"▶ [{agent_type}] 准备流式对话，用户消息已写入历史")
        return True

    @staticmethod
    def finalize_response(agent_type: str, full_response: str):
        """
        单轮对话的收尾处理（在 UI 流式完成后调用）

        流程：
        1. 清除 pending_input
        2. 将完整的助手回复追加到历史
        3. 标记就绪，清除 generating 状态和流式内容
        4. routine 特殊处理：尝试解析7天恢复计划

        参数:
            agent_type: Agent 类型
            full_response: 完整的助手回复文本
        """
        # 清除待处理输入
        SessionStore.clear_pending_input(agent_type)

        # 写入助手回复
        if full_response.strip():
            SessionStore.append_to_history(agent_type, "assistant", full_response)

        # 清除中间状态，标记就绪
        SessionStore.set_agent_generating(agent_type, False)
        SessionStore.clear_agent_streaming_content(agent_type)
        SessionStore.set_agent_ready(agent_type, True)

        # routine 特殊处理：尝试解析7天恢复计划 + 治愈歌单，存入 SessionStore
        if agent_type == "routine":
            from utils.routine_parser import parse_7day_plan
            tasks = parse_7day_plan(full_response)
            if tasks:
                SessionStore.set_routine_tasks(tasks)
                log_info(f"📅 恢复计划解析成功（单聊），共 {len(tasks)} 天")

            from controllers.music_mapper import parse_song_list
            songs = parse_song_list(full_response)
            if songs:
                SessionStore.set_song_list(songs)
                log_info(f"🎵 治愈歌单解析成功（单聊），共 {len(songs)} 首")

        log_info(f"✅ [{agent_type}] 单轮对话完成，回复已写入历史")

    @staticmethod
    def send_message(agent_type: str, user_message: str):
        """
        UI 层发送消息的入口

        只做状态预备：追加用户消息 + 设置 pending_input，然后由 app.py 在下次 rerun
        时调用 prepare_pending_input 完成流式准备。

        参数:
            agent_type: Agent 类型
            user_message: 用户消息
        """
        # 设置待处理输入（供下次渲染时 prepare 读取）
        SessionStore.set_pending_input(agent_type, user_message)
        # 触发重绘（app.py 主循环会检测 pending_input 并调用 prepare_pending_input）
        st.rerun()

    @staticmethod
    def clear_all_history():
        """清除所有对话历史和 Agent 原生记忆"""
        SessionStore.clear_all_history()

        # 清除所有 Agent 的原生 Agno 记忆
        if "agent_manager" in st.session_state:
            agent_manager = st.session_state.agent_manager
            for agent_type in SessionStore.AGENT_ORDER:
                agent = agent_manager.get_agent(agent_type)
                if agent:
                    try:
                        agent.clear_memory()
                    except Exception as e:
                        log_error(f"清除 [{agent_type}] 原生记忆失败: {str(e)}")

        log_info("✅ 已清除所有对话历史和原生记忆")
