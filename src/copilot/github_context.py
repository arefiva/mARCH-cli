"""
GitHub repository context extraction for Copilot CLI.

Extracts repository information from the current working directory.
"""

import subprocess
from pathlib import Path
from typing import Any

from src.copilot.logging_config import get_logger

logger = get_logger(__name__)


class RepositoryContext:
    """Represents context information about a repository."""

    def __init__(
        self,
        repo_root: Path,
        owner: str,
        name: str,
        url: str,
        branch: str = "main",
        is_dirty: bool = False,
    ) -> None:
        """
        Initialize repository context.

        Args:
            repo_root: Root path of the repository
            owner: Repository owner
            name: Repository name
            url: Repository URL
            branch: Current branch name
            is_dirty: Whether working directory has uncommitted changes
        """
        self.repo_root = repo_root
        self.owner = owner
        self.name = name
        self.url = url
        self.branch = branch
        self.is_dirty = is_dirty

    def __str__(self) -> str:
        return f"{self.owner}/{self.name} ({self.branch})"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "repo_root": str(self.repo_root),
            "owner": self.owner,
            "name": self.name,
            "url": self.url,
            "branch": self.branch,
            "is_dirty": self.is_dirty,
        }


class GitContextExtractor:
    """Extracts Git/GitHub context from the current working directory."""

    def __init__(self, cwd: Path | None = None) -> None:
        """
        Initialize context extractor.

        Args:
            cwd: Current working directory (defaults to Path.cwd())
        """
        self.cwd = cwd or Path.cwd()

    def find_git_root(self) -> Path | None:
        """
        Find the root directory of the Git repository.

        Returns:
            Path to git root if in a git repository, None otherwise
        """
        current = self.cwd.resolve()

        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent

        return None

    def get_remote_url(self) -> str | None:
        """
        Get the remote URL of the current repository.

        Returns:
            Remote URL if found, None otherwise
        """
        git_root = self.find_git_root()
        if not git_root:
            return None

        try:
            result = subprocess.run(
                ["git", "-C", str(git_root), "config", "remote.origin.url"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug(f"Failed to get remote URL: {e}")

        return None

    def get_current_branch(self) -> str | None:
        """
        Get the current Git branch.

        Returns:
            Branch name if found, None otherwise
        """
        git_root = self.find_git_root()
        if not git_root:
            return None

        try:
            result = subprocess.run(
                ["git", "-C", str(git_root), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug(f"Failed to get current branch: {e}")

        return None

    def is_dirty(self) -> bool:
        """
        Check if working directory has uncommitted changes.

        Returns:
            True if dirty, False otherwise
        """
        git_root = self.find_git_root()
        if not git_root:
            return False

        try:
            result = subprocess.run(
                ["git", "-C", str(git_root), "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return len(result.stdout.strip()) > 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug(f"Failed to check git status: {e}")

        return False

    def parse_github_url(self, url: str) -> tuple[str, str] | None:
        """
        Parse GitHub repository URL to extract owner and name.

        Args:
            url: GitHub URL (https or ssh format)

        Returns:
            Tuple of (owner, name) if valid GitHub URL, None otherwise
        """
        # Handle https://github.com/owner/repo.git
        if url.startswith("https://github.com/"):
            path = url.replace("https://github.com/", "").replace(".git", "")
            parts = path.split("/")
            if len(parts) == 2:
                return (parts[0], parts[1])

        # Handle git@github.com:owner/repo.git
        if url.startswith("git@github.com:"):
            path = url.replace("git@github.com:", "").replace(".git", "")
            parts = path.split("/")
            if len(parts) == 2:
                return (parts[0], parts[1])

        return None

    def extract_context(self) -> RepositoryContext | None:
        """
        Extract GitHub repository context from current directory.

        Returns:
            RepositoryContext if in a Git repository, None otherwise
        """
        git_root = self.find_git_root()
        if not git_root:
            return None

        remote_url = self.get_remote_url()
        if not remote_url:
            logger.warning("Git repository found but no remote URL configured")
            return None

        parsed = self.parse_github_url(remote_url)
        if not parsed:
            logger.warning(f"Remote URL is not a GitHub repository: {remote_url}")
            return None

        owner, name = parsed
        branch = self.get_current_branch() or "main"
        is_dirty = self.is_dirty()

        return RepositoryContext(
            repo_root=git_root,
            owner=owner,
            name=name,
            url=remote_url,
            branch=branch,
            is_dirty=is_dirty,
        )
