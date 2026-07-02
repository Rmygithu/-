"""
统一日志工具
配置带时间戳、级别、Agent 名称的输出格式
"""

import logging
import sys
from typing import Optional


# 日志格式：[时间] [级别] 消息
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str = "breakup_recovery", level: int = logging.INFO) -> logging.Logger:
    """
    设置并返回日志记录器

    参数:
        name: 日志记录器名称
        level: 日志级别

    返回:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if not logger.handlers:
        logger.setLevel(level)

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # 设置格式
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    return logger


# 全局日志记录器
logger = setup_logger()


def log_agent_start(agent_name: str):
    """
    打印 Agent 开始执行日志

    参数:
        agent_name: Agent 名称
    """
    logger.info(f"🚀 {agent_name} 开始生成回复...")


def log_agent_success(agent_name: str):
    """
    打印 Agent 执行成功日志

    参数:
        agent_name: Agent 名称
    """
    logger.info(f"✅ {agent_name} 生成完成")


def log_agent_error(agent_name: str, error: str):
    """
    打印 Agent 执行失败日志

    参数:
        agent_name: Agent 名称
        error: 错误详情
    """
    logger.error(f"❌ {agent_name} 生成失败：{error}")


def log_info(message: str):
    """打印信息日志"""
    logger.info(message)


def log_error(message: str):
    """打印错误日志"""
    logger.error(message)


def log_warning(message: str):
    """打印警告日志"""
    logger.warning(message)
