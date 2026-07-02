# ui 包初始化
# Streamlit UI 组件化拆分

from .sidebar import render_sidebar
from .input_area import render_input_area
from .chat_tabs import render_chat_tabs
from .common import render_footer, render_header

__all__ = [
    "render_sidebar",
    "render_input_area",
    "render_chat_tabs",
    "render_footer",
    "render_header",
]
