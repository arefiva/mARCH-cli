"""Git-aware file search for mARCH CLI.

Provides file search functionality that respects git repository boundaries
and supports fuzzy matching for @ file references.
"""

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class FileMatch:
    """Represents a file match result."""

    path: str  # Absolute path
    relative_path: str  # Path relative to search root
    score: float  # Match score (0-1, higher is better)
    is_directory: bool = False

    def __repr__(self) -> str:
        kind = "[DIR]" if self.is_directory else ""
        return f"FileMatch({self.relative_path}{kind}, score={self.score:.2f})"


class GitAwareFileSearch:
    """Search files within git repository or CWD boundaries."""

    def __init__(self, working_directory: Optional[str] = None):
        """Initialize file search.

        Args:
            working_directory: Starting directory for search (defaults to CWD)
        """
        self._cwd = Path(working_directory or os.getcwd()).resolve()
        self._git_root: Optional[Path] = None
        self._file_cache: Optional[List[str]] = None
        self._cache_root: Optional[Path] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl_seconds: float = 30  # Refresh cache every 30 seconds
        self._max_files: int = 10000  # Limit results to prevent memory spikes

    @property
    def search_root(self) -> Path:
        """Get the search root (git root or CWD)."""
        if self._git_root is None:
            self._git_root = self._find_git_root()
        return self._git_root or self._cwd

    def _find_git_root(self) -> Optional[Path]:
        """Find the git repository root.

        Returns:
            Path to git root, or None if not in a git repository
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self._cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return Path(result.stdout.strip()).resolve()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def _get_git_files(self) -> List[str]:
        """Get list of files tracked by git.

        Returns:
            List of relative file paths
        """
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=self.search_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split("\n") if f]
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return []

    def _get_untracked_files(self) -> List[str]:
        """Get untracked files (not in .gitignore).

        Returns:
            List of relative file paths
        """
        try:
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.search_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split("\n") if f]
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return []

    def _get_all_files(self, include_untracked: bool = True) -> List[str]:
        """Get all searchable files.

        Args:
            include_untracked: Include untracked files (not in .gitignore)

        Returns:
            List of relative file paths (limited to _max_files)
        """
        # Check cache validity (TTL-based)
        now = time.time()
        if (
            self._file_cache is not None
            and self._cache_root == self.search_root
            and self._cache_timestamp is not None
            and (now - self._cache_timestamp) < self._cache_ttl_seconds
        ):
            return self._file_cache

        files = []

        if self._git_root:
            # In git repo: use git ls-files (with limit)
            files = self._get_git_files()
            if include_untracked:
                files.extend(self._get_untracked_files())
        else:
            # Not in git: walk directory (limit depth to avoid huge scans)
            files = self._walk_directory(max_depth=5)

        # Limit to _max_files to prevent memory issues
        files = files[:self._max_files]

        # Cache results with timestamp
        self._file_cache = files
        self._cache_root = self.search_root
        self._cache_timestamp = now
        return files

    def _walk_directory(self, max_depth: int = 5) -> List[str]:
        """Walk directory tree (fallback when not in git).

        Args:
            max_depth: Maximum directory depth to traverse

        Returns:
            List of relative file paths (limited to _max_files)
        """
        files = []
        root = self.search_root

        for dirpath, dirnames, filenames in os.walk(root):
            # Check if we've hit the file limit
            if len(files) >= self._max_files:
                dirnames.clear()  # Stop traversing
                break

            # Calculate depth
            rel_dir = Path(dirpath).relative_to(root)
            depth = len(rel_dir.parts)

            if depth > max_depth:
                dirnames.clear()  # Don't descend further
                continue

            # Skip hidden directories
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]

            for filename in filenames:
                if not filename.startswith("."):
                    rel_path = Path(dirpath).relative_to(root) / filename
                    files.append(str(rel_path))
                    # Early exit if we hit limit
                    if len(files) >= self._max_files:
                        break

        return files

    def get_directories(self) -> List[str]:
        """Get list of directories for navigation.

        Returns:
            List of directory paths relative to search root
        """
        dirs = set()
        for file_path in self._get_all_files():
            parts = Path(file_path).parts
            # Add all parent directories
            for i in range(1, len(parts)):
                dirs.add(str(Path(*parts[:i])))

        return sorted(dirs)

    def search(
        self, query: str, max_results: int = 20, include_dirs: bool = True
    ) -> List[FileMatch]:
        """Search for files matching query.

        Args:
            query: Search query (fuzzy matched against paths)
            max_results: Maximum number of results to return
            include_dirs: Include directories in results

        Returns:
            List of FileMatch objects sorted by score (descending)
        """
        files = self._get_all_files()
        results = []

        query_lower = query.lower()

        for file_path in files:
            score = self._fuzzy_score(query_lower, file_path.lower())
            if score > 0:
                abs_path = str(self.search_root / file_path)
                results.append(
                    FileMatch(
                        path=abs_path,
                        relative_path=file_path,
                        score=score,
                        is_directory=False,
                    )
                )

        # Add directories if requested
        if include_dirs:
            for dir_path in self.get_directories():
                score = self._fuzzy_score(query_lower, dir_path.lower())
                if score > 0:
                    abs_path = str(self.search_root / dir_path)
                    results.append(
                        FileMatch(
                            path=abs_path,
                            relative_path=f"{dir_path}/",
                            score=score * 0.9,  # Slight penalty for directories
                            is_directory=True,
                        )
                    )

        # Sort by score (descending) and limit results
        results.sort(key=lambda m: (-m.score, m.relative_path))
        return results[:max_results]

    def _fuzzy_score(self, query: str, target: str) -> float:
        """Calculate fuzzy match score.

        Simple scoring:
        - Exact prefix match: 1.0
        - Contains match: 0.7
        - Subsequence match: 0.3-0.6
        - No match: 0.0

        Args:
            query: Search query (lowercase)
            target: Target string (lowercase)

        Returns:
            Match score (0-1)
        """
        if not query:
            return 0.5  # Empty query matches everything moderately

        if target.startswith(query):
            return 1.0

        # Check filename match (higher priority than path match)
        filename = Path(target).name
        if filename.startswith(query):
            return 0.95

        if query in target:
            return 0.7

        if query in filename:
            return 0.8

        # Subsequence match
        query_idx = 0
        for char in target:
            if query_idx < len(query) and char == query[query_idx]:
                query_idx += 1

        if query_idx == len(query):
            # All query chars found in order
            return 0.3 + (0.3 * query_idx / len(target))

        return 0.0

    def invalidate_cache(self) -> None:
        """Invalidate the file cache (call when files may have changed)."""
        self._file_cache = None
        self._cache_root = None
        self._cache_timestamp = None


# Singleton instance
_search_instance: Optional[GitAwareFileSearch] = None


def get_file_search(working_directory: Optional[str] = None) -> GitAwareFileSearch:
    """Get or create the file search instance.

    Args:
        working_directory: Working directory for search

    Returns:
        GitAwareFileSearch instance
    """
    global _search_instance
    if _search_instance is None:
        _search_instance = GitAwareFileSearch(working_directory)
    return _search_instance
