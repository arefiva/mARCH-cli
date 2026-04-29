"""
GitHub integration for Copilot CLI.

Provides centralized access to GitHub authentication, API, and context extraction.
"""

from pathlib import Path

from copilot.github_api import GitHubAPIClient
from copilot.github_auth import GitHubAuthenticator, GitHubToken
from copilot.github_context import GitContextExtractor, RepositoryContext
from copilot.logging_config import get_logger

logger = get_logger(__name__)


class GitHubIntegration:
    """Main GitHub integration class."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """
        Initialize GitHub integration.

        Args:
            config_dir: Configuration directory (defaults to ~/.copilot)
        """
        if config_dir is None:
            config_dir = Path.home() / ".copilot"

        self.authenticator = GitHubAuthenticator(config_dir)
        self.api_client = GitHubAPIClient(self.authenticator)
        self.context_extractor = GitContextExtractor()

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with GitHub."""
        return self.authenticator.is_authenticated()

    def authenticate_with_pat(self, token: str) -> bool:
        """
        Authenticate with Personal Access Token.

        Args:
            token: GitHub PAT

        Returns:
            True if successful, False otherwise
        """
        return self.authenticator.authenticate_with_pat(token)

    def get_auth_token(self) -> GitHubToken | None:
        """Get current authentication token."""
        return self.authenticator.get_token()

    def logout(self) -> None:
        """Log out (clear authentication token)."""
        self.authenticator.clear_token()
        logger.info("Logged out from GitHub")

    def get_current_repo_context(self) -> RepositoryContext | None:
        """
        Get GitHub repository context from current directory.

        Returns:
            RepositoryContext if in a Git repo, None otherwise
        """
        return self.context_extractor.extract_context()

    def get_user_info(self) -> dict | None:
        """
        Get authenticated user information.

        Returns:
            User info dict if authenticated, None otherwise
        """
        return self.api_client.get_user()

    # Expose API client methods for convenience
    def get_user_repositories(self, limit: int = 10):
        """Get user's repositories."""
        return self.api_client.get_user_repositories(limit)

    def get_repository(self, owner: str, repo: str):
        """Get repository information."""
        return self.api_client.get_repository(owner, repo)

    def get_issues(self, owner: str, repo: str, state: str = "open", limit: int = 10):
        """Get repository issues."""
        return self.api_client.get_issues(owner, repo, state, limit)

    def get_pull_requests(self, owner: str, repo: str, state: str = "open", limit: int = 10):
        """Get repository pull requests."""
        return self.api_client.get_pull_requests(owner, repo, state, limit)

    def get_issue(self, owner: str, repo: str, issue_number: int):
        """Get specific issue."""
        return self.api_client.get_issue(owner, repo, issue_number)

    def get_pull_request(self, owner: str, repo: str, pr_number: int):
        """Get specific pull request."""
        return self.api_client.get_pull_request(owner, repo, pr_number)

