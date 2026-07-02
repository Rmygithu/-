"""
常量定义：Tab 名称、文案、枚举值
所有名称统一为「心愈 AI・分手情绪疗愈系统」
"""

# ===== 项目信息 =====
APP_NAME = "心愈 AI・分手情绪疗愈系统"
APP_NAME_EN = "HeartHeal AI"
APP_TAGLINE = "你的专属情绪疗愈团队"

# Tab 名称
TAB_NAMES = {
    "therapist": "🤗 情绪疗愈",
    "closure": "✍️ 告别释怀",
    "routine": "📅 恢复规划",
    "honesty": "💪 清醒真话",
}

# Tab 图标
TAB_ICONS = {
    "therapist": "🤗",
    "closure": "✍️",
    "routine": "📅",
    "honesty": "💪",
}

# Tab 副标题
TAB_SUBTITLES = {
    "therapist": "共情倾听与情感支持",
    "closure": "告别信与情绪释放",
    "routine": "7天恢复计划",
    "honesty": "客观分析与清醒反馈",
}

# Agent 名称映射（含情绪评估）
AGENT_DISPLAY_NAMES = {
    "emotion_eval": "情绪评估师",
    "therapist": "共情疗愈师",
    "closure": "释怀专家",
    "routine": "恢复规划师",
    "honesty": "清醒分析师",
}

# 情绪标签（用于情绪评估结果展示）
EMOTION_TYPE_ICONS = {
    "悲伤": "😢",
    "愤怒": "😤",
    "不甘": "😣",
    "释然": "😌",
    "焦虑": "😰",
}

# 分手类型标签
BREAKUP_TYPE_ICONS = {
    "被分手": "💔",
    "主动分手": "🚶",
    "和平分手": "🤝",
    "暧昧拉扯": "🌀",
}

# 情绪烈度对应颜色语义
INTENSITY_LEVEL = {
    "high": (8, 10),    # 高烈度：≥ 8
    "mid":  (4, 7),     # 中烈度：4-7
    "low":  (1, 3),     # 低烈度：≤ 3
}

# MiMo 默认配置（仅非敏感项，API Key 从环境变量读取）
# 实际加载逻辑在 config/settings.py
MIMO_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
MIMO_MODEL_ID = "mimo-v2.5-pro"

# 页面配置
PAGE_TITLE = "心愈 AI・分手情绪疗愈系统"
PAGE_ICON = "💝"

# 一键生成按钮文案
GENERATE_BUTTON_TEXT = "✨ 一键生成全套疗愈方案"

# 页脚版权信息
FOOTER_HTML = """
<div style='text-align: center; color: #888; font-size: 0.85rem; padding: 1rem 0;'>
    <p>💝 心愈 AI · HeartHeal AI ｜ 陪你走过每一段艰难时刻</p>
    <p style='font-size:0.78rem;'>每一次分手，都是认识自己的新开始</p>
</div>
"""

# 批量生成进度名称（5 步）
BATCH_PROGRESS_NAMES = {
    "emotion_eval": "情绪评估",
    "therapist": "情绪疗愈",
    "closure": "告别释怀",
    "routine": "恢复规划",
    "honesty": "清醒真话",
}
