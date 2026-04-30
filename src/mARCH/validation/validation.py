"""
Validation and verification utilities for system integrity.

Provides health checks, dependency verification, and system validation.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    name: str
    status: str  # "ok", "warning", "error"
    message: str
    details: dict[str, Any] | None = None

    def is_healthy(self) -> bool:
        """Check if result is healthy."""
        return self.status == "ok"

    def __str__(self) -> str:
        """String representation."""
        return f"[{self.status.upper()}] {self.name}: {self.message}"


class HealthChecker:
    """Performs system health checks."""

    def __init__(self) -> None:
        """Initialize health checker."""
        self.results: list[HealthCheckResult] = []

    def check_python_version(self) -> HealthCheckResult:
        """Check Python version compatibility."""
        import sys

        version = sys.version_info
        required_major = 3
        required_minor = 10

        if version.major >= required_major and version.minor >= required_minor:
            return HealthCheckResult(
                name="Python Version",
                status="ok",
                message=f"Python {version.major}.{version.minor}.{version.micro}",
                details={"version": f"{version.major}.{version.minor}.{version.micro}"},
            )
        else:
            return HealthCheckResult(
                name="Python Version",
                status="error",
                message=f"Python {version.major}.{version.minor} (requires 3.10+)",
                details={"version": f"{version.major}.{version.minor}"},
            )

    def check_required_dependencies(self) -> HealthCheckResult:
        """Check required dependencies."""
        required = {
            "typer": "CLI framework",
            "pydantic": "Data validation",
            "rich": "Terminal output",
            "github": "GitHub API",
        }

        missing = []
        available = []

        for module, description in required.items():
            try:
                __import__(module)
                available.append(module)
            except ImportError:
                missing.append(module)

        if not missing:
            return HealthCheckResult(
                name="Required Dependencies",
                status="ok",
                message="All required dependencies installed",
                details={"available": available},
            )
        else:
            return HealthCheckResult(
                name="Required Dependencies",
                status="error",
                message=f"Missing: {', '.join(missing)}",
                details={"available": available, "missing": missing},
            )

    def check_optional_dependencies(self) -> HealthCheckResult:
        """Check optional dependencies."""
        optional = {
            "anthropic": "Claude API",
            "tree_sitter": "Syntax parsing",
            "Pillow": "Image handling",
        }

        available = []
        missing = []

        for module, description in optional.items():
            try:
                __import__(module)
                available.append(module)
            except ImportError:
                missing.append(module)

        if len(available) == len(optional):
            return HealthCheckResult(
                name="Optional Dependencies",
                status="ok",
                message="All optional dependencies installed",
                details={"available": available},
            )
        elif len(available) > 0:
            return HealthCheckResult(
                name="Optional Dependencies",
                status="warning",
                message=f"Some optional dependencies missing: {', '.join(missing)}",
                details={"available": available, "missing": missing},
            )
        else:
            return HealthCheckResult(
                name="Optional Dependencies",
                status="warning",
                message="No optional dependencies installed",
                details={"available": available, "missing": missing},
            )

    def check_platform_support(self) -> HealthCheckResult:
        """Check platform support."""
        from mARCH.platform.platform_utils import OSType, get_platform_info

        platform = get_platform_info()

        if platform.os_type == OSType.UNKNOWN:
            return HealthCheckResult(
                name="Platform Support",
                status="warning",
                message="Unknown platform (may have limited support)",
                details={"os": platform.system},
            )
        else:
            return HealthCheckResult(
                name="Platform Support",
                status="ok",
                message=f"Supported platform: {platform.system}",
                details={"os": platform.system, "platform": platform.platform},
            )

    def check_configuration(self) -> HealthCheckResult:
        """Check configuration availability."""
        from mARCH.config.config import get_config_manager

        try:
            config = get_config_manager()
            config.ensure_config_dir()

            return HealthCheckResult(
                name="Configuration",
                status="ok",
                message="Configuration accessible",
                details={"config_dir": str(config.user_config_dir)},
            )
        except Exception as e:
            return HealthCheckResult(
                name="Configuration",
                status="error",
                message=f"Configuration error: {e}",
                details={"error": str(e)},
            )

    def check_state_persistence(self) -> HealthCheckResult:
        """Check state persistence."""
        from mARCH.state.state_persistence import get_state_manager

        try:
            manager = get_state_manager()
            manager.ensure_dirs()

            return HealthCheckResult(
                name="State Persistence",
                status="ok",
                message="State management operational",
                details={"base_dir": str(manager.base_dir)},
            )
        except Exception as e:
            return HealthCheckResult(
                name="State Persistence",
                status="error",
                message=f"State persistence error: {e}",
                details={"error": str(e)},
            )

    def run_all_checks(self) -> list[HealthCheckResult]:
        """Run all health checks."""
        self.results = [
            self.check_python_version(),
            self.check_required_dependencies(),
            self.check_optional_dependencies(),
            self.check_platform_support(),
            self.check_configuration(),
            self.check_state_persistence(),
        ]
        return self.results

    def get_summary(self) -> dict[str, int]:
        """Get summary of check results."""
        summary = {"ok": 0, "warning": 0, "error": 0}

        for result in self.results:
            summary[result.status] = summary.get(result.status, 0) + 1

        return summary

    def is_healthy(self) -> bool:
        """Check if all critical checks passed."""
        for result in self.results:
            if result.status == "error":
                return False
        return True


class DependencyAuditor:
    """Audits dependencies for security and compatibility."""

    @staticmethod
    def get_installed_packages() -> dict[str, str]:
        """Get all installed packages and versions."""
        import pkg_resources

        packages = {}
        for dist in pkg_resources.working_set:
            packages[dist.project_name] = dist.version
        return packages

    @staticmethod
    def check_outdated() -> list[dict[str, str]]:
        """Check for outdated packages."""
        try:
            import subprocess
            result = subprocess.run(
                ["pip", "list", "--outdated", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                import json
                deps: list[dict[str, str]] = json.loads(result.stdout)
                return deps
            return []
        except Exception:
            return []

    @staticmethod
    def check_security_vulnerabilities() -> list[dict[str, Any]]:
        """Check for known security vulnerabilities."""
        try:
            import subprocess
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                import json
                audit_result: dict[str, list[dict[str, Any]]] = json.loads(result.stdout)
                return audit_result.get("vulnerabilities", [])
            return []
        except Exception:
            return []


class IntegrationValidator:
    """Validates integration between components."""

    @staticmethod
    def validate_cli_module() -> bool:
        """Validate CLI module loads."""
        try:
            from mARCH import cli
            return hasattr(cli, "app") or hasattr(cli, "cli_main")
        except Exception:
            return False

    @staticmethod
    def validate_github_integration() -> bool:
        """Validate GitHub integration loads."""
        try:
            from mARCH import github_integration
            return hasattr(github_integration, "GitHubIntegration")
        except Exception:
            return False

    @staticmethod
    def validate_code_intelligence() -> bool:
        """Validate code intelligence loads."""
        try:
            from mARCH import code_intelligence
            return hasattr(code_intelligence, "CodeIntelligence")
        except Exception:
            return False

    @staticmethod
    def validate_tui_module() -> bool:
        """Validate TUI module loads."""
        try:
            from mARCH import tui
            return hasattr(tui, "mARCHTUI")
        except Exception:
            return False

    @staticmethod
    def validate_agent_module() -> bool:
        """Validate agent module loads."""
        try:
            from mARCH import agent_state
            return hasattr(agent_state, "AgentManager")
        except Exception:
            return False

    @staticmethod
    def validate_config_module() -> bool:
        """Validate configuration module loads."""
        try:
            from mARCH.config.config import get_config_manager
            return get_config_manager() is not None
        except Exception:
            return False

    @staticmethod
    def validate_state_module() -> bool:
        """Validate state persistence module loads."""
        try:
            from state_persistence import get_state_manager
            return get_state_manager() is not None
        except Exception:
            return False

    @staticmethod
    def validate_platform_module() -> bool:
        """Validate platform utilities module loads."""
        try:
            from platform_utils import get_platform_info
            return get_platform_info() is not None
        except Exception:
            return False

    @classmethod
    def validate_all(cls) -> dict[str, bool]:
        """Validate all modules."""
        return {
            "cli": cls.validate_cli_module(),
            "github": cls.validate_github_integration(),
            "code_intelligence": cls.validate_code_intelligence(),
            "tui": cls.validate_tui_module(),
            "agent": cls.validate_agent_module(),
            "config": cls.validate_config_module(),
            "state": cls.validate_state_module(),
            "platform": cls.validate_platform_module(),
        }
