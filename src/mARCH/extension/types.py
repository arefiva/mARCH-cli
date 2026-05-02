"""Extension type definitions and enums."""

from enum import Enum
from typing import Literal


class ExtensionType(str, Enum):
    """Supported extension types."""

    CLI_COMMAND = "cli_command"
    TOOL = "tool"
    MCP_SERVER = "mcp_server"
    SCRIPT = "script"
    SKILL = "skill"


class SandboxLevel(str, Enum):
    """Sandboxing levels for extensions."""

    NONE = "none"  # Full access (trusted first-party)
    FILE_RESTRICTED = "file_restricted"  # Whitelisted file access
    PROCESS_ISOLATED = "process_isolated"  # Subprocess with resource limits


class ExtensionStatus(str, Enum):
    """Extension lifecycle status."""

    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"
    FAILED = "failed"


# Type hints for extension configuration
PermissionType = Literal["file_read", "file_write", "network_read", "environment_vars"]
