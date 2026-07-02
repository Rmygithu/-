"""
智能体模块单元测试
"""

import pytest
from unittest.mock import Mock, patch
from agents.manager import AgentManager


class TestAgentManager:
    """Agent 管理器测试"""

    def test_initialization(self):
        manager = AgentManager()
        assert manager.is_initialized is False
        assert len(manager.get_all_agents()) == 0

    def test_get_nonexistent_agent(self):
        manager = AgentManager()
        agent = manager.get_agent("nonexistent")
        assert agent is None

    @patch("agents.manager.TherapistAgent")
    @patch("agents.manager.ClosureAgent")
    @patch("agents.manager.RoutineAgent")
    @patch("agents.manager.HonestyAgent")
    def test_initialize_success(self, mock_honesty, mock_routine, mock_closure, mock_therapist):
        manager = AgentManager()
        result = manager.initialize("test-key")
        assert result is True
        assert manager.is_initialized is True

    @patch("agents.manager.TherapistAgent", side_effect=Exception("Init error"))
    def test_initialize_failure(self, mock_therapist):
        manager = AgentManager()
        result = manager.initialize("test-key")
        assert result is False
        assert manager.is_initialized is False


class TestBaseAgent:
    """基类 Agent 测试"""

    def test_run_with_empty_history(self):
        from agents.base import BaseAgent

        mock_agent = Mock()
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_agent.run.return_value = mock_response

        base = BaseAgent(mock_agent, "Test Agent")
        result = base.run("Hello", [])
        assert result == "Test response"

    def test_run_with_history(self):
        from agents.base import BaseAgent

        mock_agent = Mock()
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_agent.run.return_value = mock_response

        base = BaseAgent(mock_agent, "Test Agent")
        history = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"},
        ]
        result = base.run("Hello", history)
        assert result == "Test response"

    def test_run_once(self):
        from agents.base import BaseAgent

        mock_agent = Mock()
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_agent.run.return_value = mock_response

        base = BaseAgent(mock_agent, "Test Agent")
        result = base.run_once("Test prompt")
        assert result == "Test response"
