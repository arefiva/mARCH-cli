"""Textual-based TUI application for mARCH.

Provides a reactive, widget-based terminal interface using the Textual framework.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Footer, Header, Input

from mARCH.core.slash_commands import SlashCommandParser, SlashCommandType
from mARCH.ui.tui_widgets import ConversationView, InputBar
from mARCH.ui.tui_widgets.input_bar import InputMode
from mARCH.ui.tui_widgets.message import MessageRole

if TYPE_CHECKING:
    from mARCH.ui.tui_session import TuiSession


def _help_text() -> str:
    """Return plain-text help content for the /help command."""
    return (
        "Available commands:\n"
        "  /help        Show this message\n"
        "  /status      Show current status\n"
        "  /model       Show current model\n"
        "  exit, quit   Exit the application\n\n"
        "Type a message to chat with the AI assistant."
    )


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

    def __init__(self, session: TuiSession | None = None, ai_client=None, agent=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._session = session
        # When session is provided, prefer its values; explicit kwargs override for tests
        self._ai_client = ai_client if ai_client is not None else (session.ai_client if session else None)
        self._agent = agent if agent is not None else (session.agent if session else None)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield ConversationView(id="conversation-area")
        mode_manager = self._session.mode_manager if self._session else None
        yield InputBar(id="input-bar", mode_manager=mode_manager)
        yield Footer()

    def on_mount(self) -> None:
        """Focus the input field when the app starts."""
        self.query_one("#march-input", Input).focus()

    def on_input_bar_mode_changed(self, event: InputBar.ModeChanged) -> None:
        """Display a system notification when the input mode changes."""
        conv = self.query_one(ConversationView)
        conv.add_message(MessageRole.SYSTEM, f"⚡ Mode changed to: {event.mode.value}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle message submission from the input bar."""
        text = event.value.strip()
        if not text:
            return
        event.input.clear()

        if text.lower() in ("exit", "quit"):
            self.exit()
            return

        if text.startswith("/"):
            self._handle_slash_command(text)
            return

        conv = self.query_one(ConversationView)
        conv.add_message(MessageRole.USER, text)
        if self._agent is not None:
            self._agent.add_user_message(text)
        if self._ai_client is not None:
            input_bar = self.query_one("#input-bar", InputBar)
            current_mode = input_bar.current_mode
            self._stream_ai_response(text, current_mode)
        else:
            conv.add_message(
                MessageRole.ASSISTANT,
                "AI client not configured — set ANTHROPIC_API_KEY",
            )

    def _handle_slash_command(self, text: str) -> None:
        """Dispatch a slash command and display the result as a SYSTEM message."""
        conv = self.query_one(ConversationView)
        parser = (
            self._session.slash_parser
            if self._session and self._session.slash_parser is not None
            else SlashCommandParser()
        )
        parsed = parser.parse(text)
        if parsed is None:
            conv.add_message(MessageRole.SYSTEM, f"Unknown command: {text}")
            return

        if parsed.command_type == SlashCommandType.HELP:
            conv.add_message(MessageRole.SYSTEM, _help_text())
        elif parsed.command_type == SlashCommandType.STATUS:
            conv.add_message(MessageRole.SYSTEM, self._status_text())
        elif parsed.command_type == SlashCommandType.MODEL:
            conv.add_message(MessageRole.SYSTEM, self._model_text())
        else:
            conv.add_message(
                MessageRole.SYSTEM,
                f"/{parsed.command_type.value} is not available in TUI mode",
            )

    def _status_text(self) -> str:
        """Return a plain-text status summary."""
        lines = ["mARCH Status:"]
        if self._session and self._session.config_manager:
            cm = self._session.config_manager
            lines.append(f"  Model: {cm.get_model()}")
            lines.append(f"  Experimental: {'on' if cm.is_experimental_enabled() else 'off'}")
        lines.append(f"  AI client: {'configured' if self._ai_client is not None else 'not configured'}")
        return "\n".join(lines)

    def _model_text(self) -> str:
        """Return the current model name as a plain-text string."""
        if self._session and self._session.config_manager:
            return f"Current model: {self._session.config_manager.get_model()}"
        return "Model: not configured"

    @work(thread=True, exclusive=True)
    def _stream_ai_response(self, user_text: str, mode: InputMode = InputMode.INTERACTIVE) -> None:
        """Stream AI response in a background thread."""
        conv = self.query_one(ConversationView)
        streaming_widget = self.call_from_thread(conv.start_streaming)
        if self._agent is not None:
            messages = self._agent.get_conversation_context(include_system_prompt=True)
        else:
            messages = [{"role": "user", "content": user_text}]
        if mode == InputMode.PLAN:
            for i in range(len(messages) - 1, -1, -1):
                if messages[i]["role"] == "user":
                    messages[i] = {**messages[i], "content": f"[[PLAN]] {user_text}"}
                    break
        full_response = ""
        try:
            for chunk in self._ai_client.stream_chat(messages):
                full_response += chunk
                self.call_from_thread(streaming_widget.append_chunk, chunk)
            if self._agent is not None:
                self._agent.add_assistant_message(full_response)
            self.call_from_thread(conv.finish_streaming)
        except Exception as e:
            self.call_from_thread(streaming_widget.append_chunk, f"Error: {e}")
            self.call_from_thread(conv.finish_streaming)

    def action_quit(self) -> None:
        """Exit the application cleanly."""
        self.exit()

