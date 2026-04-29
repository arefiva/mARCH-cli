"""
Exception hierarchy for mARCH CLI.

Defines custom exceptions for error handling across the application.
"""


class mARCHError(Exception):
    """Base exception for all mARCH CLI errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        """
        Initialize a mARCHError.

        Args:
            message: Human-readable error message
            details: Additional error details
        """
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}\n{self.details}"
        return self.message


class ConfigurationError(mARCHError):
    """Raised when configuration is invalid or missing."""

    pass


class AuthenticationError(mARCHError):
    """Raised when authentication fails or is missing."""

    pass


class GitHubError(mARCHError):
    """Raised when GitHub API operations fail."""

    pass


class LSPError(mARCHError):
    """Raised when LSP (Language Server Protocol) operations fail."""

    pass


class CodeSearchError(mARCHError):
    """Raised when code search operations fail."""

    pass


class TreeSitterError(mARCHError):
    """Raised when tree-sitter parsing fails."""

    pass


class CLIError(mARCHError):
    """Raised when CLI operations fail."""

    pass


class UIError(mARCHError):
    """Raised when UI/Terminal operations fail."""

    pass
