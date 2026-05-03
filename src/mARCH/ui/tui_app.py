"""Textual-based TUI application for mARCH.

Provides a reactive, widget-based terminal interface using the Textual framework.
"""

from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Footer, Header, Input

from mARCH.ui.tui_widgets import ConversationView, InputBar
from mARCH.ui.tui_widgets.message import MessageRole


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

    def __init__(self, ai_client=None, agent=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._ai_client = ai_client
        self._agent = agent

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield ConversationView(id="conversation-area")
        yield InputBar(id="input-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Focus the input field when the app starts."""
        self.query_one("#march-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle message submission from the input bar."""
        text = event.value.strip()
        if not text:
            return
        event.input.clear()
        conv = self.query_one(ConversationView)
        conv.add_message(MessageRole.USER, text)
        if self._agent is not None:
            self._agent.add_user_message(text)
        if self._ai_client is not None:
            self._stream_ai_response(text)
        else:
            conv.add_message(
                MessageRole.ASSISTANT,
                "AI client not configured — set ANTHROPIC_API_KEY",
            )

    @work(thread=True, exclusive=True)
    def _stream_ai_response(self, user_text: str) -> None:
        """Stream AI response in a background thread."""
        conv = self.query_one(ConversationView)
        streaming_widget = self.call_from_thread(conv.start_streaming)
        if self._agent is not None:
            messages = self._agent.get_conversation_context(include_system_prompt=True)
        else:
            messages = [{"role": "user", "content": user_text}]
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

