"""Tests for extension permissions and sandboxing."""

import pytest

from mARCH.extension.contracts import ExtensionManifest, ExtensionPermission
from mARCH.extension.permissions import PermissionValidator
from mARCH.extension.sandbox import SandboxManager
from mARCH.extension.types import ExtensionType, SandboxLevel


class TestPermissionValidator:
    """Test permission validation."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return PermissionValidator()

    def test_grant_permission(self, validator):
        """Test granting permission."""
        perm = ExtensionPermission(type="file_read", resource="/home/user/test")
        validator.grant_permission("ext1", perm)

        assert validator.has_permission("ext1", "file_read", "/home/user/test")

    def test_revoke_permission(self, validator):
        """Test revoking permission."""
        perm = ExtensionPermission(type="file_read")
        validator.grant_permission("ext1", perm)
        validator.revoke_permission("ext1", perm)

        assert not validator.has_permission("ext1", "file_read")

    def test_deny_permission(self, validator):
        """Test denying permission."""
        perm = ExtensionPermission(type="network_read", resource="api.example.com")
        validator.grant_permission("ext1", perm)
        validator.deny_permission("ext1", perm)

        assert not validator.has_permission("ext1", "network_read", "api.example.com")

    def test_has_permission_not_granted(self, validator):
        """Test checking permission that wasn't granted."""
        assert not validator.has_permission("ext1", "file_write")

    def test_has_permission_no_resource_requirement(self, validator):
        """Test permission check without specific resource."""
        perm = ExtensionPermission(type="environment_vars")
        validator.grant_permission("ext1", perm)

        assert validator.has_permission("ext1", "environment_vars")

    def test_get_permissions(self, validator):
        """Test getting all permissions for extension."""
        perm1 = ExtensionPermission(type="file_read")
        perm2 = ExtensionPermission(type="network_read")
        validator.grant_permission("ext1", perm1)
        validator.grant_permission("ext1", perm2)

        perms = validator.get_permissions("ext1")
        assert len(perms) == 2

    def test_validate_manifest_permissions_valid(self, validator):
        """Test validating valid manifest permissions."""
        manifest = ExtensionManifest(
            name="test",
            version="1.0.0",
            display_name="Test",
            description="Test",
            type=ExtensionType.TOOL,
            entry_point="main.py",
            permissions=[
                ExtensionPermission(type="file_read"),
                ExtensionPermission(type="network_read"),
            ],
        )

        errors = validator.validate_manifest_permissions(manifest)
        assert errors == []

    def test_resource_matches_exact(self, validator):
        """Test exact resource matching."""
        assert PermissionValidator._resource_matches("/home/user", "/home/user")
        assert not PermissionValidator._resource_matches("/home/user", "/home/other")

    def test_resource_matches_wildcard_single(self, validator):
        """Test single-level wildcard matching."""
        pattern = "/home/*"
        assert PermissionValidator._resource_matches(pattern, "/home/file.txt")
        assert not PermissionValidator._resource_matches(pattern, "/home/dir/file.txt")

    def test_resource_matches_wildcard_recursive(self, validator):
        """Test recursive wildcard matching."""
        pattern = "/home/**"
        assert PermissionValidator._resource_matches(pattern, "/home/file.txt")
        assert PermissionValidator._resource_matches(pattern, "/home/dir/file.txt")
        assert PermissionValidator._resource_matches(
            pattern, "/home/dir/subdir/file.txt"
        )

    def test_resource_matches_none_pattern(self, validator):
        """Test None pattern matches anything."""
        assert PermissionValidator._resource_matches(None, "/any/path")


class TestSandboxManager:
    """Test sandbox management."""

    @pytest.fixture
    def sandbox(self):
        """Create a sandbox manager instance."""
        return SandboxManager()

    def create_manifest(
        self, name, sandbox_level=SandboxLevel.FILE_RESTRICTED, permissions=None
    ):
        """Helper to create manifest."""
        return ExtensionManifest(
            name=name,
            version="1.0.0",
            display_name=name,
            description=name,
            type=ExtensionType.TOOL,
            entry_point="main.py",
            sandbox_level=sandbox_level,
            permissions=permissions or [],
        )

    def test_setup_extension_trusted(self, sandbox):
        """Test setting up trusted extension."""
        manifest = self.create_manifest(
            "trusted", sandbox_level=SandboxLevel.NONE
        )

        errors = sandbox.setup_extension(manifest)
        assert errors == []
        assert sandbox.get_sandbox_level("trusted") == SandboxLevel.NONE

    def test_setup_extension_file_restricted(self, sandbox):
        """Test setting up file-restricted extension."""
        manifest = self.create_manifest(
            "restricted",
            sandbox_level=SandboxLevel.FILE_RESTRICTED,
            permissions=[
                ExtensionPermission(type="file_read", resource="/home/user/**")
            ],
        )

        errors = sandbox.setup_extension(manifest)
        assert errors == []
        assert (
            sandbox.get_sandbox_level("restricted")
            == SandboxLevel.FILE_RESTRICTED
        )

    def test_setup_extension_process_isolated(self, sandbox):
        """Test setting up process-isolated extension."""
        manifest = self.create_manifest(
            "isolated", sandbox_level=SandboxLevel.PROCESS_ISOLATED
        )

        errors = sandbox.setup_extension(manifest)
        assert errors == []
        limits = sandbox.get_resource_limits("isolated")
        assert limits["max_memory_mb"] == 512

    def test_check_file_access_trusted(self, sandbox):
        """Test file access for trusted extension."""
        manifest = self.create_manifest(
            "trusted", sandbox_level=SandboxLevel.NONE
        )
        sandbox.setup_extension(manifest)

        from pathlib import Path

        assert sandbox.check_file_access("trusted", Path("/any/path"), "read")
        assert sandbox.check_file_access("trusted", Path("/any/path"), "write")

    def test_check_file_access_restricted_allowed(self, sandbox):
        """Test allowed file access for restricted extension."""
        manifest = self.create_manifest(
            "restricted",
            permissions=[
                ExtensionPermission(type="file_read", resource="/home/user/**")
            ],
        )
        sandbox.setup_extension(manifest)

        from pathlib import Path

        assert sandbox.check_file_access(
            "restricted", Path("/home/user/file.txt"), "read"
        )

    def test_check_file_access_restricted_denied(self, sandbox):
        """Test denied file access for restricted extension."""
        manifest = self.create_manifest(
            "restricted",
            permissions=[
                ExtensionPermission(type="file_read", resource="/home/user/**")
            ],
        )
        sandbox.setup_extension(manifest)

        from pathlib import Path

        assert not sandbox.check_file_access(
            "restricted", Path("/etc/passwd"), "read"
        )

    def test_check_network_access_trusted(self, sandbox):
        """Test network access for trusted extension."""
        manifest = self.create_manifest(
            "trusted", sandbox_level=SandboxLevel.NONE
        )
        sandbox.setup_extension(manifest)

        assert sandbox.check_network_access("trusted", "any-domain.com")

    def test_check_network_access_restricted_allowed(self, sandbox):
        """Test allowed network access for restricted extension."""
        manifest = self.create_manifest(
            "restricted",
            permissions=[
                ExtensionPermission(type="network_read", resource="api.example.com")
            ],
        )
        sandbox.setup_extension(manifest)

        assert sandbox.check_network_access("restricted", "api.example.com")

    def test_check_network_access_restricted_denied(self, sandbox):
        """Test denied network access for restricted extension."""
        manifest = self.create_manifest(
            "restricted",
            permissions=[
                ExtensionPermission(type="network_read", resource="api.example.com")
            ],
        )
        sandbox.setup_extension(manifest)

        assert not sandbox.check_network_access("restricted", "evil.com")

    def test_get_resource_limits(self, sandbox):
        """Test getting resource limits."""
        manifest = self.create_manifest(
            "test", sandbox_level=SandboxLevel.PROCESS_ISOLATED
        )
        sandbox.setup_extension(manifest)

        limits = sandbox.get_resource_limits("test")
        assert limits["max_memory_mb"] == 512
        assert limits["max_cpu_percent"] == 50

    def test_enforce_limits_ok(self, sandbox):
        """Test enforcing limits when within bounds."""
        manifest = self.create_manifest(
            "test", sandbox_level=SandboxLevel.PROCESS_ISOLATED
        )
        sandbox.setup_extension(manifest)

        metrics = {"memory_mb": 256, "cpu_percent": 25, "open_files": 50}
        violations = sandbox.enforce_limits("test", metrics)
        assert violations == []

    def test_enforce_limits_memory_exceeded(self, sandbox):
        """Test enforcing memory limit."""
        manifest = self.create_manifest(
            "test", sandbox_level=SandboxLevel.PROCESS_ISOLATED
        )
        sandbox.setup_extension(manifest)

        metrics = {"memory_mb": 600, "cpu_percent": 25, "open_files": 50}
        violations = sandbox.enforce_limits("test", metrics)
        assert len(violations) > 0
        assert "Memory" in violations[0]

    def test_enforce_limits_cpu_exceeded(self, sandbox):
        """Test enforcing CPU limit."""
        manifest = self.create_manifest(
            "test", sandbox_level=SandboxLevel.PROCESS_ISOLATED
        )
        sandbox.setup_extension(manifest)

        metrics = {"memory_mb": 256, "cpu_percent": 75, "open_files": 50}
        violations = sandbox.enforce_limits("test", metrics)
        assert len(violations) > 0
        assert "CPU" in violations[0]

    def test_enforce_limits_trusted_no_limits(self, sandbox):
        """Test that trusted extensions have no limits."""
        manifest = self.create_manifest(
            "trusted", sandbox_level=SandboxLevel.NONE
        )
        sandbox.setup_extension(manifest)

        metrics = {
            "memory_mb": 999999,
            "cpu_percent": 999,
            "open_files": 999999,
        }
        violations = sandbox.enforce_limits("trusted", metrics)
        assert violations == []
