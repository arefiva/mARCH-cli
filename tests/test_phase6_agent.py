"""
Tests for Phase 6: AI Agent & Conversation components.

Tests agent state management, conversation history, AI clients, and MCP integration.
"""


import pytest

from mARCH.core.agent_state import (
    Agent,
    AgentManager,
    AgentState,
    ConversationHistory,
    ConversationMode,
    get_agent_manager,
)
from mARCH.core.ai_client import (
    AIModelFactory,
    ConversationClient,
    get_conversation_client,
)

# ============================================================================
# Agent State Tests
# ============================================================================

class TestConversationHistory:
    """Tests for ConversationHistory."""

    def test_history_creation(self):
        """Test creating history."""
        hist = ConversationHistory()
        assert len(hist.messages) == 0

    def test_add_message(self):
        """Test adding message to history."""
        hist = ConversationHistory()
        hist.add_message("user", "Hello")
        assert len(hist.messages) == 1

    def test_get_messages(self):
        """Test retrieving messages."""
        hist = ConversationHistory()
        hist.add_message("user", "Hi")
        hist.add_message("assistant", "Hello")
        messages = hist.get_messages()
        assert len(messages) == 2

    def test_get_messages_with_limit(self):
        """Test retrieving messages with limit."""
        hist = ConversationHistory()
        hist.add_message("user", "1")
        hist.add_message("user", "2")
        hist.add_message("user", "3")
        messages = hist.get_messages(limit=2)
        assert len(messages) == 2

    def test_get_messages_filtered(self):
        """Test filtering messages by role."""
        hist = ConversationHistory()
        hist.add_message("user", "Hi")
        hist.add_message("assistant", "Hello")
        user_msgs = hist.get_messages(role_filter="user")
        assert len(user_msgs) == 1

    def test_clear_history(self):
        """Test clearing history."""
        hist = ConversationHistory()
        hist.add_message("user", "Test")
        hist.clear()
        assert len(hist.messages) == 0

    def test_export_history(self):
        """Test exporting history."""
        hist = ConversationHistory()
        hist.add_message("user", "Hello")
        exported = hist.export()
        assert len(exported) == 1
        assert exported[0]["role"] == "user"

class TestAgent:
    """Tests for Agent."""

    def test_agent_creation(self):
        """Test creating agent."""
        agent = Agent(name="TestAgent")
        assert agent.name == "TestAgent"
        assert agent.state == AgentState.IDLE

    def test_agent_state_management(self):
        """Test setting agent state."""
        agent = Agent()
        agent.set_state(AgentState.THINKING)
        assert agent.state == AgentState.THINKING

    def test_agent_mode_management(self):
        """Test setting agent mode."""
        agent = Agent()
        agent.set_mode(ConversationMode.AUTOPILOT)
        assert agent.mode == ConversationMode.AUTOPILOT
        assert agent.should_autopilot()

    def test_add_messages(self):
        """Test adding messages to agent."""
        agent = Agent()
        agent.add_user_message("Hello")
        agent.add_assistant_message("Hi")
        history = agent.get_history()
        assert len(history) == 2

    def test_get_conversation_context(self):
        """Test getting conversation context."""
        agent = Agent()
        agent.add_user_message("Test")
        context = agent.get_conversation_context()
        assert len(context) >= 2  # System prompt + message
        assert context[0]["role"] == "system"

    def test_is_ready_to_respond(self):
        """Test checking if ready to respond."""
        agent = Agent()
        assert agent.is_ready_to_respond()
        agent.set_state(AgentState.THINKING)
        assert not agent.is_ready_to_respond()

class TestAgentManager:
    """Tests for AgentManager."""

    def test_manager_creation(self):
        """Test manager creation."""
        mgr = AgentManager()
        assert mgr is not None

    def test_default_agent_exists(self):
        """Test default agent is created."""
        mgr = AgentManager()
        agent = mgr.get_agent()
        assert agent is not None

    def test_create_agent(self):
        """Test creating named agent."""
        mgr = AgentManager()
        agent = mgr.create_agent("test", ConversationMode.AUTOPILOT)
        assert agent.name == "test"
        assert agent.mode == ConversationMode.AUTOPILOT

    def test_list_agents(self):
        """Test listing agents."""
        mgr = AgentManager()
        mgr.create_agent("agent1")
        mgr.create_agent("agent2")
        agents = mgr.list_agents()
        assert "agent1" in agents
        assert "agent2" in agents

    def test_agent_manager_singleton(self):
        """Test agent manager singleton."""
        mgr1 = get_agent_manager()
        mgr2 = get_agent_manager()
        assert mgr1 is mgr2

# ============================================================================
# AI Client Tests
# ============================================================================

class TestAIModelFactory:
    """Tests for AI model factory."""

    def test_list_models(self):
        """Test listing available models."""
        models = AIModelFactory.list_available_models()
        assert len(models) > 0
        assert "claude-haiku-4-5" in models

    def test_create_claude_model(self):
        """Test creating Claude model."""
        model = AIModelFactory.create_model("claude-haiku-4-5")
        assert model is not None
        assert model.get_model_name() == "claude-haiku-4-5"

    def test_unknown_model_raises_error(self):
        """Test unknown model raises error."""
        with pytest.raises(ValueError):
            AIModelFactory.create_model("unknown-model")

class TestConversationClient:
    """Tests for ConversationClient."""

    def test_client_creation(self):
        """Test creating conversation client."""
        client = ConversationClient(model_name="claude-haiku-4-5")
        assert client is not None

    def test_temperature_management(self):
        """Test temperature setting."""
        client = ConversationClient()
        client.set_temperature(1.5)
        assert client.temperature == 1.5

    def test_max_tokens_management(self):
        """Test max tokens setting."""
        client = ConversationClient()
        client.set_max_tokens(4096)
        assert client.max_tokens == 4096

    def test_get_model_name(self):
        """Test getting model name."""
        client = ConversationClient(model_name="claude-opus-4.5")
        assert "opus" in client.get_model_name()

    def test_conversation_client_singleton(self):
        """Test conversation client singleton."""
        c1 = get_conversation_client()
        c2 = get_conversation_client()
        assert c1 is c2

