"""Status bar widget for mARCH TUI."""

from textual.widgets import Static

STATUS_ICONS: dict[str, str] = {
    "success": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "●",
}

_STATUS_STYLES: dict[str, str] = {
    "success": "bold green",
    "error": "bold red",
    "warning": "bold yellow",
    "info": "bold blue",
}


class StatusBar(Static):
    """Footer status bar showing the current operation and status icon."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary-darken-3;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__("", markup=True)
        self._status_type = "info"
        self._message = ""

    def set_status(self, message: str, status_type: str = "info") -> None:
        """Update the status bar with a message and status type."""
        self._message = message
        self._status_type = status_type
        icon = STATUS_ICONS.get(status_type, STATUS_ICONS["info"])
        style = _STATUS_STYLES.get(status_type, "")
        self.update(f"[{style}]{icon}[/]  {message}")

    def clear(self) -> None:
        """Clear the status bar."""
        self._message = ""
        self.update("")
