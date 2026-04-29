"""
GitHub API wrapper for Copilot CLI.

Provides high-level access to GitHub API operations.
"""

from dataclasses import dataclass
from typing import Any

from github import Github, GithubException
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository

from github_auth import GitHubAuthenticator
from src.copilot.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RepositoryInfo:
    """Information about a repository."""

    owner: str
    name: str
    url: str
    description: str | None = None
    is_private: bool = False
    language: str | None = None
    stars: int = 0

    @staticmethod
    def from_repo(repo: Repository) -> "RepositoryInfo":
        """Create from PyGithub Repository object."""
        return RepositoryInfo(
            owner=repo.owner.login,
            name=repo.name,
            url=repo.html_url,
            description=repo.description,
            is_private=repo.private,
            language=repo.language,
            stars=repo.stargazers_count,
        )


@dataclass
class IssueInfo:
    """Information about an issue."""

    number: int
    title: str
    state: str  # "open" or "closed"
    author: str
    url: str
    body: str | None = None
    labels: list[str] = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = []

    @staticmethod
    def from_issue(issue: Issue) -> "IssueInfo":
        """Create from PyGithub Issue object."""
        return IssueInfo(
            number=issue.number,
            title=issue.title,
            state=issue.state,
            author=issue.user.login,
            url=issue.html_url,
            body=issue.body,
            labels=[label.name for label in issue.labels],
        )


@dataclass
class PRInfo:
    """Information about a pull request."""

    number: int
    title: str
    state: str  # "open", "closed", "merged"
    author: str
    url: str
    body: str | None = None
    additions: int = 0
    deletions: int = 0
    commits: int = 0

    @staticmethod
    def from_pr(pr: PullRequest) -> "PRInfo":
        """Create from PyGithub PullRequest object."""
        return PRInfo(
            number=pr.number,
            title=pr.title,
            state=pr.state,
            author=pr.user.login,
            url=pr.html_url,
            body=pr.body,
            additions=pr.additions,
            deletions=pr.deletions,
            commits=pr.commits,
        )


class GitHubAPIClient:
    """High-level GitHub API client."""

    def __init__(self, authenticator: GitHubAuthenticator | None = None) -> None:
        """
        Initialize GitHub API client.

        Args:
            authenticator: GitHubAuthenticator instance
        """
        self.authenticator = authenticator or GitHubAuthenticator()
        self._client: Github | None = None

    def _get_client(self) -> Github:
        """Get or create PyGithub client."""
        if self._client is not None:
            return self._client

        token = self.authenticator.get_token()
        if token:
            self._client = Github(token.token)
        else:
            self._client = Github()  # Unauthenticated

        return self._client

    def get_user(self) -> dict[str, Any] | None:
        """
        Get current authenticated user.

        Returns:
            User info dict if authenticated, None otherwise
        """
        try:
            user = self._get_client().get_user()
            return {
                "login": user.login,
                "name": user.name,
                "email": user.email,
                "bio": user.bio,
                "avatar_url": user.avatar_url,
                "public_repos": user.public_repos,
                "followers": user.followers,
                "following": user.following,
            }
        except GithubException as e:
            logger.error(f"Failed to get user: {e}")
            return None

    def get_repository(self, owner: str, repo: str) -> RepositoryInfo | None:
        """
        Get repository information.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            RepositoryInfo if found, None otherwise
        """
        try:
            gh = self._get_client()
            repository = gh.get_repo(f"{owner}/{repo}")
            return RepositoryInfo.from_repo(repository)
        except GithubException as e:
            logger.error(f"Failed to get repository {owner}/{repo}: {e}")
            return None

    def get_user_repositories(self, limit: int = 10) -> list[RepositoryInfo]:
        """
        Get repositories for authenticated user.

        Args:
            limit: Maximum number of repositories to return

        Returns:
            List of RepositoryInfo objects
        """
        try:
            user = self._get_client().get_user()
            repos = []
            for repo in user.get_repos().get_page(0):
                repos.append(RepositoryInfo.from_repo(repo))
                if len(repos) >= limit:
                    break
            return repos
        except GithubException as e:
            logger.error(f"Failed to get user repositories: {e}")
            return []

    def get_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10,
    ) -> list[IssueInfo]:
        """
        Get issues for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state ("open", "closed", "all")
            limit: Maximum number of issues to return

        Returns:
            List of IssueInfo objects
        """
        try:
            gh = self._get_client()
            repository = gh.get_repo(f"{owner}/{repo}")
            issues = []
            for issue in repository.get_issues(state=state):
                issues.append(IssueInfo.from_issue(issue))
                if len(issues) >= limit:
                    break
            return issues
        except GithubException as e:
            logger.error(f"Failed to get issues for {owner}/{repo}: {e}")
            return []

    def get_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10,
    ) -> list[PRInfo]:
        """
        Get pull requests for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state ("open", "closed", "all")
            limit: Maximum number of PRs to return

        Returns:
            List of PRInfo objects
        """
        try:
            gh = self._get_client()
            repository = gh.get_repo(f"{owner}/{repo}")
            prs = []
            for pr in repository.get_pulls(state=state):
                prs.append(PRInfo.from_pr(pr))
                if len(prs) >= limit:
                    break
            return prs
        except GithubException as e:
            logger.error(f"Failed to get pull requests for {owner}/{repo}: {e}")
            return []

    def get_issue(self, owner: str, repo: str, issue_number: int) -> IssueInfo | None:
        """
        Get a specific issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            IssueInfo if found, None otherwise
        """
        try:
            gh = self._get_client()
            repository = gh.get_repo(f"{owner}/{repo}")
            issue = repository.get_issue(issue_number)
            return IssueInfo.from_issue(issue)
        except GithubException as e:
            logger.error(f"Failed to get issue #{issue_number}: {e}")
            return None

    def get_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> PRInfo | None:
        """
        Get a specific pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            PRInfo if found, None otherwise
        """
        try:
            gh = self._get_client()
            repository = gh.get_repo(f"{owner}/{repo}")
            pr = repository.get_pull(pr_number)
            return PRInfo.from_pr(pr)
        except GithubException as e:
            logger.error(f"Failed to get pull request #{pr_number}: {e}")
            return None
