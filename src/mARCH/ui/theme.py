"""Theme dataclass and factory for the mARCH TUI.

Provides centralized color definitions supporting dark (default) and light modes.
"""

from dataclasses import dataclass

from . import colors as c


@dataclass(frozen=True)
class Theme:
    """Centralized color theme for the mARCH TUI."""

    brand: str
    text: str
    background: str
    accent: str
    border: str
    status_success: str
    status_error: str
    status_warning: str
    status_info: str
    mode_interactive: str
    mode_plan: str
    mode_autopilot: str
    mode_shell: str


_DARK_THEME = Theme(
    brand=c.BRAND,
    text=c.DARK_TEXT,
    background=c.DARK_BACKGROUND,
    accent=c.DARK_ACCENT,
    border=c.DARK_BORDER,
    status_success=c.STATUS_SUCCESS,
    status_error=c.STATUS_ERROR,
    status_warning=c.STATUS_WARNING,
    status_info=c.STATUS_INFO,
    mode_interactive=c.MODE_INTERACTIVE,
    mode_plan=c.MODE_PLAN,
    mode_autopilot=c.MODE_AUTOPILOT,
    mode_shell=c.MODE_SHELL,
)

_LIGHT_THEME = Theme(
    brand=c.BRAND,
    text=c.LIGHT_TEXT,
    background=c.LIGHT_BACKGROUND,
    accent=c.LIGHT_ACCENT,
    border=c.LIGHT_BORDER,
    status_success=c.STATUS_SUCCESS,
    status_error=c.STATUS_ERROR,
    status_warning=c.STATUS_WARNING,
    status_info=c.STATUS_INFO,
    mode_interactive=c.MODE_INTERACTIVE,
    mode_plan=c.MODE_PLAN,
    mode_autopilot=c.MODE_AUTOPILOT,
    mode_shell=c.MODE_SHELL,
)


def get_theme(dark: bool = True) -> Theme:
    """Return the active Theme instance.

    Args:
        dark: If True (default) return the dark theme; False returns light theme.
    """
    return _DARK_THEME if dark else _LIGHT_THEME
