"""
GitHub authentication module.

Handles OAuth and PAT authentication with GitHub.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console

from mARCH.exceptions import AuthenticationError
from mARCH.logging_config import get_logger

logger = get_logger(__name__)
console = Console()


@dataclass
class GitHubToken:
    """Represents a GitHub authentication token."""

    token: str
    token_type: str  # "pat" or "oauth"
    created_at: datetime
    expires_at: datetime | None = None

    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "token": self.token,
            "token_type": self.token_type,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @staticmethod
    def from_dict(data: dict) -> "GitHubToken":
        """Create from dictionary."""
        return GitHubToken(
            token=data["token"],
            token_type=data["token_type"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
        )


class GitHubAuthenticator:
    """Handles GitHub authentication."""

    TOKEN_FILE_NAME = "github_token.json"

    def __init__(self, config_dir: Path | None = None) -> None:
        """
        Initialize GitHub authenticator.

        Args:
            config_dir: Configuration directory path (defaults to ~/.march)
        """
        if config_dir is None:
            config_dir = Path.home() / ".march"
        self.config_dir = config_dir
        self.token_file = config_dir / self.TOKEN_FILE_NAME
        self._token: GitHubToken | None = None

    def get_token(self) -> GitHubToken | None:
        """
        Get stored GitHub token.

        Returns:
            GitHubToken if available, None otherwise
        """
        # Check environment variables first
        env_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if env_token:
            return GitHubToken(
                token=env_token,
                token_type="env",
                created_at=datetime.now(),
            )

        # Check cache
        if self._token is not None:
            return self._token

        # Load from file
        if self.token_file.exists():
            try:
                with open(self.token_file) as f:
                    data = json.load(f)
                self._token = GitHubToken.from_dict(data)
                return self._token
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load stored token: {e}")

        return None

    def store_token(self, token: str, token_type: str = "pat") -> None:
        """
        Store GitHub token.

        Args:
            token: GitHub token string
            token_type: Type of token ("pat" or "oauth")
        """
        gh_token = GitHubToken(
            token=token,
            token_type=token_type,
            created_at=datetime.now(),
        )

        self.config_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.token_file, "w") as f:
                json.dump(gh_token.to_dict(), f, indent=2)
            os.chmod(self.token_file, 0o600)  # Restrict to user only
            self._token = gh_token
            logger.info("GitHub token stored successfully")
        except OSError as e:
            raise AuthenticationError(
                "Failed to store GitHub token",
                details=str(e),
            )

    def clear_token(self) -> None:
        """Clear stored GitHub token."""
        if self.token_file.exists():
            try:
                self.token_file.unlink()
                self._token = None
                logger.info("GitHub token cleared")
            except OSError as e:
                logger.warning(f"Failed to clear token: {e}")

    def authenticate_with_pat(self, token: str) -> bool:
        """
        Authenticate with a Personal Access Token.

        Args:
            token: GitHub PAT

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Verify token by making a simple API call
            headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
            response = httpx.get("https://api.github.com/user", headers=headers, timeout=10)

            if response.status_code == 200:
                self.store_token(token, "pat")
                logger.info("GitHub PAT authentication successful")
                return True
            else:
                logger.error(f"GitHub PAT authentication failed: {response.status_code}")
                return False

        except httpx.RequestError as e:
            logger.error(f"Network error during authentication: {e}")
            return False

    def get_user_info(self) -> dict | None:
        """
        Get authenticated user information.

        Returns:
            User info dict if authenticated, None otherwise
        """
        token = self.get_token()
        if not token:
            return None

        try:
            headers = {
                "Authorization": f"token {token.token}",
                "Accept": "application/vnd.github.v3+json",
            }
            response = httpx.get("https://api.github.com/user", headers=headers, timeout=10)

            if response.status_code == 200:
                result: dict[Any, Any] = response.json()
                return result
            else:
                logger.error(f"Failed to get user info: {response.status_code}")
                return None

        except httpx.RequestError as e:
            logger.error(f"Network error getting user info: {e}")
            return None

    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        token = self.get_token()
        if not token:
            return False

        if token.is_expired():
            return False

        return self.get_user_info() is not None
