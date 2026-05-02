"""Tests for tool extensions."""

from pathlib import Path

import pytest

from mARCH.extension.tool import (
    ToolDefinition,
    ToolExtension,
    ToolExtensionLoader,
)
from mARCH.extension.lifecycle import ExtensionContext


class TestToolDefinition:
    """Test tool definition."""

    def test_tool_creation(self):
        """Test creating a tool."""
        def handler():
            return 42

        tool = ToolDefinition("test", handler, description="Test tool")
        assert tool.name == "test"
        assert tool.callback == handler
        assert tool.description == "Test tool"

    def test_tool_with_parameters(self):
        """Test tool with parameters."""
        def handler():
            pass

        params = {"x": {"type": "number"}, "y": {"type": "number"}}
        tool = ToolDefinition(
            "calculate",
            handler,
            parameters=params,
        )
        assert tool.parameters == params


class TestToolExtension:
    """Test tool extension."""

    @pytest.fixture
    def context(self, tmp_path):
        """Create extension context."""
        return ExtensionContext("test-ext", "1.0.0", tmp_path)

    @pytest.fixture
    def extension(self, context):
        """Create tool extension."""
        return ToolExtension(context)

    def test_extension_creation(self, extension, context):
        """Test creating tool extension."""
        assert extension.context == context
        assert len(extension.tools) == 0

    def test_register_tool(self, extension):
        """Test registering tool."""
        def tool_handler(x, y):
            return x + y

        extension.register_tool(
            "add",
            tool_handler,
            description="Add two numbers",
            parameters={"x": "number", "y": "number"},
        )

        assert len(extension.tools) == 1
        assert "add" in extension.tools

    def test_register_multiple_tools(self, extension):
        """Test registering multiple tools."""
        def handler1():
            pass

        def handler2():
            pass

        extension.register_tool("tool1", handler1)
        extension.register_tool("tool2", handler2)

        assert len(extension.tools) == 2

    def test_get_tool(self, extension):
        """Test getting tool."""
        def handler():
            return 42

        extension.register_tool("answer", handler)

        tool = extension.get_tool("answer")
        assert tool is not None
        assert tool.name == "answer"

    def test_get_tool_not_found(self, extension):
        """Test getting nonexistent tool."""
        tool = extension.get_tool("nonexistent")
        assert tool is None

    def test_get_tools(self, extension):
        """Test getting all tools."""
        def h1():
            pass

        def h2():
            pass

        extension.register_tool("tool1", h1)
        extension.register_tool("tool2", h2)

        tools = extension.get_tools()
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools

    @pytest.mark.asyncio
    async def test_invoke_tool(self, extension):
        """Test invoking tool."""
        async def handler(x, y):
            return x + y

        extension.register_tool("add", handler)

        result = await extension.invoke_tool("add", 10, 20)
        assert result == 30

    @pytest.mark.asyncio
    async def test_invoke_tool_not_found(self, extension):
        """Test invoking nonexistent tool."""
        with pytest.raises(ValueError):
            await extension.invoke_tool("nonexistent")


@pytest.mark.asyncio
class TestToolExtensionLoader:
    """Test tool extension loader."""

    @pytest.fixture
    def loader(self):
        """Create tool extension loader."""
        return ToolExtensionLoader()

    async def test_loader_creation(self, loader):
        """Test creating loader."""
        assert len(loader.extensions) == 0

    async def test_list_extensions(self, loader):
        """Test listing extensions."""
        extensions = loader.list_extensions()
        assert extensions == []

    async def test_get_all_tools(self, loader):
        """Test getting all tools."""
        tools = loader.get_all_tools()
        assert tools == {}
