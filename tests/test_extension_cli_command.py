"""Tests for CLI command extensions."""

from pathlib import Path

import pytest

from mARCH.extension.cli_command import (
    CliCommand,
    CliCommandExtension,
    CliExtensionLoader,
)
from mARCH.extension.lifecycle import ExtensionContext


class TestCliCommand:
    """Test CLI command definition."""

    def test_command_creation(self):
        """Test creating a CLI command."""
        def handler():
            return "result"

        cmd = CliCommand("test", handler, help="Test command")
        assert cmd.name == "test"
        assert cmd.callback == handler
        assert cmd.help == "Test command"

    def test_command_with_description(self):
        """Test command with description."""
        def handler():
            pass

        cmd = CliCommand(
            "test",
            handler,
            help="Help",
            description="Full description",
        )
        assert cmd.description == "Full description"


class TestCliCommandExtension:
    """Test CLI command extension."""

    @pytest.fixture
    def context(self, tmp_path):
        """Create extension context."""
        return ExtensionContext("test-ext", "1.0.0", tmp_path)

    @pytest.fixture
    def extension(self, context):
        """Create CLI extension."""
        return CliCommandExtension(context)

    def test_extension_creation(self, extension, context):
        """Test creating CLI extension."""
        assert extension.context == context
        assert len(extension.commands) == 0

    def test_register_command(self, extension):
        """Test registering command."""
        def cmd_handler():
            return "output"

        extension.register_command(
            "hello",
            cmd_handler,
            help="Say hello",
        )

        assert len(extension.commands) == 1
        assert extension.commands[0].name == "hello"

    def test_register_multiple_commands(self, extension):
        """Test registering multiple commands."""
        def cmd1():
            pass

        def cmd2():
            pass

        extension.register_command("cmd1", cmd1)
        extension.register_command("cmd2", cmd2)

        assert len(extension.commands) == 2

    def test_get_commands(self, extension):
        """Test getting all commands."""
        def handler():
            pass

        extension.register_command("test1", handler)
        extension.register_command("test2", handler)

        commands = extension.get_commands()
        assert len(commands) == 2


@pytest.mark.asyncio
class TestCliExtensionLoader:
    """Test CLI extension loader."""

    @pytest.fixture
    def loader(self):
        """Create CLI extension loader."""
        return CliExtensionLoader()

    async def test_loader_creation(self, loader):
        """Test creating loader."""
        assert len(loader.extensions) == 0

    async def test_list_extensions(self, loader):
        """Test listing extensions."""
        extensions = loader.list_extensions()
        assert extensions == []

    async def test_get_all_commands(self, loader):
        """Test getting all commands."""
        commands = loader.get_all_commands()
        assert commands == {}
