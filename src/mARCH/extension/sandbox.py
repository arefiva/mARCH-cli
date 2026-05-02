"""Extension sandboxing and security management."""

import logging
from pathlib import Path
from typing import Optional

from .contracts import ExtensionManifest
from .permissions import PermissionValidator
from .types import PermissionType, SandboxLevel

logger = logging.getLogger(__name__)


class SandboxManager:
    """Manages sandboxing and resource limits for extensions."""

    def __init__(self):
        """Initialize sandbox manager."""
        self.permission_validator = PermissionValidator()
        self.sandbox_levels: dict[str, SandboxLevel] = {}
        self.file_whitelist: dict[str, list[Path]] = {}
        self.network_whitelist: dict[str, list[str]] = {}
        self.resource_limits: dict[str, dict[str, int]] = {}

    def setup_extension(self, manifest: ExtensionManifest) -> list[str]:
        """Set up sandbox for an extension based on manifest.

        Args:
            manifest: Extension manifest

        Returns:
            List of errors (empty if successful)
        """
        errors = []

        # Store sandbox level
        self.sandbox_levels[manifest.name] = manifest.sandbox_level

        # Grant declared permissions
        for permission in manifest.permissions:
            self.permission_validator.grant_permission(manifest.name, permission)

        # Validate permissions
        perm_errors = self.permission_validator.validate_manifest_permissions(manifest)
        errors.extend(perm_errors)

        # Set up file whitelist from permissions
        self._setup_file_whitelist(manifest)

        # Set up network whitelist from permissions
        self._setup_network_whitelist(manifest)

        # Set up resource limits based on sandbox level
        self._setup_resource_limits(manifest)

        logger.debug(f"Set up sandbox for {manifest.name} at level {manifest.sandbox_level}")
        return errors

    def _setup_file_whitelist(self, manifest: ExtensionManifest) -> None:
        """Set up file system whitelist from manifest permissions.

        Args:
            manifest: Extension manifest
        """
        whitelist = []

        for permission in manifest.permissions:
            if permission.type == "file_read" and permission.resource:
                whitelist.append(Path(permission.resource))
            elif permission.type == "file_write" and permission.resource:
                whitelist.append(Path(permission.resource))

        # Add extension directory
        if whitelist:
            self.file_whitelist[manifest.name] = whitelist

    def _setup_network_whitelist(self, manifest: ExtensionManifest) -> None:
        """Set up network whitelist from manifest permissions.

        Args:
            manifest: Extension manifest
        """
        whitelist = []

        for permission in manifest.permissions:
            if permission.type == "network_read" and permission.resource:
                whitelist.append(permission.resource)

        if whitelist:
            self.network_whitelist[manifest.name] = whitelist

    def _setup_resource_limits(self, manifest: ExtensionManifest) -> None:
        """Set up resource limits based on sandbox level.

        Args:
            manifest: Extension manifest
        """
        limits = {}

        if manifest.sandbox_level == SandboxLevel.PROCESS_ISOLATED:
            # Strict limits for process-isolated extensions
            limits["max_memory_mb"] = 512
            limits["max_cpu_percent"] = 50
            limits["max_open_files"] = 100
        elif manifest.sandbox_level == SandboxLevel.FILE_RESTRICTED:
            # Moderate limits
            limits["max_memory_mb"] = 1024
            limits["max_cpu_percent"] = 100
            limits["max_open_files"] = 1024
        else:
            # No limits for trusted extensions
            limits["max_memory_mb"] = 0
            limits["max_cpu_percent"] = 0
            limits["max_open_files"] = 0

        self.resource_limits[manifest.name] = limits

    def check_file_access(
        self, extension_name: str, path: Path, access_type: str = "read"
    ) -> bool:
        """Check if extension can access a file.

        Args:
            extension_name: Name of extension
            path: Path to check
            access_type: Type of access ("read" or "write")

        Returns:
            True if access is allowed, False otherwise
        """
        sandbox_level = self.sandbox_levels.get(extension_name)

        if sandbox_level == SandboxLevel.NONE:
            return True  # Full access

        # Check permissions
        permission_type: PermissionType = (
            "file_write" if access_type == "write" else "file_read"
        )

        return self.permission_validator.has_permission(
            extension_name, permission_type, str(path)
        )

    def check_network_access(self, extension_name: str, domain: str) -> bool:
        """Check if extension can access a network domain.

        Args:
            extension_name: Name of extension
            domain: Domain to check

        Returns:
            True if access is allowed, False otherwise
        """
        sandbox_level = self.sandbox_levels.get(extension_name)

        if sandbox_level == SandboxLevel.NONE:
            return True  # Full access

        # Check permissions
        return self.permission_validator.has_permission(
            extension_name, "network_read", domain
        )

    def get_resource_limits(self, extension_name: str) -> dict[str, int]:
        """Get resource limits for an extension.

        Args:
            extension_name: Name of extension

        Returns:
            Dictionary of resource limits
        """
        return self.resource_limits.get(extension_name, {})

    def get_sandbox_level(self, extension_name: str) -> Optional[SandboxLevel]:
        """Get sandbox level for an extension.

        Args:
            extension_name: Name of extension

        Returns:
            Sandbox level or None
        """
        return self.sandbox_levels.get(extension_name)

    def enforce_limits(self, extension_name: str, metrics: dict[str, float]) -> list[str]:
        """Enforce resource limits for an extension.

        Checks current metrics against limits.

        Args:
            extension_name: Name of extension
            metrics: Current resource metrics (memory_mb, cpu_percent, open_files)

        Returns:
            List of violations (empty if no violations)
        """
        violations = []
        limits = self.get_resource_limits(extension_name)

        if not limits:
            return violations

        memory_limit = limits.get("max_memory_mb", 0)
        if memory_limit > 0 and metrics.get("memory_mb", 0) > memory_limit:
            violations.append(f"Memory limit exceeded: {metrics['memory_mb']:.1f}MB > {memory_limit}MB")

        cpu_limit = limits.get("max_cpu_percent", 0)
        if cpu_limit > 0 and metrics.get("cpu_percent", 0) > cpu_limit:
            violations.append(f"CPU limit exceeded: {metrics['cpu_percent']:.1f}% > {cpu_limit}%")

        files_limit = limits.get("max_open_files", 0)
        if files_limit > 0 and metrics.get("open_files", 0) > files_limit:
            violations.append(f"Open files limit exceeded: {metrics['open_files']} > {files_limit}")

        if violations:
            logger.warning(f"Resource violations in {extension_name}: {violations}")

        return violations
