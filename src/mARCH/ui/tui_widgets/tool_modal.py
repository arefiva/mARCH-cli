"""Tool call approval modal for mARCH TUI."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.screen import ModalScreen
from textual.widgets import Label, Static

# Maps key name → dismiss value
DISMISS_VALUES: dict[str, str] = {
    "y": "yes_once",
    "a": "always",
    "n": "deny",
    "escape": "deny",
}


class ToolModal(ModalScreen[str]):
    """Modal dialog for reviewing and approving/denying tool calls."""

    DEFAULT_CSS = """
    ToolModal {
        align: center middle;
    }

    ToolModal > #modal-container {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    ToolModal Label {
        margin: 0 0 1 0;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("y", "approve_once", "Yes (once)", show=True),
        Binding("a", "approve_always", "Always", show=True),
        Binding("n", "deny", "Deny", show=True),
        Binding("escape", "deny", "Deny", show=False),
        Binding("1", "approve_once", "Yes (once)", show=False),
        Binding("2", "approve_always", "Always", show=False),
        Binding("3", "deny", "Deny", show=False),
        Binding("4", "deny", "Deny", show=False),
    ]

    def __init__(
        self,
        tool_name: str = "",
        description: str = "",
        arguments: str = "",
    ) -> None:
        super().__init__()
        self._tool_name = tool_name
        self._description = description
        self._arguments = arguments

    def compose(self) -> ComposeResult:
        with Static(id="modal-container"):
            yield Label(f"[bold]Tool:[/bold] {self._tool_name}", markup=True)
            yield Label(
                f"[bold]Description:[/bold] {self._description}", markup=True
            )
            yield Label(
                f"[bold]Arguments:[/bold]\n{self._arguments}", markup=True
            )
            yield Static(
                "[dim]y=yes_once  a=always  n/Esc=deny[/dim]",
                markup=True,
            )

    def action_approve_once(self) -> None:
        self.dismiss(DISMISS_VALUES["y"])

    def action_approve_always(self) -> None:
        self.dismiss(DISMISS_VALUES["a"])

    def action_deny(self) -> None:
        self.dismiss(DISMISS_VALUES["n"])
