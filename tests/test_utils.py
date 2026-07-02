"""
工具函数单元测试
"""

import pytest
from utils.validators import validate_api_key, validate_input, sanitize_input


class TestValidateApiKey:
    """API Key 验证测试"""

    def test_valid_mimo_key(self):
        # 使用格式正确的测试 key（不包含真实密钥）
        assert validate_api_key("tp-test_key_1234567890abcdef", "mimo") is True

    def test_empty_key(self):
        assert validate_api_key("", "mimo") is False

    def test_none_key(self):
        assert validate_api_key(None, "mimo") is False

    def test_short_key(self):
        assert validate_api_key("abc", "mimo") is False

    def test_whitespace_key(self):
        assert validate_api_key("   ", "mimo") is False


class TestValidateInput:
    """用户输入验证测试"""

    def test_valid_text_input(self):
        is_valid, msg = validate_input("I feel sad", [])
        assert is_valid is True

    def test_valid_file_input(self):
        is_valid, msg = validate_input("", ["file1.jpg"])
        assert is_valid is True

    def test_empty_input(self):
        is_valid, msg = validate_input("", [])
        assert is_valid is False

    def test_short_input(self):
        is_valid, msg = validate_input("a", [])
        assert is_valid is False


class TestSanitizeInput:
    """输入清理测试"""

    def test_normal_text(self):
        assert sanitize_input("Hello world") == "Hello world"

    def test_empty_text(self):
        assert sanitize_input("") == ""

    def test_none_text(self):
        assert sanitize_input(None) == ""

    def test_whitespace_stripping(self):
        assert sanitize_input("  hello  ") == "hello"

    def test_long_text_truncation(self):
        long_text = "a" * 20000
        result = sanitize_input(long_text)
        assert len(result) == 10000
