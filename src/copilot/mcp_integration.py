"""
Model Context Protocol (MCP) integration for tool communication.

Provides MCP server/client functionality for connecting to external services
and tools that support the MCP standard.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class MCPResourceType(str, Enum):
    """MCP resource types."""

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    TOOL = "tool"


@dataclass
class MCPResource:
    """MCP resource definition."""

    uri: str
    name: str
    resource_type: MCPResourceType
    description: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "uri": self.uri,
            "name": self.name,
            "type": self.resource_type.value,
            "description": self.description,
            "metadata": self.metadata or {},
        }


@dataclass
class MCPTool:
    """MCP tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class MCPResourceList:
    """List of MCP resources."""

    resources: list[MCPResource]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "resources": [r.to_dict() for r in self.resources]
        }


@dataclass
class MCPToolList:
    """List of available MCP tools."""

    tools: list[MCPTool]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "tools": [t.to_dict() for t in self.tools]
        }


class MCPServer:
    """MCP server for exposing tools and resources."""

    def __init__(self, name: str = "copilot-server"):
        """Initialize MCP server."""
        self.name = name
        self.resources: dict[str, MCPResource] = {}
        self.tools: dict[str, MCPTool] = {}

    def register_resource(
        self,
        resource: MCPResource,
    ) -> None:
        """Register a resource."""
        self.resources[resource.uri] = resource

    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool

    def get_resource(self, uri: str) -> MCPResource | None:
        """Get resource by URI."""
        return self.resources.get(uri)

    def get_tool(self, name: str) -> MCPTool | None:
        """Get tool by name."""
        return self.tools.get(name)

    def list_resources(self) -> MCPResourceList:
        """List all resources."""
        return MCPResourceList(resources=list(self.resources.values()))

    def list_tools(self) -> MCPToolList:
        """List all tools."""
        return MCPToolList(tools=list(self.tools.values()))

    def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Call a tool."""
        tool = self.get_tool(tool_name)
        if not tool or not tool.handler:
            raise ValueError(f"Tool not found or not callable: {tool_name}")

        return tool.handler(**arguments)

    def to_manifest(self) -> dict:
        """Generate server manifest."""
        return {
            "name": self.name,
            "resources": [r.to_dict() for r in self.resources.values()],
            "tools": [t.to_dict() for t in self.tools.values()],
        }


class MCPClient:
    """MCP client for calling external tools."""

    def __init__(self, server_address: str | None = None):
        """Initialize MCP client."""
        self.server_address = server_address
        self.connected = False
        self.available_tools: dict[str, MCPTool] = {}

    def connect(self) -> bool:
        """Connect to MCP server."""
        if not self.server_address:
            return False

        try:
            # In a real implementation, this would establish connection
            self.connected = True
            return True
        except Exception:
            return False

    def disconnect(self) -> None:
        """Disconnect from server."""
        self.connected = False
        self.available_tools.clear()

    def list_available_tools(self) -> list[MCPTool]:
        """Get list of available tools."""
        return list(self.available_tools.values())

    def call_remote_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Call a remote tool."""
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")

        if tool_name not in self.available_tools:
            raise ValueError(f"Tool not available: {tool_name}")

        # In a real implementation, this would send RPC call
        return None

    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self.connected


class ToolRegistry:
    """Registry for MCP tools and resources."""

    def __init__(self):
        """Initialize tool registry."""
        self.registered_tools: dict[str, MCPTool] = {}
        self.registered_resources: dict[str, MCPResource] = {}
        self.tool_handlers: dict[str, Callable] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable | None = None,
    ) -> MCPTool:
        """Register a tool."""
        tool = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
        )
        self.registered_tools[name] = tool
        if handler:
            self.tool_handlers[name] = handler
        return tool

    def register_resource(
        self,
        uri: str,
        name: str,
        resource_type: MCPResourceType,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MCPResource:
        """Register a resource."""
        resource = MCPResource(
            uri=uri,
            name=name,
            resource_type=resource_type,
            description=description,
            metadata=metadata,
        )
        self.registered_resources[uri] = resource
        return resource

    def get_tool(self, name: str) -> MCPTool | None:
        """Get tool by name."""
        return self.registered_tools.get(name)

    def get_resource(self, uri: str) -> MCPResource | None:
        """Get resource by URI."""
        return self.registered_resources.get(uri)

    def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Call a registered tool."""
        if tool_name not in self.tool_handlers:
            raise ValueError(f"Tool handler not found: {tool_name}")

        handler = self.tool_handlers[tool_name]
        return handler(**arguments)

    def list_tools(self) -> list[MCPTool]:
        """List all registered tools."""
        return list(self.registered_tools.values())

    def list_resources(self) -> list[MCPResource]:
        """List all registered resources."""
        return list(self.registered_resources.values())


def get_mcp_server() -> MCPServer:
    """Get or create singleton MCP server."""
    if not hasattr(get_mcp_server, "_instance"):
        get_mcp_server._instance = MCPServer()
    return get_mcp_server._instance


def get_tool_registry() -> ToolRegistry:
    """Get or create singleton tool registry."""
    if not hasattr(get_tool_registry, "_instance"):
        get_tool_registry._instance = ToolRegistry()
    return get_tool_registry._instance
