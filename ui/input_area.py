"""
公共输入区域（倾诉入口）
引导性文案，让用户感受到被接纳
"""

import streamlit as st


def render_input_area() -> str:
    """
    渲染公共输入区域

    返回:
        用户文字输入
    """
    st.subheader("💬 说说发生了什么？")
    user_input = st.text_area(
        label="在这里倾诉",
        height=140,
        placeholder="不管是刚刚分手的茫然、还是深夜反复回想的痛苦……你现在感觉怎么样？发生了什么？都可以告诉我。",
        key="public_user_input",
        label_visibility="collapsed",
    )
    return user_input
