"""
多 Tab 独立聊天窗口
纯渲染层：根据状态渲染页面，流式占位层负责消费生成器并实时更新 UI

架构说明
--------
流式执行必须在渲染阶段（同一次 Streamlit 运行周期内）完成，原因：
  st.rerun() 会立刻抛出 RerunException，中断任何正在运行的迭代器。
  因此绝不能在 for chunk in stream 循环中调用 st.rerun()。

正确模式：
  1. Controller 的 prepare_* 方法只设置状态（is_generating=True），
     不实际执行流式循环。
  2. 渲染阶段检测到 is_generating=True 时，从 Controller 获取 stream
     generator，用 st.empty() 占位符原地更新，循环自然完成。
  3. 循环结束后调用 Controller 的 finalize_* 方法写入历史、清除状态。
  4. 最后调用一次 st.rerun() 刷新最终状态。
"""

import streamlit as st

from config.constants import TAB_NAMES, TAB_SUBTITLES, EMOTION_TYPE_ICONS, BREAKUP_TYPE_ICONS, INTENSITY_LEVEL
from utils.session_store import SessionStore
from utils.logger import log_error
from controllers.chat_controller import ChatController
from controllers.batch_controller import BatchController


def render_chat_tabs():
    """
    渲染多 Tab 独立聊天窗口（统一入口）

    Tabs 全程常驻，永远正常显示，不变灰、不消失。
    加载状态只作用于 Tab 内部内容区域。
    """
    tab1, tab2, tab3, tab4 = st.tabs(list(TAB_NAMES.values()))

    tab_configs = [
        (tab1, "therapist"),
        (tab2, "closure"),
        (tab3, "routine"),
        (tab4, "honesty"),
    ]

    for tab, agent_type in tab_configs:
        with tab:
            _render_single_tab(agent_type)


def _render_single_tab(agent_type: str):
    """
    渲染单个 Tab 的聊天界面

    三层渲染架构：
    1. 历史消息层：固定，只渲染已完成的历史消息
    2. 流式占位层：仅 is_generating=True 时出现，在此层完成流式循环
    3. 输入框层：仅 should_show_input=True 时显示，生成中完全隐藏

    routine Tab 额外渲染：历史层之前显示结构化7天计划表格（若已生成）

    参数:
        agent_type: Agent 类型
    """
    is_generating = SessionStore.is_agent_generating(agent_type)

    # ===== 特殊：routine Tab 顶部渲染结构化表格 + 治愈歌单 =====
    if agent_type == "routine":
        _render_routine_table()
        _render_music_player()

    # ===== 第一层：历史消息（固定，不含正在生成的内容）=====
    _render_history(agent_type)

    # ===== 第二层：流式占位（生成中才有，完成后消失）=====
    if is_generating:
        _render_streaming_placeholder(agent_type)

    # ===== 第三层：输入框（生成完成后才显示，生成中完全隐藏）=====
    elif SessionStore.should_show_input(agent_type):
        _render_input_area(agent_type)


def _render_music_player():
    """
    渲染治愈歌单链接列表

    每首歌显示为可点击链接，点击后跳转到网易云音乐搜索结果页面，
    用户可在音乐平台自行试听。

    降级逻辑：
    - 无歌单数据：静默不渲染
    """
    if not SessionStore.has_song_list():
        return

    songs = SessionStore.get_song_list()

    st.markdown("#### 🎵 治愈歌单")
    st.caption("点击歌名跳转网易云音乐搜索，在线试听")

    for i, song in enumerate(songs, start=1):
        title = song.get("title", "")
        artist = song.get("artist", "")
        search_url = song.get("search_url", "")

        # 显示歌名和歌手
        display_text = f"{title}"
        if artist:
            display_text += f" — {artist}"

        # 渲染为可点击链接（Markdown 语法）
        st.markdown(
            f"{i}. [{display_text}]({search_url}) 🎧",
            unsafe_allow_html=False,
        )


def _render_routine_table():
    """
    渲染恢复规划结构化表格（7天计划）

    仅在 SessionStore 中存有解析后的任务数据时渲染，
    展示在 routine Tab 顶部，聊天历史之前。
    使用 st.dataframe 展示，列：天数 / 主题 / 任务1 / 任务2 / 任务3。
    """
    if not SessionStore.has_routine_tasks():
        return

    tasks = SessionStore.get_routine_tasks()

    import pandas as pd

    rows = []
    for t in tasks:
        task_list = t.get("tasks", [])
        rows.append({
            "天数":  f"第{t['day']}天",
            "主题":  t.get("theme", ""),
            "任务1": task_list[0] if len(task_list) > 0 else "",
            "任务2": task_list[1] if len(task_list) > 1 else "",
            "任务3": task_list[2] if len(task_list) > 2 else "",
        })

    df = pd.DataFrame(rows)

    st.markdown("#### 📅 七天恢复计划总览")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "天数":  st.column_config.TextColumn("天数",  width="small"),
            "主题":  st.column_config.TextColumn("主题",  width="medium"),
            "任务1": st.column_config.TextColumn("任务1", width="large"),
            "任务2": st.column_config.TextColumn("任务2", width="large"),
            "任务3": st.column_config.TextColumn("任务3", width="large"),
        },
    )
    st.divider()


def _render_history(agent_type: str):
    """
    渲染历史消息层（已完成的对话，固定不变）

    参数:
        agent_type: Agent 类型
    """
    chat_history = SessionStore.get_chat_history(agent_type)
    for msg in chat_history:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").markdown(msg["content"])


def _render_streaming_placeholder(agent_type: str):
    """
    流式占位层：在此层执行真正的流式生成循环

    步骤：
    1. 根据上下文（批量生成 or 单聊）获取流式生成器
    2. 用 st.empty() 在 chat_message 容器内原地累积显示内容
    3. 循环自然结束后，调用 Controller 收尾（写历史、清状态）
    4. 最后 st.rerun() 一次，刷新为最终展示状态

    参数:
        agent_type: Agent 类型
    """
    agent_manager = st.session_state.get("agent_manager")
    if agent_manager is None:
        st.error("⚠️ Agent 管理器未初始化，请刷新页面重试")
        return

    agent = agent_manager.get_agent(agent_type)
    if agent is None:
        st.error(f"⚠️ Agent '{agent_type}' 未找到")
        return

    # ---- 获取流式生成器 ----
    stream = None
    is_batch = SessionStore.is_batch_generating()

    try:
        if is_batch:
            # 批量模式：从 BatchController 获取当前 Agent 的 stream
            _agent_type, stream = BatchController.get_current_agent_stream()
            if _agent_type != agent_type:
                # 不是当前批量处理的 Agent，跳过
                return
        else:
            # 单聊模式：从 ChatController 获取 pending stream
            pending_input = SessionStore.get_pending_input(agent_type)
            if pending_input is None:
                # pending_input 已被消费或不存在，不渲染
                return
            stream = agent.stream_chat(pending_input)

    except Exception as e:
        log_error(f"[{agent_type}] 获取流式生成器失败: {str(e)}")
        _finalize_with_error(agent_type, is_batch, f"⚠️ 连接 AI 时出错：{str(e)}")
        return

    # ---- 流式渲染循环（在一次 Streamlit 运行周期内完成）----
    full_text = ""
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.info("⏳ 正在生成中，请稍候...")

        if stream is not None:
            try:
                for chunk in stream:
                    content = getattr(chunk, "content", None)
                    if content:
                        full_text += content
                        # 原地更新，不触发 rerun
                        placeholder.markdown(full_text)
            except Exception as e:
                log_error(f"[{agent_type}] 流式生成中断: {str(e)}")
                if not full_text:
                    full_text = f"⚠️ 生成过程中出现错误，请重试。（错误：{str(e)}）"
                placeholder.markdown(full_text)
        else:
            full_text = "⚠️ 无法连接 AI 服务，请检查 API Key 后重试。"
            placeholder.markdown(full_text)

    # ---- 流式完成后的收尾处理 ----
    if is_batch:
        BatchController.finalize_batch_step(agent_type, full_text)
    else:
        ChatController.finalize_response(agent_type, full_text)

    # 刷新页面：批量模式会进入下一个 Agent 的准备阶段，单聊模式显示输入框
    st.rerun()


def _finalize_with_error(agent_type: str, is_batch: bool, error_msg: str):
    """
    异常时的统一收尾处理

    参数:
        agent_type: Agent 类型
        is_batch: 是否批量模式
        error_msg: 错误提示消息
    """
    st.error(error_msg)
    if is_batch:
        BatchController.finalize_batch_step(agent_type, error_msg)
    else:
        ChatController.finalize_response(agent_type, error_msg)
    st.rerun()


def _render_input_area(agent_type: str):
    """
    渲染输入框层（仅生成完成后显示）

    用户发送消息后，只调用 SessionStore.set_pending_input + st.rerun()，
    不执行任何业务逻辑（业务逻辑在下次 rerun 时由 app.py 主循环处理）。

    参数:
        agent_type: Agent 类型
    """
    agent_name = TAB_SUBTITLES.get(agent_type, agent_type)
    placeholder_text = f"继续与{agent_name}对话..."

    if chat_input := st.chat_input(placeholder_text, key=f"{agent_type}_input"):
        # 纯状态写入，不做业务处理
        SessionStore.set_pending_input(agent_type, chat_input)
        st.rerun()


def render_emotion_eval_runner():
    """
    情绪评估静默执行层

    当批量生成当前步骤为 emotion_eval 时，静默消费流式输出并完成收尾。
    不在任何 Tab 中展示，只显示 spinner 进度提示。
    必须在 render_chat_tabs() 之前调用，保证状态机能推进到 step 1。
    """
    if not SessionStore.is_batch_generating():
        return

    current_agent_type = SessionStore.get_batch_current_agent_type()
    if current_agent_type != "emotion_eval":
        return

    agent_manager = st.session_state.get("agent_manager")
    if agent_manager is None:
        log_error("[emotion_eval] AgentManager 未初始化，跳过静默评估")
        return

    # 获取流式生成器（内部会构造 emotion_eval 专用 prompt）
    _agent_type, stream = BatchController.get_current_agent_stream()
    if _agent_type != "emotion_eval":
        return

    # 静默消费流：只显示 spinner，不把原始键值对暴露给用户
    full_text = ""
    with st.spinner("🧠 正在分析情绪状态，请稍候..."):
        if stream is not None:
            try:
                for chunk in stream:
                    content = getattr(chunk, "content", None)
                    if content:
                        full_text += content
            except Exception as e:
                log_error(f"[emotion_eval] 流式生成中断: {str(e)}")
        else:
            log_error("[emotion_eval] 无法获取流式生成器，将以空结果收尾")

    # 收尾：解析键值对 → 存入 SessionStore → 推进状态机到 step 1
    BatchController.finalize_batch_step("emotion_eval", full_text)
    st.rerun()


def render_batch_progress():
    """
    渲染批量生成进度提示（Tabs 上方）

    格式：⏳ 正在生成 2/4 · 告别释怀...
    未在批量生成时不渲染任何内容。
    """
    if not SessionStore.is_batch_generating():
        return

    current_index = SessionStore.get_batch_current_index()
    current_agent_type = SessionStore.get_batch_current_agent_type()
    if current_agent_type is None:
        return

    total = len(SessionStore.AGENT_ORDER)
    agent_names = {
        "therapist": "情绪疗愈",
        "closure": "告别释怀",
        "routine": "恢复规划",
        "honesty": "清醒真话",
    }
    name = agent_names.get(current_agent_type, current_agent_type)
    st.info(f"⏳ 正在生成 {current_index + 1}/{total} · {name}...")


def render_tip_message():
    """渲染提示信息（输入区下方、Tabs 上方）"""
    st.markdown("💡 **提示**：你也可以在下方的选项卡中与每个智能体单独对话。")


def render_emotion_eval_card():
    """
    渲染情绪评估结果卡片（评估完成后常驻展示）

    数据来源：SessionStore.get_emotion_eval_result()
    仅当评估结果存在时渲染，否则静默不显示。
    """
    if not SessionStore.has_emotion_eval_result():
        return

    result = SessionStore.get_emotion_eval_result()
    if not result:
        return

    emotion_type = result.get("emotion_type", "未知")
    intensity = result.get("intensity", 0)
    core_pain = result.get("core_pain", "")
    breakup_type = result.get("breakup_type", "未知")
    suggestion = result.get("suggestion", "")

    # 情绪烈度等级判断
    if intensity >= INTENSITY_LEVEL["high"][0]:
        intensity_label = "高烈度"
        intensity_color = "🔴"
    elif intensity >= INTENSITY_LEVEL["mid"][0]:
        intensity_label = "中烈度"
        intensity_color = "🟡"
    else:
        intensity_label = "低烈度"
        intensity_color = "🟢"

    emotion_icon = EMOTION_TYPE_ICONS.get(emotion_type, "💭")
    breakup_icon = BREAKUP_TYPE_ICONS.get(breakup_type, "💔")

    with st.expander("📊 情绪评估报告", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="情绪类型", value=f"{emotion_icon} {emotion_type}")
        with col2:
            st.metric(label="情绪烈度", value=f"{intensity_color} {intensity}/10", delta=intensity_label)
        with col3:
            st.metric(label="分手类型", value=f"{breakup_icon} {breakup_type}")

        if core_pain:
            st.markdown(f"**核心痛点**：{core_pain}")
        if suggestion:
            st.markdown(f"**适配建议**：{suggestion}")
