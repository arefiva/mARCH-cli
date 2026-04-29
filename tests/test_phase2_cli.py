"""
Tests for Phase 2: CLI Foundation.

Tests for slash command parsing, CLI argument handling, and command routing.
"""

import pytest
from pathlib import Path

from mARCH.slash_commands import SlashCommandParser, SlashCommandType, ParsedCommand
from mARCH.cli import (
    AppContext,
    get_app_context,
    handle_model_command,
    handle_experimental_command,
    handle_status_command,
)


class TestSlashCommandParser:
    """Tests for SlashCommandParser."""

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        parser = SlashCommandParser()
        assert parser is not None
        assert len(parser.known_commands) > 0

    def test_parse_login_command(self):
        """Test parsing /login command."""
        parser = SlashCommandParser()
        result = parser.parse("/login")
        assert result is not None
        assert result.command_type == SlashCommandType.LOGIN
        assert result.args == []

    def test_parse_command_with_args(self):
        """Test parsing command with arguments."""
        parser = SlashCommandParser()
        result = parser.parse("/model claude-sonnet-4.5")
        assert result is not None
        assert result.command_type == SlashCommandType.MODEL
        assert "claude-sonnet-4.5" in result.args

    def test_parse_non_slash_input(self):
        """Test non-slash input returns None."""
        parser = SlashCommandParser()
        result = parser.parse("hello world")
        assert result is None

    def test_is_slash_command_valid(self):
        """Test is_slash_command with valid command."""
        parser = SlashCommandParser()
        assert parser.is_slash_command("/login") is True
        assert parser.is_slash_command("/help") is True

    def test_is_slash_command_invalid(self):
        """Test is_slash_command with invalid command."""
        parser = SlashCommandParser()
        assert parser.is_slash_command("regular input") is False
        assert parser.is_slash_command("/unknown") is False

    def test_parse_all_commands(self):
        """Test parsing all known slash commands."""
        parser = SlashCommandParser()
        for cmd_type in SlashCommandType:
            result = parser.parse(f"/{cmd_type.value}")
            assert result is not None
            assert result.command_type == cmd_type

    def test_parse_case_insensitive(self):
        """Test that command parsing is case-insensitive."""
        parser = SlashCommandParser()
        result1 = parser.parse("/LOGIN")
        result2 = parser.parse("/login")
        assert result1 is not None
        assert result2 is not None
        assert result1.command_type == result2.command_type

    def test_get_available_commands(self):
        """Test getting list of available commands."""
        parser = SlashCommandParser()
        commands = parser.get_available_commands()
        assert len(commands) == 8
        assert "/login" in commands
        assert "/help" in commands
        assert "/model" in commands


class TestAppContext:
    """Tests for AppContext."""

    def test_app_context_initialization(self):
        """Test AppContext initializes correctly."""
        ctx = AppContext()
        assert ctx is not None
        assert ctx.config_manager is not None
        assert ctx.slash_parser is not None
        assert isinstance(ctx.experimental_mode, bool)
        assert isinstance(ctx.current_model, str)

    def test_app_context_model(self):
        """Test app context model property."""
        ctx = AppContext()
        assert ctx.current_model == "claude-sonnet-4.5"

    def test_app_context_experimental(self):
        """Test app context experimental mode."""
        ctx = AppContext()
        assert isinstance(ctx.experimental_mode, bool)

    def test_get_app_context_singleton(self):
        """Test get_app_context returns singleton."""
        ctx1 = get_app_context()
        ctx2 = get_app_context()
        assert ctx1 is ctx2


class TestParsedCommand:
    """Tests for ParsedCommand."""

    def test_parsed_command_creation(self):
        """Test ParsedCommand creation."""
        cmd = ParsedCommand(
            command_type=SlashCommandType.MODEL,
            args=["claude-sonnet-4.5"],
            raw="/model claude-sonnet-4.5",
        )
        assert cmd.command_type == SlashCommandType.MODEL
        assert "claude-sonnet-4.5" in cmd.args

    def test_parsed_command_str(self):
        """Test ParsedCommand string representation."""
        cmd = ParsedCommand(
            command_type=SlashCommandType.LOGIN,
            args=[],
            raw="/login",
        )
        assert "/login" in str(cmd)


class TestCommandHandlers:
    """Tests for command handler functions."""

    def test_model_command_handler(self, capsys):
        """Test /model command handler."""
        ctx = AppContext()
        original_model = ctx.current_model
        
        # Test viewing current model
        handle_model_command(ctx, [])
        captured = capsys.readouterr()
        assert original_model in captured.out or "Current Model" in captured.out

    def test_experimental_command_handler(self, capsys):
        """Test /experimental command handler."""
        ctx = AppContext()
        original_state = ctx.experimental_mode
        
        # Toggle experimental mode
        handle_experimental_command(ctx, [])
        assert ctx.experimental_mode != original_state
        
        captured = capsys.readouterr()
        assert "Experimental mode" in captured.out

    def test_status_command_handler(self, capsys):
        """Test /status command handler."""
        ctx = AppContext()
        handle_status_command(ctx, [])
        
        captured = capsys.readouterr()
        assert "Version" in captured.out
        assert "Model" in captured.out
        assert "Experimental Mode" in captured.out


class TestSlashCommandTypes:
    """Tests for SlashCommandType enum."""

    def test_all_command_types_exist(self):
        """Test all expected command types exist."""
        expected_commands = [
            "LOGIN",
            "LOGOUT",
            "MODEL",
            "LSP",
            "FEEDBACK",
            "EXPERIMENTAL",
            "HELP",
            "STATUS",
        ]
        for cmd_name in expected_commands:
            assert hasattr(SlashCommandType, cmd_name)

    def test_command_type_values(self):
        """Test command type values are lowercase."""
        for cmd_type in SlashCommandType:
            assert cmd_type.value == cmd_type.value.lower()
