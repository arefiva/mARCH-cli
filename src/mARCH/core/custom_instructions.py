"""Loader for project-level custom instructions.

Reads `.github/copilot-instructions.md` from the repository root and
returns its content for injection into the system prompt.
"""

from pathlib import Path


class CustomInstructionsLoader:
    """Loads custom instructions from the repository's copilot instructions file."""

    _PATH = Path(".github") / "copilot-instructions.md"

    @classmethod
    def load(cls, repo_root: "str | Path") -> "str | None":
        """Read custom instructions from repo_root/.github/copilot-instructions.md.

        Args:
            repo_root: Path to the repository root directory.

        Returns:
            File contents as a string, or None if the file does not exist.
        """
        instructions_path = Path(repo_root) / cls._PATH
        try:
            return instructions_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError:
            return None
