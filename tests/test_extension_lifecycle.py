"""Tests for extension lifecycle management."""

import asyncio
from pathlib import Path

import pytest

from mARCH.extension.lifecycle import (
    ExtensionLifecycleManager,
    ExtensionLifecycleState,
    ExtensionContext,
)
from mARCH.extension.contracts import ExtensionStatus


class TestExtensionContext:
    """Test extension context."""

    def test_context_creation(self, tmp_path):
        """Test creating context."""
        ctx = ExtensionContext("test", "1.0.0", tmp_path)

        assert ctx.name == "test"
        assert ctx.version == "1.0.0"
        assert ctx.directory == tmp_path
        assert ctx.state == ExtensionLifecycleState.NOT_LOADED

    def test_context_state_change(self, tmp_path):
        """Test changing state."""
        ctx = ExtensionContext("test", "1.0.0", tmp_path)

        ctx.state = ExtensionLifecycleState.LOADING
        assert ctx.state == ExtensionLifecycleState.LOADING

        ctx.state = ExtensionLifecycleState.LOADED
        assert ctx.state == ExtensionLifecycleState.LOADED


class TestExtensionLifecycleManager:
    """Test lifecycle manager."""

    @pytest.fixture
    def manager(self):
        """Create a lifecycle manager."""
        return ExtensionLifecycleManager()

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory."""
        return tmp_path

    @pytest.mark.asyncio
    async def test_manager_creation(self, manager):
        """Test creating manager."""
        assert len(manager.loaded_extensions) == 0
        assert len(manager.hooks) == 0

    @pytest.mark.asyncio
    async def test_load_extension(self, manager, temp_dir):
        """Test loading extension."""
        success = await manager.load_extension("test-ext", "1.0.0", temp_dir)

        assert success
        assert "test-ext" in manager.loaded_extensions
        context = manager.get_extension_context("test-ext")
        assert context.state == ExtensionLifecycleState.LOADED

    @pytest.mark.asyncio
    async def test_load_extension_already_loaded(self, manager, temp_dir):
        """Test loading already loaded extension."""
        await manager.load_extension("test-ext", "1.0.0", temp_dir)

        success = await manager.load_extension("test-ext", "1.0.0", temp_dir)
        assert not success

    @pytest.mark.asyncio
    async def test_unload_extension(self, manager, temp_dir):
        """Test unloading extension."""
        await manager.load_extension("test-ext", "1.0.0", temp_dir)

        success = await manager.unload_extension("test-ext")
        assert success
        assert "test-ext" not in manager.loaded_extensions

    @pytest.mark.asyncio
    async def test_unload_nonexistent(self, manager):
        """Test unloading nonexistent extension."""
        success = await manager.unload_extension("nonexistent")
        assert not success

    @pytest.mark.asyncio
    async def test_activate_extension(self, manager, temp_dir):
        """Test activating extension."""
        await manager.load_extension("test-ext", "1.0.0", temp_dir)

        success = await manager.activate_extension("test-ext")
        assert success

        context = manager.get_extension_context("test-ext")
        assert context.state == ExtensionLifecycleState.ACTIVE

    @pytest.mark.asyncio
    async def test_deactivate_extension(self, manager, temp_dir):
        """Test deactivating extension."""
        await manager.load_extension("test-ext", "1.0.0", temp_dir)
        await manager.activate_extension("test-ext")

        success = await manager.deactivate_extension("test-ext")
        assert success

        context = manager.get_extension_context("test-ext")
        assert context.state == ExtensionLifecycleState.LOADED

    @pytest.mark.asyncio
    async def test_register_hook(self, manager):
        """Test registering hook."""
        called = []

        def on_load(name, ctx):
            called.append(name)

        manager.register_hook("on_load", on_load)
        assert "on_load" in manager.hooks

    @pytest.mark.asyncio
    async def test_register_state_callback(self, manager):
        """Test registering state callback."""
        called = []

        def on_state_change(state):
            called.append(state)

        manager.register_state_callback("test-ext", on_state_change)
        assert "test-ext" in manager.state_callbacks

    @pytest.mark.asyncio
    async def test_list_loaded(self, manager, temp_dir):
        """Test listing loaded extensions."""
        await manager.load_extension("ext1", "1.0.0", temp_dir)
        await manager.load_extension("ext2", "1.0.0", temp_dir)

        loaded = manager.list_loaded()
        assert "ext1" in loaded
        assert "ext2" in loaded

    @pytest.mark.asyncio
    async def test_get_status(self, manager, temp_dir):
        """Test getting extension status."""
        await manager.load_extension("test-ext", "1.0.0", temp_dir)

        status = manager.get_status("test-ext")
        assert status is not None
        assert status.name == "test-ext"
        assert status.version == "1.0.0"
        assert status.status == ExtensionLifecycleState.LOADED.value

    @pytest.mark.asyncio
    async def test_get_status_nonexistent(self, manager):
        """Test getting status of nonexistent extension."""
        status = manager.get_status("nonexistent")
        assert status is None

    @pytest.mark.asyncio
    async def test_load_time_recorded(self, manager, temp_dir):
        """Test that load time is recorded."""
        await manager.load_extension("test-ext", "1.0.0", temp_dir)

        context = manager.get_extension_context("test-ext")
        assert context.load_time_ms is not None
        assert context.load_time_ms >= 0
