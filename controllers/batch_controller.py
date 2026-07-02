"""
批量生成控制器
负责一键生成的业务逻辑：状态准备、单步推进、收尾写入

5 步状态机：
  Step 0 — emotion_eval：静默运行，输出键值对，解析后存入 SessionStore
  Step 1-4 — therapist / closure / routine / honesty：流式生成，写入 Tab 历史
"""

import streamlit as st
from typing import Optional, Generator, Dict, Any

from prompts.user_templates import get_generate_prompt, get_emotion_eval_prompt
from utils.session_store import SessionStore
from utils.logger import log_info, log_error, log_warning


class BatchController:
    """
    批量生成控制器（5 步状态机版本）

    职责：
    1. 启动批量生成（清空历史、设置状态机起点到 step 0）
    2. 准备阶段：按 agent_type 差异化处理（emotion_eval 不写历史）
    3. 提供流式生成器供 UI 层消费（循环在 UI 层执行，避免 rerun 死锁）
    4. 收尾阶段：emotion_eval 解析存储；疗愈 Agent 写入历史并推进
    """

    # step 0 专用：情绪评估 Agent 标识
    EMOTION_EVAL_AGENT_TYPE = "emotion_eval"

    # ─────────────────────────────────────────────────────────────────────────
    # 公开接口
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def start_batch(user_input: str):
        """
        启动批量生成

        参数:
            user_input: 用户输入文本
        """
        SessionStore.start_batch(user_input)
        log_info("🚀 开始一键生成全套方案（5 步状态机）...")

    @staticmethod
    def prepare_current_agent() -> bool:
        """
        准备当前 Agent 的生成状态（不执行流式，只变更状态）

        - step 0（emotion_eval）：无对话历史，只记录进入状态
        - step 1-4（疗愈 Agent）：追加用户消息到历史，标记 generating

        返回:
            True → 有 Agent 需要处理；False → 全部完成或状态异常
        """
        if not SessionStore.is_batch_generating():
            return False

        current_agent_type = SessionStore.get_batch_current_agent_type()
        if current_agent_type is None:
            BatchController._complete_batch()
            return False

        if current_agent_type == BatchController.EMOTION_EVAL_AGENT_TYPE:
            # step 0：不写历史，直接进入生成
            log_info("▶ [emotion_eval] 情绪评估准备就绪（静默模式）")
            return True

        # step 1-4：追加用户消息，标记生成中
        initial_prompt = SessionStore.get_batch_initial_prompt()
        history = SessionStore.get_chat_history(current_agent_type)
        if not history or history[-1].get("role") != "user":
            SessionStore.append_to_history(current_agent_type, "user", initial_prompt)

        SessionStore.set_agent_generating(current_agent_type, True)
        log_info(f"▶ [{current_agent_type}] 批量生成准备就绪")
        return True

    @staticmethod
    def get_current_agent_stream() -> tuple[Optional[str], Optional[Generator]]:
        """
        获取当前 Agent 的流式生成器（供 UI 层消费）

        - step 0：使用情绪评估专用提示词
        - step 1-4：使用疗愈提示词 + 情绪上下文注入

        返回:
            (agent_type, stream_generator) 或 (None, None)
        """
        if not SessionStore.is_batch_generating():
            return None, None

        current_agent_type = SessionStore.get_batch_current_agent_type()
        if current_agent_type is None:
            return None, None

        agent_manager = st.session_state.get("agent_manager")
        if agent_manager is None:
            log_error("AgentManager 未初始化")
            return current_agent_type, None

        agent = agent_manager.get_agent(current_agent_type)
        if agent is None:
            log_error(f"Agent '{current_agent_type}' 未找到")
            return current_agent_type, None

        initial_prompt = SessionStore.get_batch_initial_prompt()

        # 按 step 类型选择提示词
        if current_agent_type == BatchController.EMOTION_EVAL_AGENT_TYPE:
            prompt = get_emotion_eval_prompt(initial_prompt)
        else:
            # step 1-4：注入情绪评估结果（step 0 完成后才有值）
            emotion_eval_result = SessionStore.get_emotion_eval_result()
            prompt = get_generate_prompt(current_agent_type, initial_prompt, emotion_eval_result)

        try:
            stream = agent.run_once_stream(prompt)
            return current_agent_type, stream
        except Exception as e:
            log_error(f"[{current_agent_type}] 获取流式生成器失败: {str(e)}")
            return current_agent_type, None

    @staticmethod
    def finalize_batch_step(agent_type: str, full_response: str):
        """
        当前 Agent 流式生成完成后的收尾处理

        - step 0（emotion_eval）：解析键值对 → 存入 SessionStore，不写 Tab 历史
        - step 1-4（疗愈 Agent）：写入 Tab 历史，标记就绪，推进索引

        参数:
            agent_type:    刚完成的 Agent 类型
            full_response: 完整的助手回复文本
        """
        if agent_type == BatchController.EMOTION_EVAL_AGENT_TYPE:
            BatchController._finalize_emotion_eval(full_response)
        else:
            BatchController._finalize_healing_agent(agent_type, full_response)

        SessionStore.advance_batch()
        log_info(f"✅ [{agent_type}] 批量步骤完成，推进到下一步")

    @staticmethod
    def get_progress_text() -> str:
        """
        获取批量生成进度文本（5 步总计）

        返回:
            如 "正在分析 · 情绪评估（1/5）..."，未在生成时返回空字符串
        """
        if not SessionStore.is_batch_generating():
            return ""

        current_index      = SessionStore.get_batch_current_index()
        current_agent_type = SessionStore.get_batch_current_agent_type()
        if current_agent_type is None:
            return ""

        total = len(SessionStore.BATCH_AGENT_ORDER)   # 5
        step  = current_index + 1

        agent_labels = {
            "emotion_eval": "情绪评估",
            "therapist":    "情绪疗愈",
            "closure":      "告别释怀",
            "routine":      "恢复规划",
            "honesty":      "清醒真话",
        }
        label = agent_labels.get(current_agent_type, current_agent_type)

        if current_agent_type == BatchController.EMOTION_EVAL_AGENT_TYPE:
            return f"正在分析 · {label}（{step}/{total}）..."
        return f"正在生成 · {label}（{step}/{total}）..."

    # ─────────────────────────────────────────────────────────────────────────
    # 私有方法
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _finalize_emotion_eval(full_response: str):
        """
        处理情绪评估（step 0）的收尾：解析输出并存入 SessionStore

        参数:
            full_response: 情绪评估 Agent 的完整输出
        """
        result = BatchController._parse_emotion_eval_response(full_response)
        if result:
            SessionStore.set_emotion_eval_result(result)
            log_info(
                f"🧠 情绪评估完成：{result.get('emotion_type')} "
                f"烈度{result.get('intensity')} · {result.get('breakup_type')}"
            )
        else:
            log_warning("⚠️ 情绪评估结果解析失败，后续 Agent 将不注入情绪上下文")

    @staticmethod
    def _finalize_healing_agent(agent_type: str, full_response: str):
        """
        处理疗愈 Agent（step 1-4）的收尾：写入历史，标记就绪

        参数:
            agent_type:    Agent 类型
            full_response: 完整的助手回复
        """
        if full_response.strip():
            SessionStore.append_to_history(agent_type, "assistant", full_response)

        SessionStore.set_agent_generating(agent_type, False)
        SessionStore.clear_agent_streaming_content(agent_type)
        SessionStore.set_agent_ready(agent_type, True)

        # routine 特殊处理：尝试解析7天计划并存入 SessionStore
        if agent_type == "routine":
            from utils.routine_parser import parse_7day_plan
            tasks = parse_7day_plan(full_response)
            if tasks:
                SessionStore.set_routine_tasks(tasks)
                log_info(f"📅 恢复计划解析成功，共 {len(tasks)} 天")
            else:
                log_warning("⚠️ 恢复计划解析失败，表格将不显示")

            # 解析治愈歌单
            from controllers.music_mapper import parse_song_list
            songs = parse_song_list(full_response)
            if songs:
                SessionStore.set_song_list(songs)
                log_info(f"🎵 治愈歌单解析成功，共 {len(songs)} 首")

    @staticmethod
    def _complete_batch():
        """标记批量生成全部完成"""
        SessionStore.set_batch_state(SessionStore.BATCH_STATE_COMPLETED)
        log_info("🎉 全套方案生成完成！")

    @staticmethod
    def _parse_emotion_eval_response(response: str) -> Optional[Dict[str, Any]]:
        """
        解析情绪评估 Agent 的键值对输出

        期望格式（每行一对，键值用冒号分隔）：
            情绪类型: 悲伤
            情绪烈度: 8
            核心痛点: 被突然提分手，缺乏心理准备
            分手类型: 被分手
            适配建议: 给予充分安全感，避免过早要求理性分析

        参数:
            response: 原始文本

        返回:
            解析成功返回字典；失败返回 None
        """
        key_map = {
            "情绪类型": "emotion_type",
            "情绪烈度": "intensity",
            "核心痛点": "core_pain",
            "分手类型": "breakup_type",
            "适配建议": "suggestion",
        }
        result: Dict[str, Any] = {}

        for line in response.splitlines():
            line = line.strip()
            if not line or ":" not in line and "：" not in line:
                continue
            # 兼容中英文冒号
            sep = "：" if "：" in line else ":"
            parts = line.split(sep, 1)
            if len(parts) != 2:
                continue
            raw_key   = parts[0].strip()
            raw_value = parts[1].strip()

            eng_key = key_map.get(raw_key)
            if eng_key is None:
                continue

            # intensity 转为整数
            if eng_key == "intensity":
                try:
                    result[eng_key] = int(raw_value)
                except ValueError:
                    result[eng_key] = 5   # 解析失败时取中值
            else:
                result[eng_key] = raw_value

        # 校验必填字段
        required = {"emotion_type", "intensity", "core_pain", "breakup_type"}
        if not required.issubset(result.keys()):
            missing = required - result.keys()
            log_warning(f"情绪评估解析缺少字段：{missing}，原始输出：{response[:200]}")
            return None

        return result
