"""Extension permissions model and validation."""

import logging
from typing import Optional

from .contracts import ExtensionManifest, ExtensionPermission
from .types import PermissionType

logger = logging.getLogger(__name__)


class PermissionValidator:
    """Validates and manages extension permissions."""

    def __init__(self):
        """Initialize permission validator."""
        self.granted_permissions: dict[str, list[ExtensionPermission]] = {}
        self.denied_permissions: dict[str, list[ExtensionPermission]] = {}

    def grant_permission(
        self, extension_name: str, permission: ExtensionPermission
    ) -> None:
        """Grant a permission to an extension.

        Args:
            extension_name: Name of extension
            permission: Permission to grant
        """
        if extension_name not in self.granted_permissions:
            self.granted_permissions[extension_name] = []
        # Avoid duplicates
        if permission not in self.granted_permissions[extension_name]:
            self.granted_permissions[extension_name].append(permission)
        logger.info(f"Granted {permission.type} to {extension_name}")

    def revoke_permission(
        self, extension_name: str, permission: ExtensionPermission
    ) -> None:
        """Revoke a permission from an extension.

        Args:
            extension_name: Name of extension
            permission: Permission to revoke
        """
        if extension_name in self.granted_permissions:
            if permission in self.granted_permissions[extension_name]:
                self.granted_permissions[extension_name].remove(permission)
        logger.info(f"Revoked {permission.type} from {extension_name}")

    def deny_permission(
        self, extension_name: str, permission: ExtensionPermission
    ) -> None:
        """Deny a permission to an extension.

        Args:
            extension_name: Name of extension
            permission: Permission to deny
        """
        if extension_name not in self.denied_permissions:
            self.denied_permissions[extension_name] = []
        # Avoid duplicates
        if permission not in self.denied_permissions[extension_name]:
            self.denied_permissions[extension_name].append(permission)
        logger.info(f"Denied {permission.type} to {extension_name}")

    def has_permission(
        self,
        extension_name: str,
        permission_type: PermissionType,
        resource: Optional[str] = None,
    ) -> bool:
        """Check if extension has a permission.

        Args:
            extension_name: Name of extension
            permission_type: Type of permission to check
            resource: Specific resource to check (e.g., file path)

        Returns:
            True if permission is granted, False otherwise
        """
        # Check denials first
        if extension_name in self.denied_permissions:
            for denied in self.denied_permissions[extension_name]:
                if denied.type == permission_type:
                    if resource is None or self._resource_matches(
                        denied.resource, resource
                    ):
                        return False

        # Check grants
        if extension_name in self.granted_permissions:
            for granted in self.granted_permissions[extension_name]:
                if granted.type == permission_type:
                    if resource is None or self._resource_matches(granted.resource, resource):
                        return True

        return False

    def get_permissions(self, extension_name: str) -> list[ExtensionPermission]:
        """Get all granted permissions for an extension.

        Args:
            extension_name: Name of extension

        Returns:
            List of granted permissions
        """
        return list(self.granted_permissions.get(extension_name, set()))

    def validate_manifest_permissions(
        self, manifest: ExtensionManifest
    ) -> list[str]:
        """Validate that manifest permissions are well-formed.

        Args:
            manifest: Extension manifest

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        for permission in manifest.permissions:
            if not permission.type:
                errors.append(f"Permission missing type in {manifest.name}")

            if permission.type not in ["file_read", "file_write", "network_read", "environment_vars"]:
                errors.append(
                    f"Unknown permission type {permission.type} in {manifest.name}"
                )

        return errors

    @staticmethod
    def _resource_matches(pattern: Optional[str], resource: str) -> bool:
        """Check if resource matches pattern.

        Supports simple wildcards:
        - /home/* matches any file in /home/
        - /home/user/** matches any file recursively

        Args:
            pattern: Pattern to match (None matches anything)
            resource: Resource to test

        Returns:
            True if resource matches pattern
        """
        if pattern is None:
            return True

        # Simple glob matching
        if pattern == "*":
            return True

        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            return resource.startswith(prefix)

        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            # Ensure we're checking one level only
            if not resource.startswith(prefix + "/"):
                return False
            # Get the part after the prefix and slash
            remaining = resource[len(prefix) + 1 :]
            # Should not have "/" in remaining (i.e., single level only)
            return "/" not in remaining

        return pattern == resource
