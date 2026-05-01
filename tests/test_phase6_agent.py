"""
Tests for Phase 6: AI Agent & Conversation components.

Tests agent state management, conversation history, AI clients, and MCP integration.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from mARCH.core.agent_state import (
    AgentState,
    ConversationMode,
    ConversationMessage,
    AgentContext,
    ConversationHistory,
    Agent,
    AgentManager,
    get_agent_manager,
)
from mARCH.core.ai_client import (
    AIModelFactory,
    ConversationClient,
    CodeAnalysisClient,
    get_conversation_client,
    get_code_analysis_client,
)
from mARCH.platform.mcp_integration import (
    MCPResourceType,
    MCPResource,
    MCPTool,
    MCPServer,
    MCPClient,
    ToolRegistry,
    get_mcp_server,
    get_tool_registry,
)


# ============================================================================
# Agent State Tests
# ============================================================================


class TestAgentState:
    """Tests for AgentState enum."""

    def test_agent_states_exist(self):
        """Test all agent states are defined."""
        assert AgentState.IDLE in AgentState
        assert AgentState.THINKING in AgentState
        assert AgentState.PROCESSING in AgentState
        assert AgentState.RESPONDING in AgentState
        assert AgentState.ERROR in AgentState
        assert AgentState.WAITING_INPUT in AgentState


class TestConversationMode:
    """Tests for ConversationMode enum."""

    def test_conversation_modes_exist(self):
        """Test all conversation modes are defined."""
        assert ConversationMode.INTERACTIVE in ConversationMode
        assert ConversationMode.AUTOPILOT in ConversationMode
        assert ConversationMode.COMMAND in ConversationMode


class TestConversationMessage:
    """Tests for ConversationMessage."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = ConversationMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None

    def test_message_to_dict(self):
        """Test converting message to dict."""
        msg = ConversationMessage(role="assistant", content="Hi there")
        msg_dict = msg.to_dict()
        assert msg_dict["role"] == "assistant"
        assert msg_dict["content"] == "Hi there"


class TestAgentContext:
    """Tests for AgentContext."""

    def test_context_creation(self):
        """Test creating context."""
        ctx = AgentContext(current_directory="/home/user")
        assert ctx.current_directory == "/home/user"

    def test_update_from_github_context(self):
        """Test updating from GitHub context."""
        ctx = AgentContext()
        github_ctx = {
            "repo_root": "/home/user/repo",
            "branch": "main",
        }
        ctx.update_from_github_context(github_ctx)
        assert ctx.current_directory == "/home/user/repo"
        assert ctx.git_branch == "main"


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


class TestCodeAnalysisClient:
    """Tests for CodeAnalysisClient."""

    def test_code_analysis_client_creation(self):
        """Test creating code analysis client."""
        client = CodeAnalysisClient()
        assert client is not None

    def test_code_analysis_client_singleton(self):
        """Test code analysis client singleton."""
        c1 = get_code_analysis_client()
        c2 = get_code_analysis_client()
        assert c1 is c2


# ============================================================================
# MCP Integration Tests
# ============================================================================


class TestMCPResourceType:
    """Tests for MCPResourceType enum."""

    def test_resource_types_exist(self):
        """Test resource types are defined."""
        assert MCPResourceType.TEXT in MCPResourceType
        assert MCPResourceType.FILE in MCPResourceType
        assert MCPResourceType.TOOL in MCPResourceType


class TestMCPResource:
    """Tests for MCPResource."""

    def test_resource_creation(self):
        """Test creating resource."""
        resource = MCPResource(
            uri="file:///test.py",
            name="Test File",
            resource_type=MCPResourceType.FILE,
        )
        assert resource.uri == "file:///test.py"

    def test_resource_to_dict(self):
        """Test converting resource to dict."""
        resource = MCPResource(
            uri="http://example.com",
            name="Example",
            resource_type=MCPResourceType.TEXT,
        )
        res_dict = resource.to_dict()
        assert res_dict["uri"] == "http://example.com"
        assert res_dict["type"] == "text"


class TestMCPTool:
    """Tests for MCPTool."""

    def test_tool_creation(self):
        """Test creating tool."""
        tool = MCPTool(
            name="test_tool",
            description="Test tool",
            input_schema={"type": "object"},
        )
        assert tool.name == "test_tool"

    def test_tool_to_dict(self):
        """Test converting tool to dict."""
        tool = MCPTool(
            name="analyze",
            description="Analyze code",
            input_schema={"properties": {}},
        )
        tool_dict = tool.to_dict()
        assert tool_dict["name"] == "analyze"


class TestMCPServer:
    """Tests for MCPServer."""

    def test_server_creation(self):
        """Test creating MCP server."""
        server = MCPServer()
        assert server is not None

    def test_register_resource(self):
        """Test registering resource."""
        server = MCPServer()
        resource = MCPResource(
            uri="test",
            name="Test",
            resource_type=MCPResourceType.TEXT,
        )
        server.register_resource(resource)
        assert server.get_resource("test") is not None

    def test_register_tool(self):
        """Test registering tool."""
        server = MCPServer()
        tool = MCPTool(
            name="test",
            description="Test",
            input_schema={},
        )
        server.register_tool(tool)
        assert server.get_tool("test") is not None

    def test_list_resources(self):
        """Test listing resources."""
        server = MCPServer()
        resource = MCPResource(
            uri="res1",
            name="Resource",
            resource_type=MCPResourceType.FILE,
        )
        server.register_resource(resource)
        resources = server.list_resources()
        assert len(resources.resources) >= 1

    def test_mcp_server_singleton(self):
        """Test MCP server singleton."""
        s1 = get_mcp_server()
        s2 = get_mcp_server()
        assert s1 is s2


class TestMCPClient:
    """Tests for MCPClient."""

    def test_client_creation(self):
        """Test creating MCP client."""
        client = MCPClient()
        assert client is not None

    def test_connection_status(self):
        """Test connection status."""
        client = MCPClient()
        assert not client.is_connected()


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_registry_creation(self):
        """Test creating tool registry."""
        registry = ToolRegistry()
        assert registry is not None

    def test_register_tool_in_registry(self):
        """Test registering tool in registry."""
        registry = ToolRegistry()
        tool = registry.register_tool(
            name="test",
            description="Test tool",
            input_schema={"type": "object"},
        )
        assert registry.get_tool("test") is not None

    def test_register_resource_in_registry(self):
        """Test registering resource in registry."""
        registry = ToolRegistry()
        resource = registry.register_resource(
            uri="test",
            name="Test",
            resource_type=MCPResourceType.FILE,
        )
        assert registry.get_resource("test") is not None

    def test_list_tools_in_registry(self):
        """Test listing tools in registry."""
        registry = ToolRegistry()
        registry.register_tool("t1", "Tool 1", {})
        registry.register_tool("t2", "Tool 2", {})
        tools = registry.list_tools()
        assert len(tools) >= 2

    def test_tool_registry_singleton(self):
        """Test tool registry singleton."""
        r1 = get_tool_registry()
        r2 = get_tool_registry()
        assert r1 is r2


# ============================================================================
# Integration Tests
# ============================================================================


class TestPhase6Integration:
    """Integration tests for Phase 6 components."""

    def test_all_components_available(self):
        """Test all Phase 6 components are available."""
        assert get_agent_manager() is not None
        assert get_conversation_client() is not None
        assert get_code_analysis_client() is not None
        assert get_mcp_server() is not None
        assert get_tool_registry() is not None

    def test_agent_conversation_flow(self):
        """Test agent conversation flow."""
        manager = get_agent_manager()
        agent = manager.get_agent()

        # Simulate conversation
        agent.add_user_message("What is Python?")
        agent.add_assistant_message("Python is a programming language...")

        history = agent.get_history()
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"

    def test_mcp_server_and_client_integration(self):
        """Test MCP server and client integration."""
        server = get_mcp_server()
        
        # Register resource and tool
        resource = MCPResource(
            uri="test",
            name="Test",
            resource_type=MCPResourceType.FILE,
        )
        server.register_resource(resource)

        tool = MCPTool(
            name="test_tool",
            description="Test",
            input_schema={},
        )
        server.register_tool(tool)

        # Verify registration
        assert server.get_resource("test") is not None
        assert server.get_tool("test_tool") is not None
