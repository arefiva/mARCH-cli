"""Tests for extension manager."""

from pathlib import Path

import pytest

from mARCH.extension.manager import ExtensionManager
from mARCH.extension.registry import ExtensionRegistry


@pytest.mark.asyncio
class TestExtensionManager:
    """Test extension manager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create extension manager."""
        return ExtensionManager(search_paths=[tmp_path])

    @pytest.fixture
    def empty_manager(self):
        """Create manager with no search paths."""
        return ExtensionManager(search_paths=[])

    async def test_manager_creation(self, empty_manager):
        """Test creating manager."""
        assert empty_manager.registry is not None
        assert empty_manager.lifecycle_manager is not None
        assert empty_manager.sandbox_manager is not None

    async def test_initialize(self, manager):
        """Test initializing manager."""
        await manager.initialize()
        # Should not raise

    async def test_list_available_extensions(self, manager):
        """Test listing available extensions."""
        extensions = manager.list_available_extensions()
        assert isinstance(extensions, list)

    async def test_list_loaded_extensions(self, manager):
        """Test listing loaded extensions."""
        extensions = manager.list_loaded_extensions()
        assert isinstance(extensions, list)
        assert len(extensions) == 0

    async def test_get_available_services(self, manager):
        """Test getting available services."""
        services = manager.get_available_services()
        assert isinstance(services, list)

    async def test_shutdown(self, manager):
        """Test shutdown."""
        await manager.shutdown()
        # Should complete without error

    async def test_load_nonexistent_extension(self, manager):
        """Test loading nonexistent extension."""
        success = await manager.load_extension("nonexistent")
        assert not success

    async def test_unload_nonexistent_extension(self, manager):
        """Test unloading nonexistent extension."""
        success = await manager.unload_extension("nonexistent")
        assert not success

    async def test_get_extension_status_nonexistent(self, manager):
        """Test getting status of nonexistent extension."""
        status = manager.get_extension_status("nonexistent")
        assert status is None
