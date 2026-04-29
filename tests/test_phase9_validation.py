"""
Tests for Phase 9: Testing & Validation.

Tests system validation, health checks, and integration.
"""

import pytest

from copilot.validation import (
    HealthCheckResult,
    HealthChecker,
    DependencyAuditor,
    IntegrationValidator,
)


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_create_ok_result(self):
        """Test creating OK result."""
        result = HealthCheckResult(
            name="Test",
            status="ok",
            message="Everything is fine",
        )
        assert result.name == "Test"
        assert result.status == "ok"
        assert result.is_healthy() is True

    def test_create_warning_result(self):
        """Test creating warning result."""
        result = HealthCheckResult(
            name="Test",
            status="warning",
            message="Something to note",
        )
        assert result.status == "warning"
        assert result.is_healthy() is False

    def test_create_error_result(self):
        """Test creating error result."""
        result = HealthCheckResult(
            name="Test",
            status="error",
            message="Something is wrong",
        )
        assert result.status == "error"
        assert result.is_healthy() is False

    def test_result_with_details(self):
        """Test result with details."""
        details = {"key": "value"}
        result = HealthCheckResult(
            name="Test",
            status="ok",
            message="OK",
            details=details,
        )
        assert result.details == details

    def test_result_string_representation(self):
        """Test string representation."""
        result = HealthCheckResult(
            name="Test",
            status="ok",
            message="OK",
        )
        str_repr = str(result)
        assert "Test" in str_repr
        assert "OK" in str_repr


class TestHealthChecker:
    """Test HealthChecker class."""

    def test_create_health_checker(self):
        """Test creating health checker."""
        checker = HealthChecker()
        assert checker is not None
        assert checker.results == []

    def test_check_python_version(self):
        """Test Python version check."""
        checker = HealthChecker()
        result = checker.check_python_version()
        
        assert result.name == "Python Version"
        assert result.status in ["ok", "error"]

    def test_check_required_dependencies(self):
        """Test required dependencies check."""
        checker = HealthChecker()
        result = checker.check_required_dependencies()
        
        assert result.name == "Required Dependencies"
        assert result.status in ["ok", "error", "warning"]

    def test_check_optional_dependencies(self):
        """Test optional dependencies check."""
        checker = HealthChecker()
        result = checker.check_optional_dependencies()
        
        assert result.name == "Optional Dependencies"
        assert result.status in ["ok", "warning"]

    def test_check_platform_support(self):
        """Test platform support check."""
        checker = HealthChecker()
        result = checker.check_platform_support()
        
        assert result.name == "Platform Support"
        assert result.status in ["ok", "warning"]

    def test_check_configuration(self):
        """Test configuration check."""
        checker = HealthChecker()
        result = checker.check_configuration()
        
        assert result.name == "Configuration"
        assert result.status in ["ok", "error"]

    def test_check_state_persistence(self):
        """Test state persistence check."""
        checker = HealthChecker()
        result = checker.check_state_persistence()
        
        assert result.name == "State Persistence"
        assert result.status in ["ok", "error"]

    def test_run_all_checks(self):
        """Test running all checks."""
        checker = HealthChecker()
        results = checker.run_all_checks()
        
        assert len(results) >= 5
        assert all(isinstance(r, HealthCheckResult) for r in results)

    def test_get_summary(self):
        """Test getting check summary."""
        checker = HealthChecker()
        checker.run_all_checks()
        summary = checker.get_summary()
        
        assert isinstance(summary, dict)
        assert "ok" in summary
        assert "warning" in summary
        assert "error" in summary

    def test_is_healthy(self):
        """Test is_healthy check."""
        checker = HealthChecker()
        checker.run_all_checks()
        
        is_healthy = checker.is_healthy()
        assert isinstance(is_healthy, bool)


class TestDependencyAuditor:
    """Test DependencyAuditor class."""

    def test_get_installed_packages(self):
        """Test getting installed packages."""
        packages = DependencyAuditor.get_installed_packages()
        
        assert isinstance(packages, dict)
        # Should have common packages
        assert len(packages) > 0

    def test_check_outdated(self):
        """Test checking outdated packages."""
        outdated = DependencyAuditor.check_outdated()
        
        # Should return a list (even if empty)
        assert isinstance(outdated, list)

    def test_check_security_vulnerabilities(self):
        """Test checking security vulnerabilities."""
        vulnerabilities = DependencyAuditor.check_security_vulnerabilities()
        
        # Should return a list (even if empty or if pip-audit not installed)
        assert isinstance(vulnerabilities, list)


class TestIntegrationValidator:
    """Test IntegrationValidator class."""

    def test_validate_cli_module(self):
        """Test CLI module validation."""
        result = IntegrationValidator.validate_cli_module()
        assert isinstance(result, bool)
        assert result is True

    def test_validate_github_integration(self):
        """Test GitHub integration validation."""
        result = IntegrationValidator.validate_github_integration()
        assert isinstance(result, bool)

    def test_validate_code_intelligence(self):
        """Test code intelligence validation."""
        result = IntegrationValidator.validate_code_intelligence()
        assert isinstance(result, bool)

    def test_validate_tui_module(self):
        """Test TUI module validation."""
        result = IntegrationValidator.validate_tui_module()
        assert isinstance(result, bool)

    def test_validate_agent_module(self):
        """Test agent module validation."""
        result = IntegrationValidator.validate_agent_module()
        assert isinstance(result, bool)

    def test_validate_config_module(self):
        """Test config module validation."""
        result = IntegrationValidator.validate_config_module()
        assert isinstance(result, bool)
        assert result is True

    def test_validate_state_module(self):
        """Test state module validation."""
        result = IntegrationValidator.validate_state_module()
        assert isinstance(result, bool)
        assert result is True

    def test_validate_platform_module(self):
        """Test platform module validation."""
        result = IntegrationValidator.validate_platform_module()
        assert isinstance(result, bool)
        assert result is True

    def test_validate_all(self):
        """Test validating all modules."""
        results = IntegrationValidator.validate_all()
        
        assert isinstance(results, dict)
        assert "cli" in results
        assert "github" in results
        assert "code_intelligence" in results
        assert "tui" in results
        assert "agent" in results
        assert "config" in results
        assert "state" in results
        assert "platform" in results


class TestIntegration:
    """Integration tests for Phase 9."""

    def test_health_check_workflow(self):
        """Test complete health check workflow."""
        checker = HealthChecker()
        results = checker.run_all_checks()
        
        # Should have multiple results
        assert len(results) >= 5
        
        # All results should have required fields
        for result in results:
            assert result.name is not None
            assert result.status in ["ok", "warning", "error"]
            assert result.message is not None

    def test_module_validation_workflow(self):
        """Test complete module validation workflow."""
        validations = IntegrationValidator.validate_all()
        
        # Should validate all modules
        assert len(validations) == 8
        
        # Core modules should be available
        assert validations.get("config") is True
        assert validations.get("state") is True
        assert validations.get("platform") is True

    def test_dependency_audit_workflow(self):
        """Test dependency audit workflow."""
        packages = DependencyAuditor.get_installed_packages()
        
        # Should have packages
        assert len(packages) > 0
        
        # Should be able to check outdated
        outdated = DependencyAuditor.check_outdated()
        assert isinstance(outdated, list)

    def test_overall_system_health(self):
        """Test overall system health."""
        # Run health checks
        checker = HealthChecker()
        health_results = checker.run_all_checks()
        
        # Validate modules
        validations = IntegrationValidator.validate_all()
        
        # Should be able to get Python version
        python_check = next(
            (r for r in health_results if r.name == "Python Version"),
            None,
        )
        assert python_check is not None
        assert python_check.status == "ok"
        
        # Should have dependencies
        deps_check = next(
            (r for r in health_results if r.name == "Required Dependencies"),
            None,
        )
        assert deps_check is not None
        assert deps_check.status in ["ok", "warning"]
        
        # Core modules should validate
        assert validations["config"] is True
        assert validations["platform"] is True
