"""Plan mode display modal for mARCH TUI."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.screen import ModalScreen
from textual.widgets import Markdown, Static

# Maps key name → dismiss value
DISMISS_VALUES: dict[str, str] = {
    "e": "exit_only",
    "i": "interactive",
    "a": "autopilot",
    "f": "autopilot_fleet",
}


class PlanModal(ModalScreen[str]):
    """Modal dialog for reviewing a generated plan and choosing an action."""

    DEFAULT_CSS = """
    PlanModal {
        align: center middle;
    }

    PlanModal > #plan-container {
        width: 80;
        height: auto;
        max-height: 90vh;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("e", "exit_only", "Exit only", show=True),
        Binding("i", "interactive", "Interactive", show=True),
        Binding("a", "autopilot", "Autopilot", show=True),
        Binding("f", "autopilot_fleet", "Fleet", show=True),
        Binding("escape", "exit_only", "Exit", show=False),
    ]

    def __init__(self, plan_summary: str = "") -> None:
        super().__init__()
        self._plan_summary = plan_summary

    def compose(self) -> ComposeResult:
        with Static(id="plan-container"):
            yield Markdown(self._plan_summary or "_No plan summary available._")
            yield Static(
                "[dim]e=exit_only  i=interactive  a=autopilot  f=fleet[/dim]",
                markup=True,
            )

    def action_exit_only(self) -> None:
        self.dismiss(DISMISS_VALUES["e"])

    def action_interactive(self) -> None:
        self.dismiss(DISMISS_VALUES["i"])

    def action_autopilot(self) -> None:
        self.dismiss(DISMISS_VALUES["a"])

    def action_autopilot_fleet(self) -> None:
        self.dismiss(DISMISS_VALUES["f"])
