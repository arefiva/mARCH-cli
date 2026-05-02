"""
Advanced command-line argument parsing.

Provides CommandParser for parsing complex command syntax with flags, positionals,
and subcommands.
"""

import re
import shlex
from dataclasses import dataclass, field
from typing import Any, Optional, Union
from enum import Enum


class TokenType(Enum):
    """Token types in parsed commands."""

    FLAG = "flag"
    VALUE = "value"
    POSITIONAL = "positional"
    OPTION = "option"
    SUBCOMMAND = "subcommand"


@dataclass
class CommandToken:
    """Represents a token in a parsed command."""

    type: TokenType
    raw_value: str
    parsed_value: Any = None
    position: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class ParsedCommand:
    """Result of command parsing."""

    command_name: str
    flags: dict[str, Any] = field(default_factory=dict)
    positionals: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)
    raw_command: str = ""
    parse_errors: list[str] = field(default_factory=list)
    tokens: list[CommandToken] = field(default_factory=list)

    def get_flag(self, name: str, default: Any = None) -> Any:
        """
        Get a flag value.

        Args:
            name: Flag name (with or without dashes)
            default: Default value if flag not found

        Returns:
            Flag value or default
        """
        # Normalize flag name
        flag_name = name.lstrip("-")
        
        # Try different variations
        for key in self.flags:
            if key.lstrip("-") == flag_name:
                return self.flags[key]
        
        return default

    def get_positional(self, index: int) -> Optional[str]:
        """
        Get a positional argument by index.

        Args:
            index: Positional argument index (0-based)

        Returns:
            Positional argument or None if not found
        """
        if 0 <= index < len(self.positionals):
            return self.positionals[index]
        return None

    def has_flag(self, name: str) -> bool:
        """
        Check if a flag exists.

        Args:
            name: Flag name (with or without dashes)

        Returns:
            True if flag exists
        """
        flag_name = name.lstrip("-")
        return any(key.lstrip("-") == flag_name for key in self.flags)

    def has_errors(self) -> bool:
        """Check if there were parse errors."""
        return len(self.parse_errors) > 0


class CommandParser:
    """
    Parser for complex command-line syntax.

    Handles flags, positional arguments, quoted strings, and escape sequences.
    """

    def __init__(self) -> None:
        """Initialize CommandParser."""
        self._flag_pattern = re.compile(r'^--?[\w-]+=?')
        self._short_flag_pattern = re.compile(r'^-[a-zA-Z](?:=|$)')

    def parse(self, command: str) -> ParsedCommand:
        """
        Parse a command string.

        Args:
            command: Command string to parse

        Returns:
            ParsedCommand with parsed components
        """
        if not command or not isinstance(command, str):
            return ParsedCommand(
                command_name="",
                raw_command=command or "",
                parse_errors=["Invalid command string"],
            )

        try:
            # Use shlex for initial tokenization
            tokens = shlex.split(command, comments=False)
        except ValueError as e:
            return ParsedCommand(
                command_name="",
                raw_command=command,
                parse_errors=[f"Syntax error: {str(e)}"],
            )

        if not tokens:
            return ParsedCommand(
                command_name="",
                raw_command=command,
                parse_errors=["Empty command"],
            )

        # First token is command name
        command_name = tokens[0]
        flags: dict[str, Any] = {}
        positionals: list[str] = []
        options: dict[str, Any] = {}
        parsed_tokens: list[CommandToken] = []

        i = 1
        while i < len(tokens):
            token = tokens[i]
            position = i

            if self._is_flag(token):
                # Parse flag
                flag_token = self._parse_flag(token)
                if flag_token:
                    parsed_tokens.append(flag_token)
                    key = flag_token.parsed_value["key"]
                    value = flag_token.parsed_value.get("value")

                    # Check if flag expects a value
                    if value is None and token.startswith("--") and "=" not in token:
                        # Next token might be the value
                        if i + 1 < len(tokens) and not self._is_flag(tokens[i + 1]):
                            value = tokens[i + 1]
                            i += 1

                    flags[key] = value if value is not None else True
            else:
                # Positional argument
                positionals.append(token)
                parsed_tokens.append(
                    CommandToken(
                        type=TokenType.POSITIONAL,
                        raw_value=token,
                        parsed_value=token,
                        position=position,
                    )
                )

            i += 1

        return ParsedCommand(
            command_name=command_name,
            flags=flags,
            positionals=positionals,
            options=options,
            raw_command=command,
            parse_errors=[],
            tokens=parsed_tokens,
        )

    def _is_flag(self, token: str) -> bool:
        """Check if token is a flag."""
        return token.startswith("-")

    def _parse_flag(self, token: str) -> Optional[CommandToken]:
        """Parse a single flag token."""
        if "=" in token:
            # Flag with equals: --flag=value or -f=value
            key, value = token.split("=", 1)
            key = key.lstrip("-")
            return CommandToken(
                type=TokenType.FLAG,
                raw_value=token,
                parsed_value={"key": key, "value": value},
            )
        else:
            # Flag without value: --flag or -f
            key = token.lstrip("-")
            return CommandToken(
                type=TokenType.FLAG,
                raw_value=token,
                parsed_value={"key": key, "value": None},
            )

    def validate_syntax(self, command: str) -> tuple[bool, list[str]]:
        """
        Validate command syntax.

        Args:
            command: Command string to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        if not command:
            return False, ["Empty command"]

        parsed = self.parse(command)
        return not parsed.has_errors(), parsed.parse_errors

    def extract_flags(self, command: str) -> dict[str, Any]:
        """
        Extract all flags from a command.

        Args:
            command: Command string

        Returns:
            Dictionary of flags and their values
        """
        parsed = self.parse(command)
        return parsed.flags

    def extract_positionals(self, command: str) -> list[str]:
        """
        Extract positional arguments from a command.

        Args:
            command: Command string

        Returns:
            List of positional arguments
        """
        parsed = self.parse(command)
        return parsed.positionals

    def get_suggestions(self, partial_command: str) -> list[str]:
        """
        Get command suggestions for partial input.

        Args:
            partial_command: Partial command string

        Returns:
            List of possible completions
        """
        suggestions = []

        # If partial ends with space, might be looking for flags
        if partial_command.endswith(" "):
            suggestions.extend(["--help", "--version", "--quiet"])
        # If partial contains dash, suggest flags
        elif "-" in partial_command.split()[-1]:
            partial_flag = partial_command.split()[-1]
            all_flags = ["--help", "--version", "--quiet", "--verbose", "--force"]
            suggestions = [f for f in all_flags if f.startswith(partial_flag)]

        return suggestions

    def parse_subcommand(self, command: str) -> tuple[str, str]:
        """
        Extract main command and subcommand.

        Args:
            command: Command string potentially containing subcommand

        Returns:
            Tuple of (main_command, subcommand)
        """
        try:
            tokens = shlex.split(command)
            if len(tokens) < 2:
                return (tokens[0] if tokens else "", "")

            # First token is main command, second is potential subcommand
            main = tokens[0]
            sub = tokens[1] if not tokens[1].startswith("-") else ""

            return (main, sub)
        except ValueError:
            return ("", "")

    def normalize_command(self, command: str) -> str:
        """
        Normalize command string (e.g., collapse whitespace).

        Args:
            command: Command string to normalize

        Returns:
            Normalized command
        """
        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', command.strip())
        return normalized
