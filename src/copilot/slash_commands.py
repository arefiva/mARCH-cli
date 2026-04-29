"""
Slash command parser for Copilot CLI.

Handles parsing and routing of commands like /login, /model, /lsp, etc.
"""

from dataclasses import dataclass
from enum import Enum


class SlashCommandType(str, Enum):
    """Available slash commands."""

    LOGIN = "login"
    LOGOUT = "logout"
    MODEL = "model"
    LSP = "lsp"
    FEEDBACK = "feedback"
    EXPERIMENTAL = "experimental"
    HELP = "help"
    STATUS = "status"


@dataclass
class ParsedCommand:
    """Represents a parsed slash command."""

    command_type: SlashCommandType
    args: list[str]
    raw: str

    def __str__(self) -> str:
        return f"/{self.command_type.value} {' '.join(self.args)}".strip()


class SlashCommandParser:
    """Parser for slash commands in the CLI."""

    def __init__(self) -> None:
        """Initialize the slash command parser."""
        self.known_commands = {cmd.value: cmd for cmd in SlashCommandType}

    def parse(self, user_input: str) -> ParsedCommand | None:
        """
        Parse a user input string for slash commands.

        Args:
            user_input: Raw user input string

        Returns:
            ParsedCommand if input is a valid slash command, None otherwise
        """
        user_input = user_input.strip()

        # Check if it starts with slash
        if not user_input.startswith("/"):
            return None

        # Remove the leading slash and split
        command_str = user_input[1:].strip()
        parts = command_str.split(maxsplit=1)

        if not parts:
            return None

        command_name = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        # Validate command
        if command_name not in self.known_commands:
            return None

        command_type = self.known_commands[command_name]
        return ParsedCommand(command_type=command_type, args=args, raw=user_input)

    def is_slash_command(self, user_input: str) -> bool:
        """
        Check if input is a valid slash command.

        Args:
            user_input: User input string

        Returns:
            True if valid slash command, False otherwise
        """
        return self.parse(user_input) is not None

    def get_available_commands(self) -> list[str]:
        """Get list of available slash commands."""
        return [f"/{cmd.value}" for cmd in SlashCommandType]
