#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置检查脚本
验证环境变量是否正确配置
"""

import os
import sys
from dotenv import load_dotenv

# 设置标准输出编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 加载 .env 文件
load_dotenv()


def check_config():
    """检查配置是否完整"""
    print("=" * 50)
    print("💔 心愈 AI - 配置检查")
    print("=" * 50)
    print()

    issues = []
    warnings = []

    # 检查 MIMO_API_KEY
    api_key = os.getenv("MIMO_API_KEY")
    if not api_key:
        issues.append("❌ MIMO_API_KEY 未配置")
    elif api_key == "your_mimo_api_key_here":
        issues.append("❌ MIMO_API_KEY 仍为默认占位符，请填入真实的 API Key")
    else:
        print(f"✅ MIMO_API_KEY: {'*' * 8}{api_key[-4:]}")

    # 检查 MIMO_BASE_URL
    base_url = os.getenv("MIMO_BASE_URL")
    if not base_url:
        warnings.append("⚠️ MIMO_BASE_URL 未配置，将使用默认值")
        base_url = "https://token-plan-cn.xiaomimimo.com/v1"
    print(f"✅ MIMO_BASE_URL: {base_url}")

    # 检查 MIMO_MODEL_ID
    model_id = os.getenv("MIMO_MODEL_ID")
    if not model_id:
        warnings.append("⚠️ MIMO_MODEL_ID 未配置，将使用默认值")
        model_id = "mimo-v2.5-pro"
    print(f"✅ MIMO_MODEL_ID: {model_id}")

    print()

    # 输出警告
    if warnings:
        print("⚠️ 警告：")
        for w in warnings:
            print(f"  {w}")
        print()

    # 输出错误
    if issues:
        print("❌ 错误：")
        for i in issues:
            print(f"  {i}")
        print()
        print("📋 配置步骤：")
        print("  1. 复制 .env.example 为 .env")
        print("  2. 在 .env 文件中填入你的 API Key")
        print("  3. 重新运行此脚本验证配置")
        print()
        return False

    print("✅ 配置检查通过！可以启动应用了。")
    print()
    print("🚀 启动命令：")
    print("  streamlit run app.py")
    print()
    return True


if __name__ == "__main__":
    success = check_config()
    sys.exit(0 if success else 1)
