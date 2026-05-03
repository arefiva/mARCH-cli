"""Animated spinner widget for mARCH TUI."""

from textual.widgets import Static

SPINNER_FRAMES: list[str] = list("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")


class SpinnerWidget(Static):
    """Animated braille spinner that cycles on a timer interval."""

    DEFAULT_CSS = """
    SpinnerWidget {
        width: 3;
        content-align: center middle;
    }
    """

    def __init__(self) -> None:
        super().__init__(SPINNER_FRAMES[0])
        self._frame_index = 0
        self._running = False

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.1, self._advance_frame, pause=True)

    def start(self) -> None:
        """Start the spinner animation."""
        self._running = True
        self._timer.resume()

    def stop(self) -> None:
        """Stop the spinner and clear it."""
        self._running = False
        self._timer.pause()
        self.update(" ")

    def _advance_frame(self) -> None:
        self._frame_index = (self._frame_index + 1) % len(SPINNER_FRAMES)
        self.update(SPINNER_FRAMES[self._frame_index])
