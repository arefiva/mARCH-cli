"""
Exception hierarchy for Copilot CLI.

Defines custom exceptions for error handling across the application.
"""


class CopilotError(Exception):
    """Base exception for all Copilot CLI errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        """
        Initialize a CopilotError.

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


class ConfigurationError(CopilotError):
    """Raised when configuration is invalid or missing."""

    pass


class AuthenticationError(CopilotError):
    """Raised when authentication fails or is missing."""

    pass


class GitHubError(CopilotError):
    """Raised when GitHub API operations fail."""

    pass


class LSPError(CopilotError):
    """Raised when LSP (Language Server Protocol) operations fail."""

    pass


class CodeSearchError(CopilotError):
    """Raised when code search operations fail."""

    pass


class TreeSitterError(CopilotError):
    """Raised when tree-sitter parsing fails."""

    pass


class CLIError(CopilotError):
    """Raised when CLI operations fail."""

    pass


class UIError(CopilotError):
    """Raised when UI/Terminal operations fail."""

    pass
