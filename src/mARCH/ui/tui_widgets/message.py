"""Individual message widget for mARCH TUI conversations."""

from enum import Enum

from textual.widgets import Static


class MessageRole(str, Enum):
    """Role of a conversation message."""

    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"
    TOOL = "TOOL"


_ROLE_STYLES: dict[MessageRole, str] = {
    MessageRole.USER: "bold cyan",
    MessageRole.ASSISTANT: "bold green",
    MessageRole.SYSTEM: "bold yellow",
    MessageRole.TOOL: "bold magenta",
}


class MessageWidget(Static):
    """Renders a single conversation message with a role label and content."""

    DEFAULT_CSS = """
    MessageWidget {
        margin: 0 0 1 0;
        padding: 0 1;
    }
    """

    def __init__(self, role: MessageRole, content: str) -> None:
        self._role = role
        self._content = content
        label = f"[{_ROLE_STYLES[role]}]{role.value}[/]"
        super().__init__(f"{label}  {content}", markup=True)

    def append_chunk(self, text: str) -> None:
        """Append a streaming text chunk to this message's content."""
        self._content += text
        label = f"[{_ROLE_STYLES[self._role]}]{self._role.value}[/]"
        self.update(f"{label}  {self._content}")
