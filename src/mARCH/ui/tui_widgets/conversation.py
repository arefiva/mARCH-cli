"""Scrollable conversation view widget for mARCH TUI."""

from textual.containers import VerticalScroll
from textual.widgets import Static

from .message import MessageRole, MessageWidget

_PLACEHOLDER = "No messages yet — start typing below."


class ConversationView(VerticalScroll):
    """Scrollable container that renders a list of MessageWidget instances."""

    DEFAULT_CSS = """
    ConversationView {
        height: 1fr;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._placeholder: Static | None = None
        self._streaming_widget: MessageWidget | None = None

    def compose(self):  # type: ignore[override]
        self._placeholder = Static(
            f"[dim]{_PLACEHOLDER}[/dim]",
            markup=True,
            id="conversation-placeholder",
        )
        yield self._placeholder

    def add_message(self, role: MessageRole, content: str) -> None:
        """Mount a new MessageWidget and scroll to it."""
        self._remove_placeholder()
        widget = MessageWidget(role=role, content=content)
        self.mount(widget)
        self.call_after_refresh(self.scroll_end, animate=False)

    def start_streaming(self, role: MessageRole = MessageRole.ASSISTANT) -> MessageWidget:
        """Create a placeholder MessageWidget for streaming and return it."""
        self._remove_placeholder()
        widget = MessageWidget(role=role, content="")
        self._streaming_widget = widget
        self.mount(widget)
        self.call_after_refresh(self.scroll_end, animate=False)
        return widget

    def finish_streaming(self) -> None:
        """Mark the current streaming widget as complete."""
        self._streaming_widget = None

    def _remove_placeholder(self) -> None:
        if self._placeholder is not None:
            try:
                self._placeholder.remove()
            except Exception:
                pass
            self._placeholder = None
