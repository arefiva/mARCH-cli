"""Tool extension support."""

import logging
from typing import Any, Callable, Optional

from .lifecycle import ExtensionContext

logger = logging.getLogger(__name__)


class ToolDefinition:
    """Definition of a tool provided by an extension."""

    def __init__(
        self,
        name: str,
        callback: Callable,
        description: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
    ):
        """Initialize tool definition.

        Args:
            name: Tool name
            callback: Tool callback function
            description: Tool description
            parameters: Parameter schema
        """
        self.name = name
        self.callback = callback
        self.description = description
        self.parameters = parameters or {}


class ToolExtension:
    """Base class for tool extensions."""

    def __init__(self, context: ExtensionContext):
        """Initialize tool extension.

        Args:
            context: Extension context
        """
        self.context = context
        self.tools: dict[str, ToolDefinition] = {}

    async def on_load(self) -> None:
        """Called when extension is loaded."""
        pass

    async def on_unload(self) -> None:
        """Called when extension is unloaded."""
        pass

    def register_tool(
        self,
        name: str,
        callback: Callable,
        description: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
    ) -> None:
        """Register a tool.

        Args:
            name: Tool name
            callback: Tool callback
            description: Description
            parameters: Parameter schema
        """
        tool = ToolDefinition(name, callback, description, parameters)
        self.tools[name] = tool
        logger.debug(f"Registered tool {name} from {self.context.name}")

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool definition or None
        """
        return self.tools.get(name)

    def get_tools(self) -> dict[str, ToolDefinition]:
        """Get all tools provided by this extension.

        Returns:
            Dictionary of tools
        """
        return dict(self.tools)

    async def invoke_tool(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Invoke a tool.

        Args:
            name: Tool name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tool result
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")

        return await tool.callback(*args, **kwargs)


class ToolExtensionLoader:
    """Loads and manages tool extensions."""

    def __init__(self):
        """Initialize tool extension loader."""
        self.extensions: dict[str, ToolExtension] = {}

    async def load_extension(
        self, manifest: "ExtensionManifest", context: ExtensionContext  # noqa: F821
    ) -> bool:
        """Load a tool extension.

        Args:
            manifest: Extension manifest
            context: Extension context

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Loading tool extension: {manifest.name}")
            # TODO: Dynamically import extension module
            return True
        except Exception as e:
            logger.error(f"Failed to load tool extension {manifest.name}: {e}")
            return False

    async def unload_extension(self, name: str) -> bool:
        """Unload a tool extension.

        Args:
            name: Extension name

        Returns:
            True if successful, False otherwise
        """
        ext = self.extensions.get(name)
        if not ext:
            return False

        try:
            await ext.on_unload()
            del self.extensions[name]
            logger.info(f"Unloaded tool extension: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload tool extension {name}: {e}")
            return False

    def get_extension(self, name: str) -> Optional[ToolExtension]:
        """Get a tool extension.

        Args:
            name: Extension name

        Returns:
            Extension or None
        """
        return self.extensions.get(name)

    def list_extensions(self) -> list[str]:
        """List all loaded tool extensions.

        Returns:
            List of extension names
        """
        return list(self.extensions.keys())

    async def invoke_tool(self, extension_name: str, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        """Invoke a tool from an extension.

        Args:
            extension_name: Extension name
            tool_name: Tool name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tool result
        """
        ext = self.get_extension(extension_name)
        if not ext:
            raise ValueError(f"Extension not found: {extension_name}")

        return await ext.invoke_tool(tool_name, *args, **kwargs)

    def get_all_tools(self) -> dict[str, dict[str, ToolDefinition]]:
        """Get all tools from all extensions.

        Returns:
            Dictionary mapping extension name to tools
        """
        result = {}
        for ext_name, ext in self.extensions.items():
            result[ext_name] = ext.get_tools()
        return result
