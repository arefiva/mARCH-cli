"""
TUI layout and window management components.

Provides screen layout, paneling, and multi-window management for complex TUI.
"""

from enum import Enum

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text


class PanelLocation(str, Enum):
    """Panel location in layout."""

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


class TUILayout:
    """Main TUI layout manager."""

    def __init__(self, console: Console | None = None):
        """
        Initialize TUI layout.

        Args:
            console: Rich Console instance
        """
        self.console = console or Console()
        self.layout = Layout()
        self._setup_default_layout()

    def _setup_default_layout(self) -> None:
        """Set up default layout with header, body, footer."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

    def set_header(self, text: str, style: str = "bold cyan") -> None:
        """
        Set header content.

        Args:
            text: Header text
            style: Rich style
        """
        header_text = Text(text, style=style)
        self.layout["header"].update(Panel(header_text))

    def set_footer(self, text: str, style: str = "dim") -> None:
        """
        Set footer content.

        Args:
            text: Footer text
            style: Rich style
        """
        footer_text = Text(text, style=style)
        self.layout["footer"].update(Panel(footer_text))

    def set_body(self, renderable) -> None:
        """
        Set body content.

        Args:
            renderable: Rich renderable object (Panel, Text, Table, etc.)
        """
        self.layout["body"].update(renderable)

    def get_layout(self) -> Layout:
        """Get the current layout object."""
        return self.layout

    def print_layout(self) -> None:
        """Print the entire layout to console."""
        self.console.print(self.layout)

    def create_two_column_layout(self) -> None:
        """Create a two-column layout."""
        # Split into header/body/footer vertically first
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        # Then split main horizontally
        self.layout["main"].split(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1),
        )

    def create_three_column_layout(self) -> None:
        """Create a three-column layout."""
        # Split into header/body/footer vertically first
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        # Then split main into three columns horizontally
        self.layout["main"].split(
            Layout(name="left", ratio=1),
            Layout(name="center", ratio=2),
            Layout(name="right", ratio=1),
        )


class Window:
    """Individual window/panel in TUI."""

    def __init__(
        self,
        name: str,
        title: str | None = None,
        border_style: str = "blue",
    ):
        """
        Initialize window.

        Args:
            name: Window identifier
            title: Window title
            border_style: Border style
        """
        self.name = name
        self.title = title or name
        self.border_style = border_style
        self.content = ""
        self.is_active = False

    def set_content(self, content: str) -> None:
        """Set window content."""
        self.content = content

    def get_panel(self) -> Panel:
        """Get window as Rich Panel."""
        panel = Panel(
            self.content,
            title=self.title,
            border_style=self.border_style if self.is_active else "dim",
            expand=True,
        )
        return panel

    def activate(self) -> None:
        """Activate window (highlight)."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate window."""
        self.is_active = False

    def toggle_active(self) -> None:
        """Toggle active state."""
        self.is_active = not self.is_active


class WindowManager:
    """Manage multiple windows."""

    def __init__(self, console: Console | None = None):
        """
        Initialize window manager.

        Args:
            console: Rich Console instance
        """
        self.console = console or Console()
        self.windows: dict[str, Window] = {}
        self.active_window: str | None = None

    def create_window(
        self,
        name: str,
        title: str | None = None,
        border_style: str = "blue",
    ) -> Window:
        """
        Create a new window.

        Args:
            name: Window identifier
            title: Window title
            border_style: Border style

        Returns:
            Created Window object
        """
        window = Window(name, title, border_style)
        self.windows[name] = window

        # Set first window as active
        if self.active_window is None:
            self.active_window = name
            window.activate()

        return window

    def get_window(self, name: str) -> Window | None:
        """Get window by name."""
        return self.windows.get(name)

    def set_active_window(self, name: str) -> bool:
        """
        Set active window.

        Args:
            name: Window name

        Returns:
            True if window exists and was activated
        """
        if name not in self.windows:
            return False

        # Deactivate previous window
        if self.active_window and self.active_window in self.windows:
            self.windows[self.active_window].deactivate()

        # Activate new window
        self.active_window = name
        self.windows[name].activate()
        return True

    def get_active_window(self) -> Window | None:
        """Get currently active window."""
        if self.active_window:
            return self.windows.get(self.active_window)
        return None

    def update_window_content(self, name: str, content: str) -> bool:
        """
        Update window content.

        Args:
            name: Window name
            content: New content

        Returns:
            True if window exists and was updated
        """
        if name in self.windows:
            self.windows[name].set_content(content)
            return True
        return False

    def list_windows(self) -> list[str]:
        """Get list of window names."""
        return list(self.windows.keys())

    def render_all_windows(self) -> None:
        """Render all windows to console."""
        from rich.columns import Columns

        panels = [w.get_panel() for w in self.windows.values()]
        columns = Columns(panels)
        self.console.print(columns)

    def clear_windows(self) -> None:
        """Clear all windows."""
        self.windows.clear()
        self.active_window = None


class StatusBar:
    """Status bar display."""

    def __init__(self, console: Console | None = None):
        """
        Initialize status bar.

        Args:
            console: Rich Console instance
        """
        self.console = console or Console()
        self.messages: dict[str, str] = {}

    def set_status(self, key: str, message: str) -> None:
        """Set status message."""
        self.messages[key] = message

    def get_status(self, key: str) -> str | None:
        """Get status message."""
        return self.messages.get(key)

    def clear_status(self, key: str) -> None:
        """Clear specific status message."""
        if key in self.messages:
            del self.messages[key]

    def render_status_bar(self) -> None:
        """Render status bar."""
        if not self.messages:
            return

        status_text = " | ".join(self.messages.values())
        bar = Panel(
            status_text,
            style="dim",
            expand=False,
        )
        self.console.print(bar)


def get_tui_layout() -> TUILayout:
    """Get or create TUI layout instance."""
    if not hasattr(get_tui_layout, "_instance"):
        get_tui_layout._instance = TUILayout()
    return get_tui_layout._instance


def get_window_manager() -> WindowManager:
    """Get or create window manager instance."""
    if not hasattr(get_window_manager, "_instance"):
        get_window_manager._instance = WindowManager()
    return get_window_manager._instance


def get_status_bar() -> StatusBar:
    """Get or create status bar instance."""
    if not hasattr(get_status_bar, "_instance"):
        get_status_bar._instance = StatusBar()
    return get_status_bar._instance
