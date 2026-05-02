"""REPL wrapper for mARCH CLI using prompt-toolkit for rich input handling.

Provides arrow key navigation, command history, and proper terminal input support.
"""

import asyncio
from pathlib import Path
from typing import Optional, Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console

from mARCH.core.execution_mode import ExecutionMode

console = Console()


class ModeChangeSignal(Exception):
    """Signal that mode should change (used to interrupt prompt)."""

    def __init__(self, new_mode: ExecutionMode):
        self.new_mode = new_mode
        super().__init__(f"Mode change to {new_mode.value}")


class MARCH_REPL:
    """REPL wrapper for mARCH CLI with readline support and mode switching."""

    def __init__(self, mode_manager: Optional["ModeManager"] = None):
        """Initialize REPL with history file.

        Args:
            mode_manager: Optional ModeManager for Shift+Tab mode switching
        """
        from mARCH.core.execution_mode import ModeManager

        self.mode_manager = mode_manager
        self.history_file = Path.home() / ".mARCH" / "history"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # Create key bindings
        kb = self._create_key_bindings()

        self.session = PromptSession(
            history=FileHistory(str(self.history_file)),
            multiline=False,  # Single line input
            enable_history_search=True,  # Enable Ctrl+R history search
            key_bindings=kb,  # Add custom key bindings
        )

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings for the REPL.

        Returns:
            KeyBindings with Shift+Tab mode switching
        """
        bindings = KeyBindings()

        @bindings.add("s-tab")  # Shift+Tab
        def _(event):
            """Handle Shift+Tab - cycle through modes."""
            if self.mode_manager:
                new_mode = self.mode_manager.cycle_mode()
                # Raise signal to exit prompt and trigger mode change
                raise ModeChangeSignal(new_mode)

        return bindings

    def get_input(self, mode: ExecutionMode = ExecutionMode.INTERACTIVE) -> str:
        """Get user input with readline support and mode indicator.

        Supports:
        - Arrow keys for cursor navigation
        - Backspace/Delete for editing
        - Up/Down for history navigation
        - Ctrl+R for history search
        - Home/End keys
        - Shift+Tab for mode cycling
        - Mode indicator in prompt

        Args:
            mode: Current ExecutionMode to display in prompt

        Returns:
            User input string, stripped of whitespace
            Special format "__MODE_CHANGE__<mode>" if Shift+Tab pressed

        Raises:
            KeyboardInterrupt: If Ctrl+C pressed
            EOFError: If EOF reached
        """
        try:
            # Build prompt with mode indicator
            mode_colors = {
                ExecutionMode.INTERACTIVE: "cyan",
                ExecutionMode.PLAN: "yellow",
                ExecutionMode.AUTOPILOT: "green",
                ExecutionMode.AUTOPILOT_FLEET: "magenta",
                ExecutionMode.SHELL: "red",
            }

            mode_name = mode.value
            mode_color = mode_colors.get(mode, "white")

            # Use HTML for rich formatting (matches original style)
            prompt_text = HTML(
                f"<ansi>march<ansi{mode_color}>[{mode_name}]</ansi{mode_color}></ansi>"
                f"<ansi>></ansi> "
            )

            user_input = self.session.prompt(prompt_text)
            return user_input.strip()

        except ModeChangeSignal as e:
            # Shift+Tab pressed - signal mode change
            return f"__MODE_CHANGE__{e.new_mode.value}"
        except KeyboardInterrupt:
            raise
        except EOFError:
            raise


class SyncREPL:
    """Synchronous wrapper around MARCH_REPL for compatibility."""

    def __init__(self, mode_manager: Optional["ModeManager"] = None):
        """Initialize sync REPL.

        Args:
            mode_manager: Optional ModeManager for mode switching
        """
        self.repl = MARCH_REPL(mode_manager=mode_manager)
        self.mode_manager = mode_manager

    def get_input(
        self, mode: ExecutionMode = ExecutionMode.INTERACTIVE
    ) -> str:
        """Get input synchronously with mode display.

        Args:
            mode: Current ExecutionMode to display in prompt

        Returns:
            User input string, stripped of whitespace
            Special format "__MODE_CHANGE__<mode>" if Shift+Tab pressed
        """
        return self.repl.get_input(mode=mode)


# Singleton instance for use in CLI
_repl_instance: Optional[SyncREPL] = None


def get_repl(mode_manager: Optional["ModeManager"] = None) -> SyncREPL:
    """Get or create the singleton REPL instance.

    Args:
        mode_manager: Optional ModeManager for mode switching (only used at creation)

    Returns:
        SyncREPL instance
    """
    global _repl_instance
    if _repl_instance is None:
        _repl_instance = SyncREPL(mode_manager=mode_manager)
    return _repl_instance
