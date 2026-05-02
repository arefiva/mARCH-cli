"""Main extension manager coordinating all extension systems."""

import logging
from pathlib import Path
from typing import Optional

from .cli_command import CliExtensionLoader
from .lifecycle import ExtensionLifecycleManager
from .registry import ExtensionRegistry
from .sandbox import SandboxManager
from .tool import ToolExtensionLoader
from .discovery import ServiceRegistry

logger = logging.getLogger(__name__)


class ExtensionManager:
    """Central manager for all extension systems."""

    def __init__(self, search_paths: Optional[list[Path]] = None):
        """Initialize extension manager.

        Args:
            search_paths: Paths to search for extensions
        """
        self.registry = ExtensionRegistry(search_paths)
        self.lifecycle_manager = ExtensionLifecycleManager()
        self.sandbox_manager = SandboxManager()
        self.service_registry = ServiceRegistry()
        self.cli_loader = CliExtensionLoader()
        self.tool_loader = ToolExtensionLoader()

    async def initialize(self) -> None:
        """Initialize the extension system.

        Discovers available extensions and validates them.
        """
        logger.info("Initializing extension system")

        # Discover extensions
        manifests = self.registry.discover()
        logger.info(f"Discovered {len(manifests)} extensions")

        # Validate all extensions
        errors = self.registry.validate_all()
        if errors:
            logger.warning(f"Extension validation errors: {errors}")

        # Set up sandboxing for discovered extensions
        for name, manifest in manifests.items():
            sandbox_errors = self.sandbox_manager.setup_extension(manifest)
            if sandbox_errors:
                logger.warning(
                    f"Sandbox setup errors for {name}: {sandbox_errors}"
                )

    async def load_extension(self, name: str, auto_activate: bool = True) -> bool:
        """Load an extension.

        Args:
            name: Extension name
            auto_activate: Automatically activate after loading

        Returns:
            True if successful, False otherwise
        """
        manifest = self.registry.get_manifest(name)
        if not manifest:
            logger.error(f"Extension not found: {name}")
            return False

        # Check dependencies
        missing_deps = self.registry.validate_extension(name)
        if missing_deps:
            logger.error(f"Extension {name} has missing dependencies: {missing_deps}")
            return False

        # Get extension directory
        ext_dir = self.registry.get_extension_dir(name)
        if not ext_dir:
            logger.error(f"Extension directory not found for {name}")
            return False

        # Load extension
        success = await self.lifecycle_manager.load_extension(
            name, manifest.version, ext_dir
        )

        if success and auto_activate:
            success = await self.lifecycle_manager.activate_extension(name)

        if success:
            logger.info(f"Successfully loaded extension: {name}")
        else:
            logger.error(f"Failed to load extension: {name}")

        return success

    async def unload_extension(self, name: str) -> bool:
        """Unload an extension.

        Args:
            name: Extension name

        Returns:
            True if successful, False otherwise
        """
        success = await self.lifecycle_manager.unload_extension(name)

        if success:
            # Clean up service registry
            await self.service_registry.clear_extension_data(name)
            logger.info(f"Successfully unloaded extension: {name}")
        else:
            logger.error(f"Failed to unload extension: {name}")

        return success

    async def load_auto_extensions(self) -> dict[str, bool]:
        """Load all extensions marked with auto_load=true.

        Returns:
            Dictionary mapping extension name to success status
        """
        results = {}
        manifests = self.registry.get_all_manifests()

        for name, manifest in manifests.items():
            # Skip if not marked for auto-load (default is true)
            # This would be checked from extension config file
            results[name] = await self.load_extension(name, auto_activate=True)

        return results

    def get_extension_status(self, name: str) -> Optional[dict]:
        """Get status of an extension.

        Args:
            name: Extension name

        Returns:
            Status dictionary or None
        """
        status = self.lifecycle_manager.get_status(name)
        if not status:
            return None

        return {
            "name": status.name,
            "version": status.version,
            "status": status.status,
            "error": status.last_error,
            "load_time_ms": status.load_time_ms,
        }

    def list_loaded_extensions(self) -> list[str]:
        """List all loaded extensions.

        Returns:
            List of extension names
        """
        return self.lifecycle_manager.list_loaded()

    def list_available_extensions(self) -> list[dict]:
        """List all available extensions.

        Returns:
            List of extension information dicts
        """
        manifests = self.registry.get_all_manifests()
        return [
            {
                "name": m.name,
                "version": m.version,
                "type": m.type.value,
                "description": m.description,
            }
            for m in manifests.values()
        ]

    def get_available_services(self) -> list[dict]:
        """Get all available services from loaded extensions.

        Returns:
            List of service information dicts
        """
        services = self.service_registry.list_all_services()
        return [
            {
                "extension": s["extension"],
                "name": s["name"],
                "methods": s["methods"],
            }
            for s in services
        ]

    async def shutdown(self) -> None:
        """Shutdown the extension system.

        Unloads all extensions and cleans up resources.
        """
        logger.info("Shutting down extension system")

        loaded = self.lifecycle_manager.list_loaded()
        for name in loaded:
            await self.unload_extension(name)

        logger.info("Extension system shutdown complete")
