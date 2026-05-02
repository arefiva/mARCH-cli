"""Tests for extension registry and discovery."""

from pathlib import Path

import pytest
import yaml

from mARCH.extension.contracts import ExtensionManifest
from mARCH.extension.registry import ExtensionRegistry
from mARCH.extension.types import ExtensionType


class TestExtensionRegistry:
    """Test extension registry and discovery."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create a registry with test extension directory."""
        return ExtensionRegistry(search_paths=[tmp_path])

    @pytest.fixture
    def extension_dir(self, tmp_path):
        """Create a test extension directory."""
        ext_dir = tmp_path / "test-ext"
        ext_dir.mkdir()
        return ext_dir

    def create_manifest(self, ext_dir, name, version="1.0.0", dependencies=None):
        """Helper to create a manifest file."""
        manifest_path = ext_dir / "manifest.yaml"
        manifest_data = {
            "name": name,
            "version": version,
            "display_name": name,
            "description": f"Test extension {name}",
            "type": "tool",
            "entry_point": "main.py",
        }
        if dependencies:
            manifest_data["dependencies"] = dependencies

        manifest_path.write_text(yaml.dump(manifest_data))
        return manifest_path

    def test_registry_creation(self, tmp_path):
        """Test creating registry."""
        registry = ExtensionRegistry(search_paths=[tmp_path])
        assert tmp_path in registry.search_paths

    def test_discovery_no_extensions(self, registry, tmp_path):
        """Test discovery with no extensions."""
        manifests = registry.discover()
        assert len(manifests) == 0

    def test_discovery_single_extension(self, registry, extension_dir):
        """Test discovery of single extension."""
        self.create_manifest(extension_dir, "test-ext")

        manifests = registry.discover()
        assert len(manifests) == 1
        assert "test-ext" in manifests
        assert manifests["test-ext"].version == "1.0.0"

    def test_discovery_multiple_extensions(self, registry, tmp_path):
        """Test discovery of multiple extensions."""
        # Create multiple extension directories
        for i in range(3):
            ext_dir = tmp_path / f"ext-{i}"
            ext_dir.mkdir()
            self.create_manifest(ext_dir, f"ext-{i}")

        manifests = registry.discover()
        assert len(manifests) == 3

    def test_discovery_caching(self, registry, extension_dir):
        """Test that discover caches results."""
        self.create_manifest(extension_dir, "cached")

        first = registry.discover()
        assert len(first) == 1

        # Discover again should return cached result
        second = registry.discover()
        assert len(second) == 1
        assert first == second

    def test_discovery_force_rediscover(self, registry, extension_dir, tmp_path):
        """Test force rediscovery."""
        self.create_manifest(extension_dir, "test-1")
        registry.discover()

        # Add another extension
        ext_dir2 = tmp_path / "test-2"
        ext_dir2.mkdir()
        self.create_manifest(ext_dir2, "test-2")

        # Force rediscover should find new extension
        manifests = registry.discover(force=True)
        assert len(manifests) == 2

    def test_get_manifest(self, registry, extension_dir):
        """Test getting manifest by name."""
        self.create_manifest(extension_dir, "found")

        manifest = registry.get_manifest("found")
        assert manifest is not None
        assert manifest.name == "found"

    def test_get_manifest_not_found(self, registry):
        """Test getting nonexistent manifest."""
        manifest = registry.get_manifest("nonexistent")
        assert manifest is None

    def test_get_all_manifests(self, registry, tmp_path):
        """Test getting all manifests."""
        for i in range(3):
            ext_dir = tmp_path / f"ext-{i}"
            ext_dir.mkdir()
            self.create_manifest(ext_dir, f"ext-{i}")

        manifests = registry.get_all_manifests()
        assert len(manifests) == 3

    def test_validate_extension_no_dependencies(self, registry, extension_dir):
        """Test validation with no dependencies."""
        self.create_manifest(extension_dir, "independent")
        registry.discover()

        errors = registry.validate_extension("independent")
        assert errors == []

    def test_validate_extension_missing_dependency(self, registry, extension_dir):
        """Test validation with missing dependency."""
        self.create_manifest(extension_dir, "dependent", dependencies=["missing"])
        registry.discover()

        errors = registry.validate_extension("dependent")
        assert "missing" in errors[0]

    def test_validate_extension_not_found(self, registry):
        """Test validation of nonexistent extension."""
        errors = registry.validate_extension("nonexistent")
        assert len(errors) > 0

    def test_validate_all_extensions(self, registry, tmp_path):
        """Test validation of all extensions."""
        # Create valid extensions
        ext1 = tmp_path / "ext-1"
        ext1.mkdir()
        self.create_manifest(ext1, "ext-1")

        # Create extension with missing dependency
        ext2 = tmp_path / "ext-2"
        ext2.mkdir()
        self.create_manifest(ext2, "ext-2", dependencies=["missing"])

        registry.discover()
        errors = registry.validate_all()

        assert "ext-1" not in errors  # No errors for valid extension
        assert "ext-2" in errors  # Has errors for missing dependency

    def test_resolve_dependencies_no_deps(self, registry, extension_dir):
        """Test dependency resolution with no dependencies."""
        self.create_manifest(extension_dir, "independent")
        registry.discover()

        order = registry.resolve_dependencies("independent")
        assert order == ["independent"]

    def test_resolve_dependencies_linear(self, registry, tmp_path):
        """Test dependency resolution with linear chain."""
        # Create chain: a -> b -> c
        for name, dep in [("a", ["b"]), ("b", ["c"]), ("c", None)]:
            ext_dir = tmp_path / name
            ext_dir.mkdir()
            self.create_manifest(ext_dir, name, dependencies=dep or [])

        registry.discover()

        # Resolve dependencies for a
        order = registry.resolve_dependencies("a")
        # Should be in order: c, b, a
        assert order.index("c") < order.index("b")
        assert order.index("b") < order.index("a")

    def test_resolve_dependencies_not_found(self, registry):
        """Test resolving nonexistent extension."""
        registry.discover()

        with pytest.raises(ValueError, match="not found"):
            registry.resolve_dependencies("nonexistent")

    def test_get_manifest_path(self, registry, extension_dir):
        """Test getting manifest file path."""
        self.create_manifest(extension_dir, "located")
        registry.discover()

        path = registry.get_manifest_path("located")
        assert path is not None
        assert path.exists()
        assert path.name == "manifest.yaml"

    def test_get_extension_dir(self, registry, extension_dir):
        """Test getting extension directory."""
        self.create_manifest(extension_dir, "located")
        registry.discover()

        ext_dir = registry.get_extension_dir("located")
        assert ext_dir == extension_dir

    def test_add_search_path(self, registry, tmp_path):
        """Test adding search path."""
        new_path = tmp_path / "new"
        new_path.mkdir()

        # Create extension in new path
        ext_dir = new_path / "new-ext"
        ext_dir.mkdir()
        self.create_manifest(ext_dir, "new-ext")

        # Add path and discover
        registry.add_search_path(new_path)

        manifests = registry.get_all_manifests()
        assert "new-ext" in manifests

    def test_remove_search_path(self, registry, tmp_path):
        """Test removing search path."""
        # First, discover with the path
        ext_dir = tmp_path / "test-ext"
        ext_dir.mkdir()
        self.create_manifest(ext_dir, "test-ext")

        registry.discover()
        assert "test-ext" in registry.get_all_manifests()

        # Remove the path
        registry.remove_search_path(tmp_path)

        # Rediscover should be empty
        manifests = registry.get_all_manifests()
        assert len(manifests) == 0
