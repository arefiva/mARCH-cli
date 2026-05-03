"""Header widget for mARCH Textual TUI."""

from importlib.metadata import version

try:
    _version = version("mARCH")
except Exception:
    try:
        from mARCH import __version__ as _version  # type: ignore[assignment]
    except Exception:
        _version = "0.1.0"

from textual.widgets import Static


class HeaderWidget(Static):
    """Displays the mARCH project name, version, and current mode."""

    DEFAULT_CSS = """
    HeaderWidget {
        height: 3;
        background: $primary-darken-3;
        color: $text;
        content-align: center middle;
        text-style: bold;
        padding: 0 2;
    }
    """

    def __init__(self, mode: str = "INTERACTIVE") -> None:
        self._mode = mode
        super().__init__()

    def render(self) -> str:  # type: ignore[override]
        try:
            width = self.app.size.width
        except Exception:
            width = 0
        mascot = "🤖 " if width >= 80 else ""
        return f"{mascot}mARCH  v{_version}  [{self._mode}]"

    def set_mode(self, mode: str) -> None:
        """Update the displayed mode indicator."""
        self._mode = mode
        self.refresh()
