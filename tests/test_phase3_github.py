"""
Tests for Phase 3: GitHub Integration.

Tests for authentication, API client, and context extraction.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from copilot.github_auth import GitHubAuthenticator, GitHubToken
from copilot.github_api import (
    GitHubAPIClient,
    RepositoryInfo,
    IssueInfo,
    PRInfo,
)
from copilot.github_context import GitContextExtractor, RepositoryContext
from copilot.github_integration import GitHubIntegration


class TestGitHubToken:
    """Tests for GitHubToken."""

    def test_token_creation(self):
        """Test GitHubToken creation."""
        token = GitHubToken(
            token="test_token",
            token_type="pat",
            created_at=datetime.now(),
        )
        assert token.token == "test_token"
        assert token.token_type == "pat"
        assert not token.is_expired()

    def test_token_serialization(self):
        """Test GitHubToken serialization."""
        token = GitHubToken(
            token="test_token",
            token_type="pat",
            created_at=datetime.now(),
        )
        data = token.to_dict()
        assert data["token"] == "test_token"
        assert data["token_type"] == "pat"

        restored = GitHubToken.from_dict(data)
        assert restored.token == token.token
        assert restored.token_type == token.token_type


class TestGitHubAuthenticator:
    """Tests for GitHubAuthenticator."""

    def test_authenticator_initialization(self, tmp_path):
        """Test authenticator initializes."""
        auth = GitHubAuthenticator(tmp_path)
        assert auth.config_dir == tmp_path
        assert auth.token_file == tmp_path / "github_token.json"

    def test_store_and_retrieve_token(self, tmp_path):
        """Test storing and retrieving tokens."""
        auth = GitHubAuthenticator(tmp_path)
        auth.store_token("test_token", "pat")

        token = auth.get_token()
        assert token is not None
        assert token.token == "test_token"
        assert token.token_type == "pat"

    def test_clear_token(self, tmp_path):
        """Test clearing token."""
        auth = GitHubAuthenticator(tmp_path)
        auth.store_token("test_token", "pat")
        assert auth.get_token() is not None

        auth.clear_token()
        assert auth.get_token() is None

    def test_env_token_priority(self, tmp_path, monkeypatch):
        """Test environment token takes priority."""
        monkeypatch.setenv("GH_TOKEN", "env_token")
        auth = GitHubAuthenticator(tmp_path)
        auth.store_token("file_token", "pat")

        token = auth.get_token()
        assert token.token == "env_token"
        assert token.token_type == "env"


class TestRepositoryContext:
    """Tests for RepositoryContext."""

    def test_context_creation(self):
        """Test RepositoryContext creation."""
        ctx = RepositoryContext(
            repo_root=Path("/home/user/repo"),
            owner="user",
            name="repo",
            url="https://github.com/user/repo",
            branch="main",
            is_dirty=False,
        )
        assert ctx.owner == "user"
        assert ctx.name == "repo"
        assert str(ctx) == "user/repo (main)"

    def test_context_to_dict(self):
        """Test RepositoryContext to_dict."""
        ctx = RepositoryContext(
            repo_root=Path("/home/user/repo"),
            owner="user",
            name="repo",
            url="https://github.com/user/repo",
        )
        data = ctx.to_dict()
        assert data["owner"] == "user"
        assert data["name"] == "repo"


class TestGitContextExtractor:
    """Tests for GitContextExtractor."""

    def test_extractor_initialization(self):
        """Test extractor initializes."""
        extractor = GitContextExtractor()
        assert extractor.cwd is not None

    def test_parse_https_url(self):
        """Test parsing HTTPS GitHub URL."""
        extractor = GitContextExtractor()
        result = extractor.parse_github_url("https://github.com/user/repo.git")
        assert result == ("user", "repo")

    def test_parse_ssh_url(self):
        """Test parsing SSH GitHub URL."""
        extractor = GitContextExtractor()
        result = extractor.parse_github_url("git@github.com:user/repo.git")
        assert result == ("user", "repo")

    def test_parse_invalid_url(self):
        """Test parsing invalid GitHub URL."""
        extractor = GitContextExtractor()
        result = extractor.parse_github_url("https://gitlab.com/user/repo.git")
        assert result is None


class TestRepositoryInfo:
    """Tests for RepositoryInfo."""

    def test_repository_info_creation(self):
        """Test RepositoryInfo creation."""
        info = RepositoryInfo(
            owner="user",
            name="repo",
            url="https://github.com/user/repo",
            stars=100,
        )
        assert info.owner == "user"
        assert info.stars == 100


class TestIssueInfo:
    """Tests for IssueInfo."""

    def test_issue_info_creation(self):
        """Test IssueInfo creation."""
        info = IssueInfo(
            number=1,
            title="Test Issue",
            state="open",
            author="user",
            url="https://github.com/user/repo/issues/1",
        )
        assert info.number == 1
        assert info.state == "open"


class TestPRInfo:
    """Tests for PRInfo."""

    def test_pr_info_creation(self):
        """Test PRInfo creation."""
        info = PRInfo(
            number=1,
            title="Test PR",
            state="open",
            author="user",
            url="https://github.com/user/repo/pull/1",
            additions=10,
            deletions=5,
        )
        assert info.number == 1
        assert info.additions == 10


class TestGitHubIntegration:
    """Tests for GitHubIntegration."""

    def test_integration_initialization(self, tmp_path):
        """Test GitHubIntegration initializes."""
        integration = GitHubIntegration(tmp_path)
        assert integration.authenticator is not None
        assert integration.api_client is not None
        assert integration.context_extractor is not None

    def test_integration_authentication_check(self, tmp_path):
        """Test authentication check."""
        integration = GitHubIntegration(tmp_path)
        assert not integration.is_authenticated()

    def test_integration_logout(self, tmp_path):
        """Test logout clears authentication."""
        integration = GitHubIntegration(tmp_path)
        integration.authenticator.store_token("test_token", "pat")
        assert integration.get_auth_token() is not None

        integration.logout()
        assert integration.get_auth_token() is None


class TestGitHubAPIClient:
    """Tests for GitHubAPIClient."""

    def test_api_client_initialization(self, tmp_path):
        """Test API client initializes."""
        auth = GitHubAuthenticator(tmp_path)
        client = GitHubAPIClient(auth)
        assert client.authenticator is not None
