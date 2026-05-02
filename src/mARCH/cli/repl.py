"""REPL wrapper for mARCH CLI using prompt-toolkit for rich input handling.

Provides arrow key navigation, command history, and proper terminal input support.
"""

import asyncio
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from rich.console import Console

console = Console()


class MARCH_REPL:
    """REPL wrapper for mARCH CLI with readline support."""

    def __init__(self):
        """Initialize REPL with history file."""
        self.history_file = Path.home() / ".mARCH" / "history"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        self.session = PromptSession(
            history=FileHistory(str(self.history_file)),
            multiline=False,  # Single line input
            enable_history_search=True,  # Enable Ctrl+R history search
        )

    def get_input(self) -> str:
        """Get user input with readline support.

        Supports:
        - Arrow keys for cursor navigation
        - Backspace/Delete for editing
        - Up/Down for history navigation
        - Ctrl+R for history search
        - Home/End keys

        Returns:
            User input string, stripped of whitespace
        """
        try:
            # Use HTML formatting for the prompt (matches original style)
            prompt_text = HTML("<ansi>march<ansiyellow>></ansiyellow></ansi> ")

            user_input = self.session.prompt(prompt_text)
            return user_input.strip()
        except KeyboardInterrupt:
            raise
        except EOFError:
            raise


class SyncREPL:
    """Synchronous wrapper around MARCH_REPL for compatibility."""

    def __init__(self):
        """Initialize sync REPL."""
        self.repl = MARCH_REPL()

    def get_input(self) -> str:
        """Get input synchronously.

        Returns:
            User input string, stripped of whitespace
        """
        return self.repl.get_input()


# Singleton instance for use in CLI
_repl_instance: Optional[SyncREPL] = None


def get_repl() -> SyncREPL:
    """Get or create the singleton REPL instance.

    Returns:
        SyncREPL instance
    """
    global _repl_instance
    if _repl_instance is None:
        _repl_instance = SyncREPL()
    return _repl_instance
