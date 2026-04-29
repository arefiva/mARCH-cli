"""
GitHub Copilot CLI - Python Implementation

A terminal-native AI coding assistant with GitHub integration.
"""

__version__ = "0.1.0"
__author__ = "GitHub"
__license__ = "MIT"

# Import modules to make them accessible as copilot.exceptions, copilot.config, etc.
from copilot import (
    exceptions,
    logging_config,
    slash_commands,
    config,
    cli,
    github_auth,
    github_api,
    github_context,
    github_integration,
    ai_client,
    agent_state,
    code_intelligence,
    lsp_client,
    lsp_config,
    mcp_integration,
    platform_utils,
    state_persistence,
    tui,
    tui_banner,
    tui_conversation,
    tui_layout,
    image_utils,
    clipboard,
    validation,
    syntax_highlight,
    tree_sitter,
    ripgrep_search,
)

# Also import key classes for convenience
from copilot.exceptions import (
    AuthenticationError,
    ConfigurationError,
    CopilotError,
    GitHubError,
)
from copilot.logging_config import setup_logging
from copilot.slash_commands import SlashCommandParser, SlashCommandType

__all__ = [
    # Modules
    "exceptions",
    "logging_config",
    "slash_commands",
    "config",
    "cli",
    "github_auth",
    "github_api",
    "github_context",
    "github_integration",
    "ai_client",
    "agent_state",
    "code_intelligence",
    "lsp_client",
    "lsp_config",
    "mcp_integration",
    "platform_utils",
    "state_persistence",
    "tui",
    "tui_banner",
    "tui_conversation",
    "tui_layout",
    "image_utils",
    "clipboard",
    "validation",
    "syntax_highlight",
    "tree_sitter",
    "ripgrep_search",
    # Key classes
    "AuthenticationError",
    "ConfigurationError",
    "CopilotError",
    "GitHubError",
    "SlashCommandParser",
    "SlashCommandType",
    "__version__",
    "setup_logging",
]
