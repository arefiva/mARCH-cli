"""
Cross-platform clipboard access.

Provides abstraction for reading and writing to system clipboard.
"""

import subprocess

from mARCH.exceptions import mARCHError
from mARCH.platform.platform_utils import get_platform_info


class ClipboardError(mARCHError):
    """Clipboard operation error."""

    pass


class ClipboardManager:
    """Manages clipboard operations across platforms."""

    def __init__(self) -> None:
        """Initialize clipboard manager."""
        self.platform_info = get_platform_info()
        self._test_clipboard()

    def _test_clipboard(self) -> None:
        """Test if clipboard is accessible."""
        try:
            # Try to write empty string to test
            self._write_system(b"")
        except Exception:
            pass

    def copy(self, text: str) -> None:
        """
        Copy text to clipboard.

        Args:
            text: Text to copy

        Raises:
            ClipboardError: If clipboard operation fails
        """
        try:
            data = text.encode("utf-8")
            self._write_system(data)
        except Exception as e:
            raise ClipboardError(
                "Failed to copy to clipboard",
                details=str(e),
            )

    def paste(self) -> str | None:
        """
        Paste text from clipboard.

        Returns:
            Text from clipboard, or None if empty or unavailable

        Raises:
            ClipboardError: If clipboard operation fails
        """
        try:
            data = self._read_system()
            if data:
                return data.decode("utf-8")
            return None
        except Exception as e:
            raise ClipboardError(
                "Failed to paste from clipboard",
                details=str(e),
            )

    def _write_system(self, data: bytes) -> None:
        """
        Write data to system clipboard.

        Args:
            data: Bytes to write
        """
        if self.platform_info.is_windows:
            self._write_windows(data)
        elif self.platform_info.is_macos:
            self._write_macos(data)
        else:
            self._write_linux(data)

    def _read_system(self) -> bytes:
        """
        Read data from system clipboard.

        Returns:
            Bytes from clipboard
        """
        if self.platform_info.is_windows:
            return self._read_windows()
        elif self.platform_info.is_macos:
            return self._read_macos()
        else:
            return self._read_linux()

    @staticmethod
    def _write_windows(data: bytes) -> None:
        """Write to Windows clipboard."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(data.decode("utf-8"))
            root.update()
            root.destroy()
        except Exception:
            # Fallback to PowerShell
            try:
                ps_command = (
                    f"Set-Clipboard -Value ([System.Text.Encoding]::UTF8.GetString("
                    f"@({','.join(str(b) for b in data)})))"
                )
                subprocess.run(
                    ["powershell", "-Command", ps_command],
                    check=True,
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                raise ClipboardError("Unable to access clipboard on Windows")

    @staticmethod
    def _read_windows() -> bytes:
        """Read from Windows clipboard."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            text = root.clipboard_get()
            root.destroy()
            return text.encode("utf-8")
        except Exception:
            # Fallback to PowerShell
            try:
                result = subprocess.run(
                    ["powershell", "-Command", "Get-Clipboard"],
                    check=True,
                    capture_output=True,
                    timeout=5,
                    text=True,
                )
                return result.stdout.encode("utf-8")
            except Exception:
                raise ClipboardError("Unable to access clipboard on Windows")

    @staticmethod
    def _write_macos(data: bytes) -> None:
        """Write to macOS clipboard via pbcopy."""
        try:
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            process.communicate(data, timeout=5)
            if process.returncode != 0:
                raise ClipboardError("pbcopy returned non-zero exit code")
        except Exception as e:
            raise ClipboardError(f"Failed to write to macOS clipboard: {e}")

    @staticmethod
    def _read_macos() -> bytes:
        """Read from macOS clipboard via pbpaste."""
        try:
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            return result.stdout
        except Exception as e:
            raise ClipboardError(f"Failed to read from macOS clipboard: {e}")

    @staticmethod
    def _write_linux(data: bytes) -> None:
        """Write to Linux clipboard via xclip or xsel."""
        for cmd in ["xclip", "xsel"]:
            try:
                if cmd == "xclip":
                    process = subprocess.Popen(
                        ["xclip", "-selection", "clipboard"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                else:  # xsel
                    process = subprocess.Popen(
                        ["xsel", "--clipboard", "--input"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                process.communicate(data, timeout=5)
                if process.returncode == 0:
                    return
            except FileNotFoundError:
                continue
            except Exception:
                continue

        raise ClipboardError(
            "No clipboard manager found. Install xclip or xsel."
        )

    @staticmethod
    def _read_linux() -> bytes:
        """Read from Linux clipboard via xclip or xsel."""
        for cmd in ["xclip", "xsel"]:
            try:
                if cmd == "xclip":
                    result = subprocess.run(
                        ["xclip", "-selection", "clipboard", "-o"],
                        capture_output=True,
                        timeout=5,
                        check=True,
                    )
                else:  # xsel
                    result = subprocess.run(
                        ["xsel", "--clipboard", "--output"],
                        capture_output=True,
                        timeout=5,
                        check=True,
                    )
                return result.stdout
            except FileNotFoundError:
                continue
            except Exception:
                continue

        raise ClipboardError(
            "No clipboard manager found. Install xclip or xsel."
        )


# Global instance
_clipboard_manager: ClipboardManager | None = None


def get_clipboard_manager() -> ClipboardManager:
    """Get or create global clipboard manager."""
    global _clipboard_manager
    if _clipboard_manager is None:
        _clipboard_manager = ClipboardManager()
    return _clipboard_manager
