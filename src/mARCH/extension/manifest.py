"""Extension manifest parsing and validation."""

import json
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import ValidationError

from .contracts import ExtensionManifest


class ManifestParseError(Exception):
    """Raised when manifest parsing fails."""

    pass


class ManifestValidator:
    """Validates and parses extension manifests."""

    SUPPORTED_FORMATS = [".yaml", ".yml", ".json"]

    @classmethod
    def load_manifest(cls, path: Path) -> ExtensionManifest:
        """Load and parse an extension manifest file.

        Args:
            path: Path to manifest file (.yaml, .yml, or .json)

        Returns:
            Parsed ExtensionManifest

        Raises:
            ManifestParseError: If file format is unsupported or content is invalid
        """
        if not path.exists():
            raise ManifestParseError(f"Manifest file not found: {path}")

        suffix = path.suffix.lower()
        if suffix not in cls.SUPPORTED_FORMATS:
            raise ManifestParseError(
                f"Unsupported manifest format: {suffix}. "
                f"Supported: {', '.join(cls.SUPPORTED_FORMATS)}"
            )

        try:
            content = cls._load_file(path, suffix)
            return ExtensionManifest(**content)
        except json.JSONDecodeError as e:
            raise ManifestParseError(f"Invalid JSON in manifest {path}: {e}") from e
        except yaml.YAMLError as e:
            raise ManifestParseError(f"Invalid YAML in manifest {path}: {e}") from e
        except ValidationError as e:
            raise ManifestParseError(f"Invalid manifest schema in {path}: {e}") from e

    @classmethod
    def _load_file(cls, path: Path, suffix: str) -> dict[str, Any]:
        """Load file content based on format."""
        content = path.read_text(encoding="utf-8")

        if suffix == ".json":
            return json.loads(content)
        else:  # .yaml or .yml
            return yaml.safe_load(content) or {}

    @classmethod
    def validate_manifest(cls, data: dict[str, Any]) -> ExtensionManifest:
        """Validate manifest data.

        Args:
            data: Dictionary of manifest data

        Returns:
            Validated ExtensionManifest

        Raises:
            ManifestParseError: If manifest data is invalid
        """
        try:
            return ExtensionManifest(**data)
        except ValidationError as e:
            raise ManifestParseError(f"Invalid manifest data: {e}") from e

    @classmethod
    def validate_dependencies(
        cls, manifest: ExtensionManifest, available_extensions: list[str]
    ) -> list[str]:
        """Validate that all declared dependencies are available.

        Args:
            manifest: Extension manifest
            available_extensions: List of available extension names

        Returns:
            List of missing dependencies (empty if all satisfied)
        """
        missing = []
        for dep in manifest.dependencies:
            if dep not in available_extensions:
                missing.append(dep)
        return missing

    @classmethod
    def check_circular_dependencies(
        cls, manifests: dict[str, ExtensionManifest]
    ) -> list[tuple[str, str]]:
        """Check for circular dependencies between extensions.

        Args:
            manifests: Dict mapping extension name to manifest

        Returns:
            List of (extension_a, extension_b) circular dependencies found
        """
        cycles = []

        def has_dependency_on(source: str, target: str, visited: set[str]) -> bool:
            """Check if source has a dependency path to target."""
            if source not in manifests:
                return False

            visited.add(source)
            manifest = manifests[source]

            for dep in manifest.dependencies:
                if dep == target:
                    return True
                if dep not in visited:
                    if has_dependency_on(dep, target, visited):
                        return True

            return False

        # Check each pair for cycles
        for ext_name, manifest in manifests.items():
            for dep in manifest.dependencies:
                if has_dependency_on(dep, ext_name, set()):
                    cycles.append((ext_name, dep))

        return cycles
