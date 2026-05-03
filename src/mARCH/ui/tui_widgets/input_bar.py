"""Input bar widget with mode cycling for mARCH TUI."""

from enum import Enum
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label


class InputMode(str, Enum):
    """Available input/execution modes."""

    INTERACTIVE = "INTERACTIVE"
    PLAN = "PLAN"
    AUTOPILOT = "AUTOPILOT"
    SHELL = "SHELL"


CYCLE_ORDER: list[InputMode] = [
    InputMode.INTERACTIVE,
    InputMode.PLAN,
    InputMode.AUTOPILOT,
]

MODE_COLORS: dict[InputMode, str] = {
    InputMode.INTERACTIVE: "cyan",
    InputMode.PLAN: "yellow",
    InputMode.AUTOPILOT: "green",
    InputMode.SHELL: "red",
}


class InputBar(Widget):
    """Input bar with mode indicator and text field."""

    class ModeChanged(Message):
        """Posted when the input mode changes."""

        def __init__(self, mode: InputMode) -> None:
            super().__init__()
            self.mode = mode

    DEFAULT_CSS = """
    InputBar {
        height: auto;
        min-height: 3;
        layout: horizontal;
        padding: 0 1;
    }

    InputBar Label {
        width: 16;
        content-align: center middle;
        text-style: bold;
    }

    InputBar Input {
        width: 1fr;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("backtab", "cycle_mode", "Cycle mode", show=True),
        Binding("ctrl+n", "toggle_multiline", "Multiline", show=False),
    ]

    def __init__(self, mode_manager=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._mode_manager = mode_manager
        self._mode = InputMode.INTERACTIVE
        self._mode_label: Label | None = None
        self._input: Input | None = None

    def compose(self) -> ComposeResult:
        color = MODE_COLORS[self._mode]
        self._mode_label = Label(
            f"[{color}]{self._mode.value}[/]",
            id="mode-label",
            markup=True,
        )
        yield self._mode_label
        self._input = Input(placeholder="Type a message…", id="march-input")
        yield self._input

    def action_cycle_mode(self) -> None:
        """Cycle to the next input mode."""
        if self._mode_manager is not None:
            new_exec_mode = self._mode_manager.cycle_mode()
            try:
                self._mode = InputMode(new_exec_mode.value.upper())
            except ValueError:
                self._mode = InputMode.INTERACTIVE
        else:
            idx = CYCLE_ORDER.index(self._mode)
            self._mode = CYCLE_ORDER[(idx + 1) % len(CYCLE_ORDER)]
        if self._mode_label is not None:
            color = MODE_COLORS[self._mode]
            self._mode_label.update(f"[{color}]{self._mode.value}[/]")
        self.post_message(InputBar.ModeChanged(self._mode))

    def action_toggle_multiline(self) -> None:
        """Toggle multiline input (no-op in this scaffold)."""

    @property
    def current_mode(self) -> InputMode:
        """Current input mode."""
        return self._mode
