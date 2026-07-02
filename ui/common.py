"""
通用 UI 组件：页眉、页脚、提示条、按钮
文案风格：温暖、有同理心，符合疗愈产品调性
"""

import streamlit as st
from config.constants import PAGE_TITLE, APP_TAGLINE, FOOTER_HTML


def render_header():
    """渲染页眉：主标题 + 副标题 + 简介"""
    st.title(f"💝 {PAGE_TITLE}")
    st.markdown(f"##### {APP_TAGLINE}")
    st.markdown(
        "分享你现在的感受，心愈 AI 会从**情绪疗愈、告别释怀、恢复规划、清醒反思**四个维度，陪你走过这段艰难时刻。"
    )
    st.divider()


def render_footer():
    """渲染页脚"""
    st.divider()
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)


def render_generate_button() -> bool:
    """
    渲染一键生成主按钮（居中放大，视觉权重高）

    返回:
        按钮是否被点击
    """
    from config.constants import GENERATE_BUTTON_TEXT
    return st.button(GENERATE_BUTTON_TEXT, type="primary", use_container_width=True)


def render_success_message(message: str):
    """渲染成功提示（绿色信息条）"""
    st.success(message)


def render_warning_message(message: str):
    """渲染警告提示（橙色信息条，口语化表达）"""
    st.warning(message)


def render_error_message(message: str):
    """渲染错误提示（用户易懂的表达）"""
    st.error(message)


def render_loading_spinner(message: str):
    """渲染加载动画上下文管理器"""
    return st.spinner(message)


def trigger_fireworks():
    """
    烟花绽放特效 — 纯 CSS 实现，3秒后自动淡出，不引入 JS

    原理：用 box-shadow 技巧模拟粒子爆炸，每朵烟花8个粒子向四周飞散。
    6朵烟花错峰绽放，与 st.balloons() 同时调用时效果互补。
    """
    st.markdown(
        """
        <div class="fw-wrap">
          <div class="fw" style="--x:18%;--y:28%;--c1:#ff6b6b;--c2:#ffd93d;--d:0.0s"></div>
          <div class="fw" style="--x:50%;--y:16%;--c1:#ffd93d;--c2:#ff9f43;--d:0.35s"></div>
          <div class="fw" style="--x:82%;--y:30%;--c1:#6bcb77;--c2:#4d96ff;--d:0.7s"></div>
          <div class="fw" style="--x:30%;--y:62%;--c1:#4d96ff;--c2:#c77dff;--d:1.0s"></div>
          <div class="fw" style="--x:68%;--y:58%;--c1:#ff6bff;--c2:#ff6b6b;--d:0.5s"></div>
          <div class="fw" style="--x:14%;--y:52%;--c1:#ffd93d;--c2:#6bcb77;--d:0.85s"></div>
        </div>

        <style>
        /* 粒子爆炸：从中心沿8个方向散射，box-shadow模拟粒子 */
        @keyframes fw-burst {
            0% {
                box-shadow:
                    0    0  0 0 var(--c1), 0    0  0 0 var(--c2),
                    0    0  0 0 var(--c1), 0    0  0 0 var(--c2),
                    0    0  0 0 var(--c1), 0    0  0 0 var(--c2),
                    0    0  0 0 var(--c1), 0    0  0 0 var(--c2);
                opacity: 1;
                transform: scale(1.2);
            }
            60% { opacity: 0.9; }
            100% {
                box-shadow:
                      0  -110px 0 3px var(--c1),
                     78px  -78px 0 3px var(--c2),
                    110px    0   0 3px var(--c1),
                     78px   78px 0 3px var(--c2),
                      0   110px 0 3px var(--c1),
                    -78px   78px 0 3px var(--c2),
                   -110px    0   0 3px var(--c1),
                    -78px  -78px 0 3px var(--c2);
                opacity: 0;
                transform: scale(0.8);
            }
        }

        /* 整体容器：fixed 覆盖全屏，2.8秒后淡出 */
        @keyframes fw-container-fade {
            0%, 55% { opacity: 1; }
            100%    { opacity: 0; pointer-events: none; }
        }

        .fw-wrap {
            position: fixed;
            inset: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: 99999;
            animation: fw-container-fade 2.8s 0.5s ease-in forwards;
        }

        .fw {
            position: absolute;
            left: var(--x);
            top:  var(--y);
            width:  10px;
            height: 10px;
            border-radius: 50%;
            background: var(--c1);
            animation: fw-burst 1.4s var(--d) cubic-bezier(.17,.67,.35,1) forwards;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_custom_css():
    """
    注入全局自定义样式

    作用范围：侧边栏任务清单的文字样式（完成划线动效）
    实现：纯 CSS transition，无 JS，不影响页面其他元素
    """
    st.markdown(
        """
        <style>
        /* 任务文字过渡基础 */
        .task-item,
        .task-done {
            display: inline-block;
            transition: text-decoration 0.3s ease, color 0.3s ease, opacity 0.3s ease;
            font-size: 0.88rem;
            line-height: 1.5;
        }

        /* 已完成：划线 + 变灰 */
        .task-done {
            text-decoration: line-through;
            color: #aaa;
            opacity: 0.75;
        }

        /* 未完成 */
        .task-item {
            color: inherit;
            opacity: 1;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
