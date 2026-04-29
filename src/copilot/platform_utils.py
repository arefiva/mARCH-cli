"""
Platform-specific utilities for cross-platform compatibility.

Provides abstraction for platform detection, console handling, and
OS-specific operations.
"""

import platform
import sys
from enum import Enum


class OSType(str, Enum):
    """Supported operating systems."""

    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


class PlatformInfo:
    """Information about the current platform."""

    def __init__(self) -> None:
        """Initialize platform info."""
        self._system = platform.system()
        self._platform = sys.platform
        self._release = platform.release()
        self._version = platform.version()
        self._machine = platform.machine()

    @property
    def os_type(self) -> OSType:
        """Get the operating system type."""
        if self._system == "Windows":
            return OSType.WINDOWS
        elif self._system == "Darwin":
            return OSType.MACOS
        elif self._system == "Linux":
            return OSType.LINUX
        return OSType.UNKNOWN

    @property
    def system(self) -> str:
        """Get system name."""
        return self._system

    @property
    def platform(self) -> str:
        """Get platform identifier."""
        return self._platform

    @property
    def release(self) -> str:
        """Get OS release."""
        return self._release

    @property
    def version(self) -> str:
        """Get OS version."""
        return self._version

    @property
    def machine(self) -> str:
        """Get machine architecture."""
        return self._machine

    @property
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return self.os_type == OSType.WINDOWS

    @property
    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return self.os_type == OSType.MACOS

    @property
    def is_linux(self) -> bool:
        """Check if running on Linux."""
        return self.os_type == OSType.LINUX

    @property
    def is_unix_like(self) -> bool:
        """Check if running on Unix-like system (macOS or Linux)."""
        return self.is_macos or self.is_linux

    def __str__(self) -> str:
        """String representation."""
        return f"{self.system} {self.release}"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"PlatformInfo(os={self.os_type}, system={self.system}, "
            f"machine={self.machine})"
        )


class ConsoleInfo:
    """Information about the console environment."""

    def __init__(self) -> None:
        """Initialize console info."""
        self._is_tty = sys.stdout.isatty()
        self._is_interactive = hasattr(sys, "ps1")
        self.width = self._get_console_width()
        self.height = self._get_console_height()

    def _get_console_width(self) -> int:
        """Get console width in characters."""
        try:
            import shutil
            return shutil.get_terminal_size().columns or 80
        except Exception:
            return 80

    def _get_console_height(self) -> int:
        """Get console height in lines."""
        try:
            import shutil
            return shutil.get_terminal_size().lines or 24
        except Exception:
            return 24

    @property
    def is_tty(self) -> bool:
        """Check if stdout is a TTY."""
        return self._is_tty

    @property
    def is_interactive(self) -> bool:
        """Check if running in interactive mode."""
        return self._is_interactive

    @property
    def supports_unicode(self) -> bool:
        """Check if console supports Unicode."""
        encoding = sys.stdout.encoding or ""
        return "utf" in encoding.lower() or "ascii" not in encoding.lower()

    @property
    def supports_colors(self) -> bool:
        """Check if console supports ANSI colors."""
        # Check environment variables
        if "TERM" in __import__("os").environ:
            term = __import__("os").environ["TERM"]
            return term != "dumb" and term != ""
        # Default to true on Unix-like systems
        return PlatformInfo().is_unix_like

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"ConsoleInfo(tty={self.is_tty}, interactive={self.is_interactive}, "
            f"size={self.width}x{self.height}, unicode={self.supports_unicode})"
        )


class ExecutablePermissions:
    """Utilities for managing executable permissions."""

    @staticmethod
    def make_executable(path: str) -> None:
        """
        Make a file executable.

        Args:
            path: File path
        """
        import os
        import stat

        if PlatformInfo().is_windows:
            # On Windows, executable bit isn't meaningful
            return

        try:
            current_permissions = os.stat(path).st_mode
            os.chmod(path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass

    @staticmethod
    def is_executable(path: str) -> bool:
        """
        Check if a file is executable.

        Args:
            path: File path

        Returns:
            True if file is executable
        """
        import os

        return os.path.isfile(path) and os.access(path, os.X_OK)


class PathUtils:
    """Platform-aware path utilities."""

    @staticmethod
    def get_app_data_dir() -> str:
        """
        Get application data directory.

        Returns:
            Path to app data directory
        """
        import os
        from pathlib import Path

        platform_info = PlatformInfo()

        if platform_info.is_windows:
            # Windows: %APPDATA%\copilot or %LOCALAPPDATA%\copilot
            appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
            if appdata:
                return str(Path(appdata) / "copilot")
        elif platform_info.is_macos:
            # macOS: ~/Library/Application Support/copilot
            return str(Path.home() / "Library" / "Application Support" / "copilot")

        # Linux and fallback: ~/.copilot
        return str(Path.home() / ".copilot")

    @staticmethod
    def get_cache_dir() -> str:
        """
        Get cache directory.

        Returns:
            Path to cache directory
        """
        import os
        from pathlib import Path

        platform_info = PlatformInfo()

        if platform_info.is_windows:
            cache = os.environ.get("TEMP") or os.environ.get("TMP")
            if cache:
                return str(Path(cache) / "copilot-cache")
        elif platform_info.is_macos:
            return str(Path.home() / "Library" / "Caches" / "copilot")

        # Linux and fallback
        cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        return str(Path(cache) / "copilot")

    @staticmethod
    def get_config_dir() -> str:
        """
        Get configuration directory.

        Returns:
            Path to config directory
        """
        import os
        from pathlib import Path

        platform_info = PlatformInfo()

        if platform_info.is_windows:
            config = os.environ.get("APPDATA")
            if config:
                return str(Path(config) / "copilot")
        elif platform_info.is_macos:
            return str(Path.home() / "Library" / "Preferences" / "copilot")

        # Linux and fallback
        config = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        return str(Path(config) / "copilot")


# Global instances
_platform_info: PlatformInfo | None = None
_console_info: ConsoleInfo | None = None


def get_platform_info() -> PlatformInfo:
    """Get or create global platform info instance."""
    global _platform_info
    if _platform_info is None:
        _platform_info = PlatformInfo()
    return _platform_info


def get_console_info() -> ConsoleInfo:
    """Get or create global console info instance."""
    global _console_info
    if _console_info is None:
        _console_info = ConsoleInfo()
    return _console_info
