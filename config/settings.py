"""
配置加载：环境变量、默认参数、模型配置

安全说明：
- 所有敏感配置必须通过环境变量提供
- 不在代码中硬编码 API Key
- 使用 .env 文件管理本地开发配置（已加入 .gitignore）
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# MiMo 默认配置（仅非敏感项）
DEFAULT_MIMO_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
DEFAULT_MIMO_MODEL_ID = "mimo-v2.5-pro"

# SQLite 数据库默认路径（项目根目录 / data / heartHeal.db）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = str(_PROJECT_ROOT / "data" / "heartHeal.db")


def get_db_path() -> str:
    """
    获取 SQLite 数据库文件路径

    优先读取环境变量 SQLITE_DB_PATH；若未设置则使用默认路径
    （项目根目录/data/heartHeal.db）。

    返回:
        数据库文件的绝对路径字符串
    """
    return os.getenv("SQLITE_DB_PATH", DEFAULT_DB_PATH)


def load_config() -> dict:
    """
    加载全局配置

    返回:
        配置字典

    异常:
        ValueError: 缺少必要的环境变量时抛出
    """
    api_key = os.getenv("MIMO_API_KEY")
    if not api_key:
        raise ValueError(
            "❌ 未找到 MIMO_API_KEY 环境变量！\n"
            "请按以下步骤配置：\n"
            "1. 复制 .env.example 为 .env\n"
            "2. 在 .env 文件中填入你的 API Key\n"
            "3. 重新启动应用"
        )

    return {
        "mimo_api_key": api_key,
        "mimo_base_url": os.getenv("MIMO_BASE_URL", DEFAULT_MIMO_BASE_URL),
        "mimo_model_id": os.getenv("MIMO_MODEL_ID", DEFAULT_MIMO_MODEL_ID),
    }


def get_api_key() -> str:
    """
    获取 MiMo API Key

    返回:
        API Key
    """
    config = load_config()
    return config["mimo_api_key"]


def get_mimo_config() -> dict:
    """
    获取 MiMo 模型配置

    返回:
        MiMo 配置字典
    """
    config = load_config()
    return {
        "api_key": config["mimo_api_key"],
        "base_url": config["mimo_base_url"],
        "model_id": config["mimo_model_id"],
    }
