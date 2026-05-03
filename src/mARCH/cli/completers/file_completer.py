"""File path completer for mARCH CLI.

Provides autocomplete for @ file references using prompt_toolkit.
"""

from typing import Iterable, Optional

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from mARCH.cli.file_search import get_file_search, FileMatch


class FileCompleter(Completer):
    """Completer for @ file references."""

    def __init__(self, trigger_char: str = "@"):
        """Initialize file completer.

        Args:
            trigger_char: Character that triggers file completion
        """
        self.trigger_char = trigger_char
        self._file_search = get_file_search()

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        """Get file path completions.

        Args:
            document: Current document
            complete_event: Completion event

        Yields:
            Completion objects for matching files
        """
        text = document.text_before_cursor

        # Find the last @ trigger
        trigger_pos = text.rfind(self.trigger_char)
        if trigger_pos == -1:
            return

        # Extract query after @
        query = text[trigger_pos + 1 :]

        # Don't complete if there's a space after query (already completed)
        if " " in query:
            return

        # Search for matching files
        try:
            matches = self._file_search.search(query, max_results=15)
        except Exception:
            return

        for match in matches:
            # Build completion text
            completion_text = f"{self.trigger_char}{match.relative_path}"

            # Calculate how much to replace
            start_position = -(len(query) + 1)  # +1 for @

            # Add trailing space after completion
            display_text = match.relative_path
            if match.is_directory:
                display_text = f"📁 {match.relative_path}"
            else:
                # Add file icon based on extension
                ext = match.relative_path.rsplit(".", 1)[-1] if "." in match.relative_path else ""
                icons = {
                    "py": "🐍",
                    "js": "📜",
                    "ts": "📘",
                    "json": "📋",
                    "md": "📝",
                    "txt": "📄",
                    "yaml": "⚙️",
                    "yml": "⚙️",
                }
                icon = icons.get(ext, "📄")
                display_text = f"{icon} {match.relative_path}"

            yield Completion(
                text=f"{match.relative_path} ",  # Space after for next input
                start_position=start_position,
                display=display_text,
                display_meta=f"score: {match.score:.0%}",
            )

    def is_active(self, document: Document) -> bool:
        """Check if file completion should be active.

        Args:
            document: Current document

        Returns:
            True if @ was typed and completion should show
        """
        text = document.text_before_cursor
        trigger_pos = text.rfind(self.trigger_char)

        if trigger_pos == -1:
            return False

        # Check there's no space after the query
        query = text[trigger_pos + 1 :]
        return " " not in query
