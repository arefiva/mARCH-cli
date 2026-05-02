"""Extension registry and discovery system."""

import logging
from pathlib import Path
from typing import Optional

from .contracts import ExtensionManifest
from .manifest import ManifestParseError, ManifestValidator
from .types import ExtensionStatus

logger = logging.getLogger(__name__)


class ExtensionRegistry:
    """Manages extension discovery and registry."""

    DEFAULT_SEARCH_PATHS = [
        Path.home() / ".copilot" / "extensions",
        Path.cwd() / ".github" / "extensions",
    ]

    def __init__(self, search_paths: Optional[list[Path]] = None):
        """Initialize the extension registry.

        Args:
            search_paths: Paths to search for extensions. If None, uses DEFAULT_SEARCH_PATHS.
        """
        self.search_paths = search_paths or self.DEFAULT_SEARCH_PATHS
        self.manifests: dict[str, ExtensionManifest] = {}
        self.manifest_paths: dict[str, Path] = {}
        self.status: dict[str, ExtensionStatus] = {}
        self._discovered = False

    def discover(self, force: bool = False) -> dict[str, ExtensionManifest]:
        """Discover extensions in search paths.

        Scans all search paths for extension manifests and builds registry.

        Args:
            force: If True, rediscover even if already discovered

        Returns:
            Dictionary mapping extension name to manifest
        """
        if self._discovered and not force:
            return self.manifests

        self.manifests.clear()
        self.manifest_paths.clear()

        for search_path in self.search_paths:
            if not search_path.exists():
                logger.debug(f"Extension search path does not exist: {search_path}")
                continue

            logger.debug(f"Scanning for extensions in: {search_path}")
            self._scan_directory(search_path)

        logger.info(f"Discovered {len(self.manifests)} extensions")
        self._discovered = True
        return self.manifests

    def _scan_directory(self, base_path: Path) -> None:
        """Scan a directory for extension manifests.

        Looks for manifest.yaml/json files in subdirectories.

        Args:
            base_path: Base directory to scan
        """
        if not base_path.is_dir():
            return

        for item in base_path.iterdir():
            if not item.is_dir():
                continue

            # Look for manifest files in each subdirectory
            for manifest_name in ["manifest.yaml", "manifest.yml", "manifest.json"]:
                manifest_path = item / manifest_name
                if manifest_path.exists():
                    self._register_manifest(manifest_path)
                    break

    def _register_manifest(self, manifest_path: Path) -> None:
        """Register a single manifest file.

        Args:
            manifest_path: Path to manifest file
        """
        try:
            manifest = ManifestValidator.load_manifest(manifest_path)
            self.manifests[manifest.name] = manifest
            self.manifest_paths[manifest.name] = manifest_path
            logger.debug(f"Registered extension: {manifest.name} ({manifest.version})")
        except ManifestParseError as e:
            logger.warning(f"Failed to parse manifest {manifest_path}: {e}")

    def get_manifest(self, name: str) -> Optional[ExtensionManifest]:
        """Get extension manifest by name.

        Args:
            name: Extension name

        Returns:
            Extension manifest or None if not found
        """
        if not self._discovered:
            self.discover()
        return self.manifests.get(name)

    def get_all_manifests(self) -> dict[str, ExtensionManifest]:
        """Get all discovered manifests.

        Returns:
            Dictionary mapping extension name to manifest
        """
        if not self._discovered:
            self.discover()
        return dict(self.manifests)

    def validate_extension(self, name: str) -> list[str]:
        """Validate that an extension's dependencies are available.

        Args:
            name: Extension name

        Returns:
            List of missing dependencies (empty if valid)
        """
        manifest = self.get_manifest(name)
        if not manifest:
            return [f"Extension not found: {name}"]

        missing = ManifestValidator.validate_dependencies(
            manifest, list(self.manifests.keys())
        )
        return missing

    def validate_all(self) -> dict[str, list[str]]:
        """Validate all extensions.

        Returns:
            Dictionary mapping extension name to list of validation errors
        """
        if not self._discovered:
            self.discover()

        errors = {}

        # Check for circular dependencies
        cycles = ManifestValidator.check_circular_dependencies(self.manifests)
        if cycles:
            logger.warning(f"Found circular dependencies: {cycles}")

        # Validate each extension
        for name in self.manifests:
            missing = self.validate_extension(name)
            if missing:
                errors[name] = missing

        return errors

    def get_manifest_path(self, name: str) -> Optional[Path]:
        """Get path to extension manifest file.

        Args:
            name: Extension name

        Returns:
            Path to manifest file or None if not found
        """
        return self.manifest_paths.get(name)

    def get_extension_dir(self, name: str) -> Optional[Path]:
        """Get the directory containing an extension.

        Args:
            name: Extension name

        Returns:
            Directory path or None if not found
        """
        manifest_path = self.get_manifest_path(name)
        if manifest_path:
            return manifest_path.parent
        return None

    def resolve_dependencies(self, name: str) -> list[str]:
        """Resolve dependencies in load order.

        Returns list of extension names in order they should be loaded
        (dependencies before dependents).

        Args:
            name: Extension name

        Returns:
            List of extension names in load order

        Raises:
            ValueError: If extension not found or has unresolved dependencies
        """
        if name not in self.manifests:
            raise ValueError(f"Extension not found: {name}")

        visited = set()
        result = []

        def visit(ext_name: str) -> None:
            if ext_name in visited:
                return
            visited.add(ext_name)

            manifest = self.manifests.get(ext_name)
            if not manifest:
                raise ValueError(f"Extension not found: {ext_name}")

            for dep in manifest.dependencies:
                if dep not in self.manifests:
                    raise ValueError(f"Dependency not found: {dep}")
                visit(dep)

            result.append(ext_name)

        visit(name)
        return result

    def add_search_path(self, path: Path) -> None:
        """Add a search path for extensions.

        Args:
            path: Path to add
        """
        if path not in self.search_paths:
            self.search_paths.append(path)
            # Rediscover when new path is added
            self.discover(force=True)

    def remove_search_path(self, path: Path) -> None:
        """Remove a search path for extensions.

        Args:
            path: Path to remove
        """
        if path in self.search_paths:
            self.search_paths.remove(path)
            # Rediscover when path is removed
            self.discover(force=True)

    def set_status(self, name: str, status: ExtensionStatus) -> None:
        """Set extension status.

        Args:
            name: Extension name
            status: Status object
        """
        self.status[name] = status

    def get_status(self, name: str) -> Optional[ExtensionStatus]:
        """Get extension status.

        Args:
            name: Extension name

        Returns:
            Status object or None
        """
        return self.status.get(name)
