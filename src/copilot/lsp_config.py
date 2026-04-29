"""
LSP server configuration management.

Handles configuration of language servers for different languages.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from exceptions import ConfigurationError


@dataclass
class LSPServerConfig:
    """Configuration for a single LSP server."""

    language: str
    command: str
    args: list[str] = field(default_factory=list)
    initializationOptions: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    env: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LSPServerConfig":
        """Create from dictionary."""
        return cls(**data)


class LSPConfigManager:
    """Manages Language Server Protocol server configuration."""

    DEFAULT_SERVERS: dict[str, LSPServerConfig] = {
        "python": LSPServerConfig(
            language="python",
            command="pylsp",
            initializationOptions={
                "configurationSources": ["pycodestyle", "pyflakes", "mccabe"]
            },
        ),
        "javascript": LSPServerConfig(
            language="javascript",
            command="node_modules/.bin/typescript-language-server",
            args=["--stdio"],
        ),
        "typescript": LSPServerConfig(
            language="typescript",
            command="node_modules/.bin/typescript-language-server",
            args=["--stdio"],
        ),
        "go": LSPServerConfig(
            language="go",
            command="gopls",
            initializationOptions={"usePlaceholders": True},
        ),
        "rust": LSPServerConfig(
            language="rust",
            command="rust-analyzer",
        ),
        "java": LSPServerConfig(
            language="java",
            command="java",
            args=[
                "-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=5005",
                "-jar",
                "/path/to/eclipse.jdt.ls/plugins/org.eclipse.equinox.launcher.jar",
                "-configuration",
                "/path/to/eclipse.jdt.ls/config_linux",
            ],
        ),
        "c": LSPServerConfig(
            language="c",
            command="clangd",
        ),
        "cpp": LSPServerConfig(
            language="cpp",
            command="clangd",
        ),
        "ruby": LSPServerConfig(
            language="ruby",
            command="solargraph",
            args=["stdio"],
        ),
        "bash": LSPServerConfig(
            language="bash",
            command="bash-language-server",
            args=["start"],
        ),
    }

    def __init__(self, config_file: Path | None = None) -> None:
        """
        Initialize LSP configuration manager.

        Args:
            config_file: Path to LSP configuration file (default: ~/.copilot/lsp-config.json)
        """
        if config_file:
            self.config_file = config_file
        else:
            self.config_file = Path.home() / ".copilot" / "lsp-config.json"

        self._servers: dict[str, LSPServerConfig] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        import copy

        if not self.config_file.exists():
            # Use deep copies of defaults to avoid mutation
            self._servers = {
                k: copy.deepcopy(v) for k, v in self.DEFAULT_SERVERS.items()
            }
            return

        try:
            with open(self.config_file) as f:
                data = json.load(f)

            self._servers = {}
            for language, config_data in data.items():
                self._servers[language] = LSPServerConfig.from_dict(config_data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise ConfigurationError(
                f"Failed to load LSP configuration from {self.config_file}",
                details=str(e),
            )

    def save_config(self) -> None:
        """Save configuration to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            config_dict = {
                lang: server.to_dict() for lang, server in self._servers.items()
            }
            with open(self.config_file, "w") as f:
                json.dump(config_dict, f, indent=2)
        except OSError as e:
            raise ConfigurationError(
                f"Failed to save LSP configuration to {self.config_file}",
                details=str(e),
            )

    def get_server_config(self, language: str) -> LSPServerConfig | None:
        """Get configuration for a language's LSP server."""
        return self._servers.get(language)

    def set_server_config(self, language: str, config: LSPServerConfig) -> None:
        """Set configuration for a language's LSP server."""
        self._servers[language] = config
        self.save_config()

    def enable_server(self, language: str) -> None:
        """Enable an LSP server."""
        if language in self._servers:
            self._servers[language].enabled = True
            self.save_config()

    def disable_server(self, language: str) -> None:
        """Disable an LSP server."""
        if language in self._servers:
            self._servers[language].enabled = False
            self.save_config()

    def is_server_enabled(self, language: str) -> bool:
        """Check if an LSP server is enabled."""
        server = self._servers.get(language)
        return server.enabled if server else False

    def list_servers(self) -> list[str]:
        """List all configured language servers."""
        return list(self._servers.keys())

    def list_enabled_servers(self) -> list[str]:
        """List all enabled language servers."""
        return [
            lang for lang, server in self._servers.items() if server.enabled
        ]

    def update_server_command(self, language: str, command: str, args: list[str] | None = None) -> None:
        """Update the command for a language server."""
        if language in self._servers:
            self._servers[language].command = command
            if args is not None:
                self._servers[language].args = args
            self.save_config()

    def get_all_servers(self) -> dict[str, LSPServerConfig]:
        """Get all server configurations."""
        return dict(self._servers)

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        # Create deep copies of default servers to avoid mutation
        import copy
        self._servers = {
            k: copy.deepcopy(v) for k, v in self.DEFAULT_SERVERS.items()
        }
        self.save_config()


# Global LSP config manager instance
_lsp_config_manager: LSPConfigManager | None = None


def get_lsp_config_manager() -> LSPConfigManager:
    """Get or create global LSP configuration manager."""
    global _lsp_config_manager
    if _lsp_config_manager is None:
        _lsp_config_manager = LSPConfigManager()
    return _lsp_config_manager
