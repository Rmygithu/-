"""
侧边栏配置面板
配置项分组清晰，说明文案温暖简洁
"""

import os
import streamlit as st
from config.constants import MIMO_BASE_URL, MIMO_MODEL_ID
from utils.session_store import SessionStore
from ui.common import trigger_fireworks


def render_sidebar() -> dict:
    """
    渲染侧边栏配置面板

    返回:
        配置字典，包含 api_key, base_url, model_id
    """
    with st.sidebar:
        st.markdown("## 💝 心愈 AI")
        st.caption("HeartHeal AI · 分手情绪疗愈系统")
        st.divider()

        # ---- API 配置 ----
        st.markdown("### 🔑 API 配置")

        # 优先从环境变量读取默认值
        default_api_key = os.getenv("MIMO_API_KEY", "")

        api_key = st.text_input(
            "MiMo API Key",
            value=default_api_key,
            type="password",
            help="填写你的小米 MiMo API Key，用于驱动所有疗愈助手",
            key="api_key_widget",
        )

        # 同步到 SessionStore（Key 变更时重置 Agent 初始化状态）
        if api_key != st.session_state.get("api_key_input", ""):
            st.session_state.api_key_input = api_key
            st.session_state.agents_initialized = False

        if api_key:
            st.success("✅ API Key 已配置")
        else:
            st.warning("⚠️ 请先填写 API Key 才能使用")

        # ---- 高级配置（折叠）----
        with st.expander("⚙️ 高级配置（可选）"):
            base_url = st.text_input(
                "API 地址",
                value=MIMO_BASE_URL,
                help="默认为小米 MiMo 官方接口地址，一般无需修改",
            )
            model_id = st.text_input(
                "模型名称",
                value=MIMO_MODEL_ID,
                help="使用的模型版本，默认 mimo-v2.5-pro",
            )

        st.divider()

        # ---- 模型说明 ----
        st.markdown("### 🤖 关于 MiMo 模型")
        st.markdown("""
- **专注推理与理解**，擅长情感分析
- 7B 参数，响应迅速
- 支持中文多轮长对话
        """)

        st.divider()

        # ---- 恢复进度面板 ----
        st.markdown("### 📊 恢复进度")
        _render_task_progress_panel()

        st.divider()

        # ---- 操作区 ----
        st.markdown("### 🗂️ 操作")
        if st.button("🗑️ 清空全部对话", type="secondary", use_container_width=True):
            # 同时清除 Agno 原生记忆
            if "agent_manager" in st.session_state:
                from utils.logger import log_error
                agent_manager = st.session_state.agent_manager
                for agent_type in SessionStore.AGENT_ORDER:
                    agent = agent_manager.get_agent(agent_type)
                    if agent:
                        try:
                            agent.clear_memory()
                        except Exception as e:
                            log_error(f"清除 [{agent_type}] 原生记忆失败: {str(e)}")
            SessionStore.clear_all_history()
            st.rerun()

        st.caption("清空后所有对话记录与情绪评估结果将同步重置")

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model_id": model_id,
    }


def _render_task_progress_panel():
    """
    渲染恢复进度面板

    布局：
    - 无计划时：占位提示
    - 有计划时：进度条 + 完成文字 + 按天分组的可折叠任务复选框
    每次勾选/取消勾选后写入 SessionStore 并触发 st.rerun()，
    首次达到100%时触发气球特效。
    """
    if not SessionStore.has_routine_tasks():
        st.caption("📝 生成恢复计划后即可打卡")
        return

    tasks = SessionStore.get_routine_tasks()
    done, total = SessionStore.get_task_progress()

    # ---- 进度条 ----
    pct = done / total if total > 0 else 0.0
    st.progress(pct)
    st.caption(f"已完成 {done}/{total}・{int(pct * 100)}%")

    # ---- 首次100%达成：触发气球特效 ----
    if done == total and total > 0 and not SessionStore.is_tasks_celebrated():
        st.balloons()
        trigger_fireworks()
        SessionStore.set_tasks_celebrated(True)

    # ---- 按天分组的任务复选框 ----
    checked_state = SessionStore.get_task_checked()
    state_changed = False

    for day_data in tasks:
        day = day_data["day"]
        theme = day_data.get("theme", "")
        day_tasks = day_data.get("tasks", [])

        with st.expander(f"第{day}天 · {theme}", expanded=False):
            for i, task_text in enumerate(day_tasks):
                task_key = f"{day}-{i}"
                is_checked = checked_state.get(task_key, False)

                # 复选框 + 自定义样式标签（两列布局）
                col_cb, col_label = st.columns([0.12, 0.88])
                with col_cb:
                    new_val = st.checkbox(
                        task_text,
                        value=is_checked,
                        key=f"sidebar_task_{task_key}",
                        label_visibility="collapsed",
                    )
                with col_label:
                    if new_val:
                        st.markdown(
                            f"<span class='task-done'>{task_text}</span>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<span class='task-item'>{task_text}</span>",
                            unsafe_allow_html=True,
                        )

                if new_val != is_checked:
                    SessionStore.set_task_checked(task_key, new_val)
                    state_changed = True

    if state_changed:
        st.rerun()
