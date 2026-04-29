"""
GitHub mARCH CLI - Python Implementation

A terminal-native AI coding assistant with GitHub integration.
"""

__version__ = "0.1.0"
__author__ = "GitHub"
__license__ = "MIT"

# Import modules to make them accessible as mARCH.exceptions, mARCH.config, etc.
from mARCH import (
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
from mARCH.exceptions import (
    AuthenticationError,
    ConfigurationError,
    mARCHError,
    GitHubError,
)
from mARCH.logging_config import setup_logging
from mARCH.slash_commands import SlashCommandParser, SlashCommandType

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
    "mARCHError",
    "GitHubError",
    "SlashCommandParser",
    "SlashCommandType",
    "__version__",
    "setup_logging",
]
