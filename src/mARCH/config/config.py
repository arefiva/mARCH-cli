"""
Configuration management for mARCH CLI.

Handles user config files, environment variables, and defaults.
"""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mARCH.exceptions import ConfigurationError

# Load environment variables from .env file if it exists
load_dotenv()


class AppSettings(BaseSettings):
    """Application settings with environment variable support."""

    # GitHub Configuration
    github_token: str | None = Field(default=None, validation_alias="GH_TOKEN")
    github_token_fallback: str | None = Field(
        default=None, validation_alias="GITHUB_TOKEN"
    )

    # Anthropic API Key
    anthropic_api_key: str | None = Field(default=None)

    # AI Model
    model: str = Field(default="claude-opus-4-1")

    # Feature Flags
    experimental: bool = Field(default=False)
    show_banner: bool = Field(default=True)

    # Logging
    log_level: str = Field(default="INFO")
    enable_file_logging: bool = Field(default=False)

    # LSP Configuration
    lsp_enabled: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_prefix="COPILOT_",
        case_sensitive=False,
        extra="allow",
    )

    @field_validator("anthropic_api_key", mode="before")
    @classmethod
    def load_anthropic_key(cls, v: Any) -> str | None:
        """Load anthropic API key from environment if not provided."""
        if v is not None:
            return v
        # Try different environment variable names
        return os.environ.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")

    @property
    def effective_github_token(self) -> str | None:
        """Get effective GitHub token (primary or fallback)."""
        return self.github_token or self.github_token_fallback

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary."""
        return self.model_dump()


class ConfigFile(BaseModel):
    """User configuration file model."""

    model_config = ConfigDict(extra="allow")

    # Optional config fields
    model: str | None = None
    experimental: bool | None = None
    log_level: str | None = None
    lsp_enabled: bool | None = None
    anthropic_api_key: str | None = None


class ConfigManager:
    """Manages application configuration from multiple sources."""

    CONFIG_DIR_NAME = ".march"
    CONFIG_FILE_NAME = "config.json"
    LSP_CONFIG_FILE_NAME = "lsp-config.json"
    REPO_CONFIG_FILE_NAME = ".github/lsp.json"

    def __init__(self) -> None:
        """Initialize configuration manager."""
        self.user_config_dir = Path.home() / self.CONFIG_DIR_NAME
        self.user_config_file = self.user_config_dir / self.CONFIG_FILE_NAME
        self.user_lsp_config_file = self.user_config_dir / self.LSP_CONFIG_FILE_NAME
        self._settings: AppSettings | None = None
        self._user_config: ConfigFile | None = None

    @property
    def settings(self) -> AppSettings:
        """Get application settings (lazy load)."""
        if self._settings is None:
            self._settings = AppSettings()
        return self._settings

    @property
    def user_config(self) -> ConfigFile:
        """Get user configuration (lazy load)."""
        if self._user_config is None:
            self._user_config = self._load_user_config()
        return self._user_config

    def _load_user_config(self) -> ConfigFile:
        """Load user configuration from file."""
        if not self.user_config_file.exists():
            return ConfigFile()

        try:
            with open(self.user_config_file) as f:
                content = f.read()
            
            # Strip JS-style comments (for compatibility with JS mARCH CLI config)
            lines = []
            for line in content.split('\n'):
                stripped = line.strip()
                if not stripped.startswith('//'):
                    lines.append(line)
            content = '\n'.join(lines)
            
            if not content.strip():
                return ConfigFile()
            
            data = json.loads(content)
            return ConfigFile(**data)
        except (json.JSONDecodeError, ValueError):
            # Config file may be managed by JS mARCH CLI with different schema
            # Return empty config for compatibility
            return ConfigFile()

    def save_user_config(self, config: ConfigFile) -> None:
        """Save user configuration to file."""
        self.user_config_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.user_config_file, "w") as f:
                json.dump(config.model_dump(exclude_none=True), f, indent=2)
            self._user_config = config
        except OSError as e:
            raise ConfigurationError(
                f"Failed to save configuration to {self.user_config_file}",
                details=str(e),
            )

    def get_lsp_config_file(self, repo_root: Path | None = None) -> Path:
        """
        Get LSP configuration file path.

        Prefers repo-level config if it exists, otherwise returns user-level config.

        Args:
            repo_root: Optional repository root directory

        Returns:
            Path to LSP configuration file
        """
        if repo_root:
            repo_lsp_config = repo_root / self.REPO_CONFIG_FILE_NAME
            if repo_lsp_config.exists():
                return repo_lsp_config

        return self.user_lsp_config_file

    def load_lsp_config(self, repo_root: Path | None = None) -> dict[str, Any]:
        """
        Load LSP configuration.

        Args:
            repo_root: Optional repository root directory

        Returns:
            LSP configuration dictionary
        """
        config_file = self.get_lsp_config_file(repo_root)

        if not config_file.exists():
            return {}

        try:
            with open(config_file) as f:
                result: dict[str, Any] = json.load(f)
                return result
        except (OSError, json.JSONDecodeError) as e:
            raise ConfigurationError(
                f"Failed to load LSP configuration from {config_file}",
                details=str(e),
            )

    def ensure_config_dir(self) -> None:
        """Ensure user configuration directory exists."""
        self.user_config_dir.mkdir(parents=True, exist_ok=True)

    def get_model(self) -> str:
        """Get configured AI model."""
        # Priority: user config > environment > default
        if self.user_config.model:
            return self.user_config.model
        if self.settings.model:
            return self.settings.model
        return "claude-sonnet-4.5"

    def set_model(self, model: str) -> None:
        """Set and persist the AI model choice."""
        self.user_config.model = model
        self.save_user_config(self.user_config)

    def is_experimental_enabled(self) -> bool:
        """Check if experimental mode is enabled."""
        if self.user_config.experimental is not None:
            return self.user_config.experimental
        return self.settings.experimental

    def set_experimental(self, enabled: bool) -> None:
        """Set and persist experimental mode."""
        self.user_config.experimental = enabled
        self.save_user_config(self.user_config)

    def get_github_token(self) -> str | None:
        """Get GitHub authentication token."""
        # Priority: GH_TOKEN > GITHUB_TOKEN > None
        return self.settings.effective_github_token

    def set_github_token(self, token: str) -> None:
        """Store GitHub token in environment."""
        os.environ["GH_TOKEN"] = token


# Global config manager instance
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """Get or create global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.ensure_config_dir()
    return _config_manager
