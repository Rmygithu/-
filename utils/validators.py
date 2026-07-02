"""
API 密钥校验、输入合法性检查
"""

from typing import Optional


def validate_api_key(api_key: str, model_provider: str = "mimo") -> bool:
    """
    验证 API Key 是否有效

    参数:
        api_key: API Key
        model_provider: 模型提供商

    返回:
        是否有效
    """
    if not api_key or not api_key.strip():
        return False

    # 基本长度检查
    if len(api_key.strip()) < 10:
        return False

    return True


def validate_input(user_input: str) -> tuple[bool, str]:
    """
    验证用户输入是否有效

    参数:
        user_input: 用户文字输入

    返回:
        (是否有效, 错误信息)
    """
    if not user_input:
        return False, "请先分享你的感受"

    if len(user_input.strip()) < 2:
        return False, "请输入更多内容"

    return True, ""


def sanitize_input(text: str) -> str:
    """
    清理用户输入，移除潜在的危险字符

    参数:
        text: 用户输入

    返回:
        清理后的文本
    """
    if not text:
        return ""

    # 移除首尾空白
    text = text.strip()

    # 限制长度
    max_length = 10000
    if len(text) > max_length:
        text = text[:max_length]

    return text
