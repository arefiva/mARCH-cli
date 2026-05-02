"""CLI command extension support."""

import logging
from typing import Any, Callable, Optional

from typer import Typer

from .contracts import ExtensionManifest
from .lifecycle import ExtensionContext

logger = logging.getLogger(__name__)


class CliCommand:
    """Represents a CLI command provided by an extension."""

    def __init__(
        self,
        name: str,
        callback: Callable,
        help: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """Initialize CLI command.

        Args:
            name: Command name
            callback: Command callback function
            help: Short help text
            description: Detailed description
        """
        self.name = name
        self.callback = callback
        self.help = help
        self.description = description


class CliCommandExtension:
    """Base class for CLI command extensions."""

    def __init__(self, context: ExtensionContext):
        """Initialize CLI extension.

        Args:
            context: Extension context
        """
        self.context = context
        self.commands: list[CliCommand] = []

    async def on_load(self) -> None:
        """Called when extension is loaded."""
        pass

    async def on_unload(self) -> None:
        """Called when extension is unloaded."""
        pass

    def register_command(
        self,
        name: str,
        callback: Callable,
        help: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Register a CLI command.

        Args:
            name: Command name
            callback: Command callback
            help: Help text
            description: Description
        """
        cmd = CliCommand(name, callback, help, description)
        self.commands.append(cmd)
        logger.debug(f"Registered command {name} from {self.context.name}")

    def get_commands(self) -> list[CliCommand]:
        """Get all commands provided by this extension.

        Returns:
            List of CLI commands
        """
        return self.commands


class CliExtensionLoader:
    """Loads and manages CLI command extensions."""

    def __init__(self):
        """Initialize CLI extension loader."""
        self.extensions: dict[str, CliCommandExtension] = {}
        self.app: Optional[Typer] = None

    async def load_extension(
        self, manifest: ExtensionManifest, context: ExtensionContext
    ) -> bool:
        """Load a CLI command extension.

        Args:
            manifest: Extension manifest
            context: Extension context

        Returns:
            True if successful, False otherwise
        """
        try:
            # TODO: Dynamically import extension module
            # For now, this is a placeholder
            logger.info(f"Loading CLI extension: {manifest.name}")

            # Create extension instance
            # This would typically load from entry_point
            # ext = import_extension(context.directory / manifest.entry_point)

            # Call on_load hook
            # await ext.on_load()

            # Store extension
            # self.extensions[manifest.name] = ext

            return True
        except Exception as e:
            logger.error(f"Failed to load CLI extension {manifest.name}: {e}")
            return False

    async def unload_extension(self, name: str) -> bool:
        """Unload a CLI command extension.

        Args:
            name: Extension name

        Returns:
            True if successful, False otherwise
        """
        ext = self.extensions.get(name)
        if not ext:
            return False

        try:
            await ext.on_unload()
            del self.extensions[name]
            logger.info(f"Unloaded CLI extension: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload CLI extension {name}: {e}")
            return False

    def register_commands(self, app: Typer) -> None:
        """Register all extension commands with Typer app.

        Args:
            app: Typer application instance
        """
        self.app = app

        for ext_name, ext in self.extensions.items():
            for cmd in ext.get_commands():
                # Create command group for extension
                cmd_app = Typer(help=f"Commands from {ext_name} extension")
                cmd_app.command(name=cmd.name, help=cmd.help)(cmd.callback)

                # Register under extension namespace
                app.add_typer(cmd_app, name=ext_name)
                logger.debug(f"Registered command {ext_name}:{cmd.name}")

    def get_extension(self, name: str) -> Optional[CliCommandExtension]:
        """Get a CLI extension.

        Args:
            name: Extension name

        Returns:
            Extension or None
        """
        return self.extensions.get(name)

    def list_extensions(self) -> list[str]:
        """List all loaded CLI extensions.

        Returns:
            List of extension names
        """
        return list(self.extensions.keys())

    def get_all_commands(self) -> dict[str, list[CliCommand]]:
        """Get all commands from all extensions.

        Returns:
            Dictionary mapping extension name to list of commands
        """
        result = {}
        for ext_name, ext in self.extensions.items():
            result[ext_name] = ext.get_commands()
        return result
