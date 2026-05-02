"""Hello command extension - simple example.

This extension demonstrates how to create a CLI command extension
for mARCH.
"""

import sys
from pathlib import Path

# Add parent to path so we can import mARCH modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from mARCH.extension.cli_command import CliCommandExtension
from mARCH.extension.lifecycle import ExtensionContext


class HelloCommandExtension(CliCommandExtension):
    """Hello world command extension."""

    async def on_load(self):
        """Initialize extension when loaded."""
        print(f"Loading {self.context.name}")

    async def on_unload(self):
        """Clean up when unloaded."""
        print(f"Unloading {self.context.name}")

    def hello(self, name: str = "World"):
        """Say hello to someone.

        Args:
            name: The name to greet
        """
        print(f"Hello, {name}!")

    def goodbye(self):
        """Say goodbye."""
        print("Goodbye!")


def create_extension(context: ExtensionContext) -> HelloCommandExtension:
    """Factory function to create the extension.

    Args:
        context: Extension context

    Returns:
        Extension instance
    """
    ext = HelloCommandExtension(context)
    ext.register_command("hello", ext.hello, help="Say hello")
    ext.register_command("goodbye", ext.goodbye, help="Say goodbye")
    return ext
