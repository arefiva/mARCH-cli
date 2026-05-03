"""Textual-based TUI application for mARCH.

Provides a reactive, widget-based terminal interface using the Textual framework.
"""

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Footer, Header, Input

from mARCH.ui.tui_widgets import ConversationView, InputBar


class MarchApp(App[None]):
    """Main Textual application for mARCH CLI."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #conversation-area {
        height: 1fr;
        border: solid $primary;
        padding: 0 1;
    }

    #input-bar {
        height: auto;
        min-height: 3;
        border: solid $accent;
        padding: 0 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+d", "quit", "Quit", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield ConversationView(id="conversation-area")
        yield InputBar(id="input-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Focus the input field when the app starts."""
        self.query_one("#march-input", Input).focus()

    def action_quit(self) -> None:
        """Exit the application cleanly."""
        self.exit()
