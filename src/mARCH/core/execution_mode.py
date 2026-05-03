"""Execution modes for mARCH CLI (interactive, plan, autopilot)."""

from enum import Enum


class ExecutionMode(Enum):
    """Agent execution mode for handling tasks."""

    INTERACTIVE = "interactive"  # User confirms each action
    PLAN = "plan"  # Generate plan, await user choice
    AUTOPILOT = "autopilot"  # Auto-execute with auto-approval
    AUTOPILOT_FLEET = "autopilot_fleet"  # Parallel execution (future)
    SHELL = "shell"  # Direct shell mode (future)

    @property
    def is_autopilot(self) -> bool:
        """Check if mode is autopilot-like (no user prompts)."""
        return self in (ExecutionMode.AUTOPILOT, ExecutionMode.AUTOPILOT_FLEET)


class ModeManager:
    """Manage execution mode transitions and state."""

    def __init__(self, initial_mode: ExecutionMode = ExecutionMode.INTERACTIVE):
        """Initialize mode manager.

        Args:
            initial_mode: Initial execution mode
        """
        self.current_mode = initial_mode
        self.previous_mode: ExecutionMode | None = None

    def set_mode(self, mode: ExecutionMode) -> ExecutionMode:
        """Set execution mode.

        Args:
            mode: New execution mode

        Returns:
            The new execution mode
        """
        self.previous_mode = self.current_mode
        self.current_mode = mode
        return self.current_mode

    def get_mode(self) -> ExecutionMode:
        """Get current execution mode.

        Returns:
            Current execution mode
        """
        return self.current_mode

    def is_autopilot(self) -> bool:
        """Check if current mode requires auto-approval.

        Returns:
            True if autopilot-like mode, False otherwise
        """
        return self.current_mode.is_autopilot

    def cycle_mode(self) -> ExecutionMode:
        """Cycle through modes (future for Shift+Tab).

        Cycles: interactive -> plan -> autopilot -> interactive

        Returns:
            The new execution mode
        """
        modes = [ExecutionMode.INTERACTIVE, ExecutionMode.PLAN, ExecutionMode.AUTOPILOT]
        current_idx = modes.index(self.current_mode)
        new_mode = modes[(current_idx + 1) % len(modes)]
        return self.set_mode(new_mode)

    def get_prompt_indicator(self) -> str:
        """Get mode indicator for prompt display.

        Returns:
            Color-formatted mode name for prompt
        """
        indicators = {
            ExecutionMode.INTERACTIVE: "[cyan]interactive[/cyan]",
            ExecutionMode.PLAN: "[yellow]plan[/yellow]",
            ExecutionMode.AUTOPILOT: "[green]autopilot[/green]",
            ExecutionMode.AUTOPILOT_FLEET: "[magenta]autopilot_fleet[/magenta]",
            ExecutionMode.SHELL: "[red]shell[/red]",
        }
        return indicators.get(self.current_mode, "[dim]unknown[/dim]")

    def get_transition_context(self, new_mode: ExecutionMode) -> str:
        """Return the mode-transition context message for the given mode.

        Args:
            new_mode: The execution mode to generate a message for.

        Returns:
            Human-readable mode transition message string.
        """
        from mARCH.core.prompts import get_mode_transition_message

        return get_mode_transition_message(new_mode)
