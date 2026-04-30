"""
GitHub mARCH CLI - Python Implementation

A terminal-native AI coding assistant with GitHub integration.
"""

__version__ = "0.1.0"
__author__ = "GitHub"
__license__ = "MIT"

# Import core modules
from mARCH import exceptions, logging_config

# Import key classes for convenience
from mARCH.exceptions import (
    AuthenticationError,
    ConfigurationError,
    mARCHError,
    GitHubError,
)
from mARCH.logging_config import setup_logging
from mARCH.core.slash_commands import SlashCommandParser, SlashCommandType

# Lazy imports for submodules to avoid circular imports
def __getattr__(name):
    """Lazy load submodules."""
    submodule_map = {
        'config': 'mARCH.config.config',
        'cli': 'mARCH.cli.cli',
        'slash_commands': 'mARCH.core.slash_commands',
        'agent_state': 'mARCH.core.agent_state',
        'ai_client': 'mARCH.core.ai_client',
        'github_auth': 'mARCH.github.github_auth',
        'github_api': 'mARCH.github.github_api',
        'github_context': 'mARCH.github.github_context',
        'github_integration': 'mARCH.github.github_integration',
        'code_intelligence': 'mARCH.code_intelligence.code_intelligence',
        'tree_sitter': 'mARCH.code_intelligence.tree_sitter',
        'syntax_highlight': 'mARCH.code_intelligence.syntax_highlight',
        'lsp_client': 'mARCH.code_intelligence.lsp_client',
        'lsp_config': 'mARCH.config.lsp_config',
        'ripgrep_search': 'mARCH.code_intelligence.ripgrep_search',
        'tui': 'mARCH.ui.tui',
        'tui_banner': 'mARCH.ui.tui_banner',
        'tui_conversation': 'mARCH.ui.tui_conversation',
        'tui_layout': 'mARCH.ui.tui_layout',
        'platform_utils': 'mARCH.platform.platform_utils',
        'image_utils': 'mARCH.platform.image_utils',
        'clipboard': 'mARCH.platform.clipboard',
        'mcp_integration': 'mARCH.platform.mcp_integration',
        'state_persistence': 'mARCH.state.state_persistence',
        'agent': 'mARCH.state.agent',
        'validation': 'mARCH.validation.validation',
    }
    if name in submodule_map:
        import importlib
        return importlib.import_module(submodule_map[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
