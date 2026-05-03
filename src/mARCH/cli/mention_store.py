"""Mention store for tracking @file and /skill references.

Stores mentioned files and skills from user input for AI context injection.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import re


@dataclass
class FileMention:
    """Represents a file mentioned with @."""

    display_text: str  # e.g., "@src/main.py"
    full_path: str  # Absolute path
    relative_path: str  # Relative path
    start_index: int  # Position in input text
    is_directory: bool = False


@dataclass
class SkillMention:
    """Represents a skill mentioned with /."""

    name: str  # e.g., "git"
    args: List[str]  # Arguments after skill name
    start_index: int  # Position in input text


class MentionStore:
    """Track and resolve mentions in user input."""

    def __init__(self, search_root: Optional[Path] = None):
        """Initialize mention store.

        Args:
            search_root: Root directory for resolving file paths
        """
        self._file_mentions: Dict[int, FileMention] = {}  # keyed by start_index
        self._skill_mentions: Dict[int, SkillMention] = {}
        self._search_root = search_root or Path.cwd()

    def add_file_mention(
        self,
        display_text: str,
        full_path: str,
        start_index: int,
        is_directory: bool = False,
    ) -> None:
        """Add a file mention.

        Args:
            display_text: Display text (e.g., "@src/main.py")
            full_path: Absolute file path
            start_index: Position in input text
            is_directory: Whether this is a directory
        """
        # Calculate relative path
        try:
            rel_path = str(Path(full_path).relative_to(self._search_root))
        except ValueError:
            rel_path = full_path

        mention = FileMention(
            display_text=display_text,
            full_path=full_path,
            relative_path=rel_path,
            start_index=start_index,
            is_directory=is_directory,
        )
        self._file_mentions[start_index] = mention

    def add_skill_mention(
        self, name: str, args: List[str], start_index: int
    ) -> None:
        """Add a skill mention.

        Args:
            name: Skill name
            args: Skill arguments
            start_index: Position in input text
        """
        mention = SkillMention(name=name, args=args, start_index=start_index)
        self._skill_mentions[start_index] = mention

    def get_file_mentions(self) -> List[FileMention]:
        """Get all file mentions sorted by position.

        Returns:
            List of FileMention objects
        """
        return sorted(self._file_mentions.values(), key=lambda m: m.start_index)

    def get_skill_mentions(self) -> List[SkillMention]:
        """Get all skill mentions sorted by position.

        Returns:
            List of SkillMention objects
        """
        return sorted(self._skill_mentions.values(), key=lambda m: m.start_index)

    def clear(self) -> None:
        """Clear all stored mentions."""
        self._file_mentions.clear()
        self._skill_mentions.clear()

    def parse_mentions_from_text(self, text: str) -> None:
        """Parse @file and /skill mentions from text.

        Args:
            text: User input text
        """
        self.clear()

        # Parse @file mentions: @path/to/file
        # Match @ followed by non-whitespace characters
        file_pattern = r"@(\S+)"
        for match in re.finditer(file_pattern, text):
            rel_path = match.group(1)
            # Remove trailing punctuation
            rel_path = rel_path.rstrip(".,;:!?)")

            full_path = str(self._search_root / rel_path)
            is_dir = Path(full_path).is_dir() if Path(full_path).exists() else False

            self.add_file_mention(
                display_text=f"@{rel_path}",
                full_path=full_path,
                start_index=match.start(),
                is_directory=is_dir,
            )

    def get_file_contents(self, max_size: int = 50000) -> Dict[str, str]:
        """Get contents of mentioned files.

        Args:
            max_size: Maximum file size in bytes to read

        Returns:
            Dictionary of relative_path -> content
        """
        contents = {}

        for mention in self.get_file_mentions():
            if mention.is_directory:
                continue

            path = Path(mention.full_path)
            if not path.exists() or not path.is_file():
                continue

            try:
                # Check file size
                if path.stat().st_size > max_size:
                    contents[mention.relative_path] = (
                        f"[File too large: {path.stat().st_size} bytes]"
                    )
                    continue

                content = path.read_text(encoding="utf-8", errors="replace")
                contents[mention.relative_path] = content
            except Exception as e:
                contents[mention.relative_path] = f"[Error reading file: {e}]"

        return contents

    def format_context_for_ai(self) -> str:
        """Format file mentions as context for AI.

        Returns:
            Formatted string with file contents
        """
        contents = self.get_file_contents()

        if not contents:
            return ""

        parts = ["### Referenced Files\n"]

        for rel_path, content in contents.items():
            parts.append(f"#### {rel_path}\n```\n{content}\n```\n")

        return "\n".join(parts)


# Singleton instance
_store_instance: Optional[MentionStore] = None


def get_mention_store(search_root: Optional[Path] = None) -> MentionStore:
    """Get or create the mention store instance.

    Args:
        search_root: Root directory for resolving paths

    Returns:
        MentionStore instance
    """
    global _store_instance
    if _store_instance is None:
        _store_instance = MentionStore(search_root)
    return _store_instance
