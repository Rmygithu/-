"""
心愈 AI・分手情绪疗愈系统 - 主入口
基于多智能体协作的情绪疗愈支持平台

职责：
1. 页面初始化（含情绪评估新节点）
2. 状态分发（Controller prepare → 渲染层消费）
3. 组件组合（顺序：侧边栏 → 标题 → 主内容区 → 页脚）
"""

import streamlit as st

# 页面配置（必须是第一个 st 调用）
st.set_page_config(
    page_title="心愈 AI・分手情绪疗愈系统",
    page_icon="💝",
    layout="wide",
)

# 导入模块
from agents.manager import AgentManager
from controllers.batch_controller import BatchController
from controllers.chat_controller import ChatController
from utils.session_store import SessionStore
from utils.validators import validate_input
from ui.sidebar import render_sidebar
from ui.input_area import render_input_area
from ui.chat_tabs import render_chat_tabs, render_batch_progress, render_tip_message, render_emotion_eval_card, render_emotion_eval_runner
from ui.common import (
    render_header,
    render_footer,
    render_generate_button,
    render_success_message,
    render_warning_message,
    inject_custom_css,
    trigger_fireworks,
)


def main():
    """
    主函数：页面初始化 → 状态分发 → UI 渲染

    关键设计：
    - 状态分发（prepare_*）必须在 UI 渲染（render_*）之前完成
    - prepare_* 方法只更改 session_state，不执行流式循环
    - 流式循环在 UI 渲染阶段（_render_streaming_placeholder）中完成
    - 情绪评估 Agent 作为批量流程的第 0 步，先评估后适配
    """

    # ========== 1. 初始化 ==========
    SessionStore.init_session_state()

    # 注入全局自定义 CSS（任务划线动效等）
    inject_custom_css()

    if "agent_manager" not in st.session_state:
        st.session_state.agent_manager = AgentManager()

    # ========== 2. 渲染侧边栏 ==========
    config = render_sidebar()

    # ========== 3. 渲染标题 ==========
    render_header()

    # ========== 4. 检查 API Key ==========
    api_key = SessionStore.get_api_key()
    if not api_key:
        st.info("💡 请先在左侧边栏填写 API Key，即可开始使用")
        render_footer()
        return

    # ========== 5. 懒加载 Agent ==========
    if not SessionStore.is_agents_initialized():
        base_url = config.get("base_url")
        model_id = config.get("model_id")

        with st.spinner("🌱 正在加载疗愈助手，请稍候..."):
            success = st.session_state.agent_manager.initialize(
                api_key=api_key,
                base_url=base_url,
                model_id=model_id,
            )
        if success:
            SessionStore.set_agents_initialized(True)
        else:
            st.error("💔 助手加载失败，请检查 API Key 是否正确后刷新重试")
            return

    # ========== 6. 状态分发 ==========
    if SessionStore.is_batch_generating():
        # 批量生成进行中：为当前步骤准备状态
        BatchController.prepare_current_agent()
    else:
        # 单 Tab 对话：检查每个 Agent 是否有待处理输入
        for agent_type in SessionStore.AGENT_ORDER:
            if SessionStore.get_pending_input(agent_type) is not None:
                ChatController.prepare_pending_input(agent_type)

    # ========== 7. 渲染主内容区 ==========
    _render_main_content()

    # ========== 8. 渲染页脚 ==========
    render_footer()


def _render_main_content():
    """渲染主内容区"""

    # 批量生成已完成：成功提示 + 气球特效（首次触发）+ 重新生成按钮
    if SessionStore.is_batch_completed():
        render_success_message("✅ 你的专属疗愈方案已生成完毕！可在下方各标签页中继续与 AI 对话。")
        # 首次完成时触发气球特效，避免重复触发
        if not SessionStore.is_batch_celebrated():
            st.balloons()
            trigger_fireworks()
            SessionStore.set_batch_celebrated(True)
        if st.button("🔄 重新生成方案"):
            SessionStore.reset_batch()
            st.rerun()

    # 正常模式：输入区 + 一键生成按钮（生成中隐藏，避免误触）
    if not SessionStore.is_batch_generating():
        user_input = render_input_area()

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if render_generate_button():
                is_valid, error_msg = validate_input(user_input)
                if not is_valid:
                    render_warning_message(error_msg)
                else:
                    BatchController.start_batch(user_input)
                    st.rerun()

    # step 0 静默执行层：emotion_eval 无 Tab，在此消费流并推进状态机
    render_emotion_eval_runner()

    # 提示信息
    render_tip_message()

    # 情绪评估结果卡片（评估完成后常驻展示）
    render_emotion_eval_card()

    # 批量生成进度（Tabs 上方）
    render_batch_progress()

    # Tabs（全程常驻，永不变灰）
    render_chat_tabs()


if __name__ == "__main__":
    main()
