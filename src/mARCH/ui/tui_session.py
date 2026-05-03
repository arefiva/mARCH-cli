"""TUI session data container for mARCH."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mARCH.config.config import ConfigManager
    from mARCH.core.agent_state import Agent
    from mARCH.core.ai_client import ConversationClient
    from mARCH.core.execution_mode import ModeManager
    from mARCH.core.slash_commands import SlashCommandParser
    from mARCH.github.github_integration import GitHubIntegration


@dataclass
class TuiSession:
    """Holds all app-level state needed by the TUI."""

    ai_client: ConversationClient | None = field(default=None)
    agent: Agent | None = field(default=None)
    slash_parser: SlashCommandParser | None = field(default=None)
    mode_manager: ModeManager | None = field(default=None)
    config_manager: ConfigManager | None = field(default=None)
    github_integration: GitHubIntegration | None = field(default=None)
