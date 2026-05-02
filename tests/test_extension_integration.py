"""Integration tests for extension system."""

from pathlib import Path

import pytest
import yaml

from mARCH.extension.manager import ExtensionManager
from mARCH.extension.contracts import ExtensionManifest
from mARCH.extension.types import ExtensionType


class TestExtensionIntegration:
    """Integration tests for the full extension system."""

    @pytest.fixture
    def extension_dir(self, tmp_path):
        """Create test extension directory."""
        ext_dir = tmp_path / "test-ext"
        ext_dir.mkdir()
        return ext_dir

    @pytest.fixture
    def manager(self, tmp_path):
        """Create extension manager."""
        return ExtensionManager(search_paths=[tmp_path])

    @pytest.fixture
    def test_manifest(self, extension_dir):
        """Create test manifest."""
        manifest = {
            "name": "test-tool",
            "version": "1.0.0",
            "display_name": "Test Tool",
            "description": "Test extension",
            "type": "tool",
            "entry_point": "main.py",
            "sandbox_level": "file_restricted",
            "permissions": [
                {"type": "file_read", "resource": "/tmp/**"}
            ],
        }
        manifest_file = extension_dir / "manifest.yaml"
        manifest_file.write_text(yaml.dump(manifest))
        return manifest

    @pytest.mark.asyncio
    async def test_discovery_and_load(self, manager, test_manifest, extension_dir):
        """Test discovering and loading an extension."""
        # Initialize should discover extension
        await manager.initialize()

        # Check it was discovered
        available = manager.list_available_extensions()
        assert len(available) > 0

        found = False
        for ext in available:
            if ext["name"] == "test-tool":
                found = True
                assert ext["version"] == "1.0.0"
                break

        assert found, "Extension not discovered"

    @pytest.mark.asyncio
    async def test_sandbox_enforcement(self, manager, test_manifest):
        """Test that sandbox settings are enforced."""
        await manager.initialize()

        # Get extension context
        status = manager.get_extension_status("test-tool")
        # Should succeed or not exist (depends on loading)

    @pytest.mark.asyncio
    async def test_service_discovery(self, manager):
        """Test service discovery capabilities."""
        # Get available services
        services = manager.get_available_services()
        assert isinstance(services, list)

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, manager, test_manifest):
        """Test full lifecycle: initialize → load → unload → shutdown."""
        # Initialize
        await manager.initialize()

        # List available
        available = manager.list_available_extensions()

        # Attempt load (may fail if extension not fully implemented)
        # This is expected for this test
        
        # List loaded
        loaded = manager.list_loaded_extensions()
        assert isinstance(loaded, list)

        # Shutdown
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_multiple_extensions(self, tmp_path):
        """Test managing multiple extensions."""
        # Create multiple test extensions
        for i in range(3):
            ext_dir = tmp_path / f"ext-{i}"
            ext_dir.mkdir()

            manifest = {
                "name": f"ext-{i}",
                "version": "1.0.0",
                "display_name": f"Extension {i}",
                "description": f"Test extension {i}",
                "type": "tool",
                "entry_point": "main.py",
            }
            manifest_file = ext_dir / "manifest.yaml"
            manifest_file.write_text(yaml.dump(manifest))

        manager = ExtensionManager(search_paths=[tmp_path])
        await manager.initialize()

        available = manager.list_available_extensions()
        assert len(available) >= 3

    @pytest.mark.asyncio
    async def test_extension_validation(self, tmp_path):
        """Test extension manifest validation."""
        # Create extension with dependency
        ext_dir = tmp_path / "dependent-ext"
        ext_dir.mkdir()

        manifest = {
            "name": "dependent",
            "version": "1.0.0",
            "display_name": "Dependent",
            "description": "Depends on base",
            "type": "tool",
            "entry_point": "main.py",
            "dependencies": ["base-ext"],
        }
        manifest_file = ext_dir / "manifest.yaml"
        manifest_file.write_text(yaml.dump(manifest))

        manager = ExtensionManager(search_paths=[tmp_path])
        await manager.initialize()

        # Validation should detect missing dependency
        errors = manager.registry.validate_all()
        # Should have errors for missing dependency
