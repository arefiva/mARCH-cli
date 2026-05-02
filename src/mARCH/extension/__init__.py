"""Extension system for mARCH CLI.

This module provides a pluggable architecture for extending mARCH with
custom capabilities including CLI commands, tools, MCP servers, and scripts.
"""

from .api import ExtensionAPI
from .contracts import (
    ExtensionCapability,
    ExtensionManifest,
)
from .lifecycle import ExtensionLifecycleManager
from .registry import ExtensionRegistry
from .types import ExtensionType, SandboxLevel

__all__ = [
    "ExtensionAPI",
    "ExtensionCapability",
    "ExtensionManifest",
    "ExtensionLifecycleManager",
    "ExtensionRegistry",
    "ExtensionType",
    "SandboxLevel",
]
