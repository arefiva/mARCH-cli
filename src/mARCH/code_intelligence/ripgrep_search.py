"""
Ripgrep integration for fast code search.

Provides high-performance code searching using ripgrep (rg) subprocess,
with support for regex patterns, file type filtering, and result parsing.
"""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchMatch:
    """A single search match in code."""

    file_path: str
    line_number: int
    column: int
    line_text: str
    match_text: str


class RipgrepSearcher:
    """Code search using ripgrep (rg) command."""

    def __init__(self, rg_path: str = "rg"):
        """
        Initialize ripgrep searcher.

        Args:
            rg_path: Path to rg executable (defaults to 'rg' in PATH)
        """
        self.rg_path = rg_path
        self._verify_rg_available()

    def _verify_rg_available(self) -> None:
        """Check if ripgrep is installed and available."""
        try:
            subprocess.run(
                [self.rg_path, "--version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                f"ripgrep not found at '{self.rg_path}'. "
                "Install with: cargo install ripgrep or apt-get install ripgrep"
            )

    def search(
        self,
        pattern: str,
        directory: str = ".",
        file_types: list[str] | None = None,
        max_results: int = 100,
        ignore_case: bool = False,
        regex: bool = True,
    ) -> list[SearchMatch]:
        """
        Search for pattern in code files.

        Args:
            pattern: Search pattern (regex by default)
            directory: Root directory to search
            file_types: File extensions to search (e.g., ['py', 'js']), None for all
            max_results: Maximum number of results to return
            ignore_case: Case-insensitive search
            regex: Use regex pattern (default True)

        Returns:
            List of SearchMatch objects
        """
        cmd = [self.rg_path, "--json"]

        if ignore_case:
            cmd.append("-i")

        if not regex:
            cmd.append("-F")  # Fixed string, not regex

        if file_types:
            for ftype in file_types:
                cmd.extend(["--type", ftype])

        cmd.extend(["-m", str(max_results)])
        cmd.extend([pattern, directory])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                text=True,
                cwd=directory,
            )
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []

        matches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            try:
                data = json.loads(line)
                if data.get("type") == "match":
                    match_data = data.get("data", {})
                    submatch = match_data.get("submatches", [{}])[0]

                    matches.append(
                        SearchMatch(
                            file_path=match_data.get("path", {}).get(
                                "text", ""
                            ),
                            line_number=match_data.get("line_number", 0),
                            column=submatch.get("start", 0),
                            line_text=match_data.get("lines", {}).get(
                                "text", ""
                            ),
                            match_text=submatch.get("match", {}).get(
                                "text", ""
                            ),
                        )
                    )
            except (json.JSONDecodeError, KeyError):
                continue

        return matches

    def search_symbol(
        self,
        symbol: str,
        directory: str = ".",
        language: str | None = None,
    ) -> list[SearchMatch]:
        """
        Search for symbol definition/usage (word boundary matching).

        Args:
            symbol: Symbol name to search for
            directory: Root directory to search
            language: Language/file type to filter (e.g., 'py', 'js')

        Returns:
            List of SearchMatch objects
        """
        # Use word boundary regex: \bsymbol\b
        pattern = rf"\b{re.escape(symbol)}\b"
        file_types = [language] if language else None

        return self.search(
            pattern,
            directory=directory,
            file_types=file_types,
            regex=True,
        )

    def search_imports(
        self, directory: str = ".", language: str = "py"
    ) -> list[SearchMatch]:
        """
        Search for imports in code files.

        Args:
            directory: Root directory to search
            language: Language to search (default: Python)

        Returns:
            List of import statement matches
        """
        if language == "py":
            pattern = r"^(import|from)\s+"
        elif language in ("js", "ts"):
            pattern = r"^(import|export|require)\s+"
        elif language == "go":
            pattern = r'^import\s*'
        elif language == "rs":
            pattern = r"^use\s+"
        else:
            return []

        return self.search(
            pattern, directory=directory, file_types=[language], regex=True
        )

    def search_in_file(
        self,
        pattern: str,
        file_path: str,
        ignore_case: bool = False,
    ) -> list[SearchMatch]:
        """
        Search for pattern within a specific file.

        Args:
            pattern: Search pattern (regex)
            file_path: Path to file to search
            ignore_case: Case-insensitive search

        Returns:
            List of SearchMatch objects
        """
        path = Path(file_path)
        if not path.exists():
            return []

        directory = str(path.parent)
        return self.search(
            pattern,
            directory=directory,
            ignore_case=ignore_case,
            regex=True,
        )

    def find_functions(
        self, directory: str = ".", language: str = "py"
    ) -> list[SearchMatch]:
        """
        Find function definitions in code.

        Args:
            directory: Root directory to search
            language: Language to search (default: Python)

        Returns:
            List of function definition matches
        """
        if language == "py":
            pattern = r"^def\s+\w+"
        elif language in ("js", "ts"):
            pattern = r"^(function|const|let|var)\s+\w+.*=.*\s*=>"
        elif language == "go":
            pattern = r"^func\s+\w+"
        elif language == "rs":
            pattern = r"^fn\s+\w+"
        else:
            return []

        return self.search(
            pattern,
            directory=directory,
            file_types=[language],
            regex=True,
        )

    def find_classes(
        self, directory: str = ".", language: str = "py"
    ) -> list[SearchMatch]:
        """
        Find class definitions in code.

        Args:
            directory: Root directory to search
            language: Language to search (default: Python)

        Returns:
            List of class definition matches
        """
        if language == "py":
            pattern = r"^class\s+\w+"
        elif language in ("js", "ts"):
            pattern = r"^class\s+\w+"
        elif language == "go":
            pattern = r"^type\s+\w+\s+struct"
        elif language == "rs":
            pattern = r"^(struct|trait|impl)\s+\w+"
        else:
            return []

        return self.search(
            pattern,
            directory=directory,
            file_types=[language],
            regex=True,
        )

    def find_todos(self, directory: str = ".") -> list[SearchMatch]:
        """
        Find TODO comments in code files.

        Args:
            directory: Root directory to search

        Returns:
            List of TODO comment matches
        """
        pattern = r"(TODO|FIXME|HACK|XXX|NOTE):\s*"
        return self.search(pattern, directory=directory, regex=True)


# Singleton instance
_searcher_instance: RipgrepSearcher | None = None


def get_ripgrep_searcher() -> RipgrepSearcher | None:
    """Get or create singleton RipgrepSearcher instance."""
    global _searcher_instance
    if _searcher_instance is None:
        try:
            _searcher_instance = RipgrepSearcher()
        except RuntimeError:
            # ripgrep not available
            return None
    return _searcher_instance
