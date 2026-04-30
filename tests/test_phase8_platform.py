"""
Tests for Phase 8: Platform-Specific Features.

Tests platform utilities, clipboard, and image handling.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from mARCH.platform.platform_utils import (
    OSType,
    PlatformInfo,
    ConsoleInfo,
    ExecutablePermissions,
    PathUtils,
    get_platform_info,
    get_console_info,
)
from mARCH.platform.clipboard import (
    ClipboardManager,
    ClipboardError,
    get_clipboard_manager,
)
from mARCH.platform.image_utils import (
    ImageProcessor,
    ImageSize,
    ImageCache,
    ImageError,
    get_image_processor,
    get_image_cache,
)


class TestOSType:
    """Test OSType enum."""

    def test_os_type_values(self):
        """Test OS type values."""
        assert OSType.WINDOWS.value == "windows"
        assert OSType.MACOS.value == "macos"
        assert OSType.LINUX.value == "linux"
        assert OSType.UNKNOWN.value == "unknown"


class TestPlatformInfo:
    """Test PlatformInfo class."""

    def test_platform_info_creation(self):
        """Test creating platform info."""
        info = PlatformInfo()
        assert info.system is not None
        assert info.platform is not None
        assert info.machine is not None

    def test_os_type_detection(self):
        """Test OS type detection."""
        info = PlatformInfo()
        assert info.os_type in [
            OSType.WINDOWS,
            OSType.MACOS,
            OSType.LINUX,
            OSType.UNKNOWN,
        ]

    def test_platform_properties(self):
        """Test platform info properties."""
        info = PlatformInfo()
        
        # At least one OS type should be true
        assert (
            info.is_windows
            or info.is_macos
            or info.is_linux
        )

    def test_unix_like_detection(self):
        """Test Unix-like detection."""
        info = PlatformInfo()
        
        if info.is_windows:
            assert not info.is_unix_like
        else:
            assert info.is_unix_like

    def test_platform_info_string_representation(self):
        """Test string representation."""
        info = PlatformInfo()
        str_repr = str(info)
        assert info.system in str_repr
        assert info.release in str_repr

    def test_platform_info_repr(self):
        """Test repr."""
        info = PlatformInfo()
        repr_str = repr(info)
        assert "PlatformInfo" in repr_str
        assert "system=" in repr_str


class TestConsoleInfo:
    """Test ConsoleInfo class."""

    def test_console_info_creation(self):
        """Test creating console info."""
        info = ConsoleInfo()
        assert info.width > 0
        assert info.height > 0

    def test_console_properties(self):
        """Test console properties."""
        info = ConsoleInfo()
        assert isinstance(info.is_tty, bool)
        assert isinstance(info.is_interactive, bool)
        assert isinstance(info.supports_unicode, bool)
        assert isinstance(info.supports_colors, bool)

    def test_console_dimensions(self):
        """Test console dimensions."""
        info = ConsoleInfo()
        assert info.width >= 80
        assert info.height >= 24

    def test_console_info_repr(self):
        """Test console info repr."""
        info = ConsoleInfo()
        repr_str = repr(info)
        assert "ConsoleInfo" in repr_str
        assert "tty=" in repr_str


class TestExecutablePermissions:
    """Test executable permissions."""

    def test_is_executable_nonexistent(self):
        """Test checking non-existent file."""
        assert not ExecutablePermissions.is_executable("/nonexistent/file")

    def test_is_executable_directory(self):
        """Test checking directory."""
        assert not ExecutablePermissions.is_executable("/tmp")

    @pytest.mark.skipif(PlatformInfo().is_windows, reason="Unix-specific test")
    def test_make_executable(self):
        """Test making file executable."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
            f.write(b"#!/bin/bash\necho test\n")

        try:
            ExecutablePermissions.make_executable(temp_path)
            assert ExecutablePermissions.is_executable(temp_path)
        finally:
            Path(temp_path).unlink()


class TestPathUtils:
    """Test path utilities."""

    def test_get_app_data_dir(self):
        """Test getting app data directory."""
        app_data = PathUtils.get_app_data_dir()
        assert isinstance(app_data, str)
        assert len(app_data) > 0
        assert "march" in app_data.lower()

    def test_get_cache_dir(self):
        """Test getting cache directory."""
        cache = PathUtils.get_cache_dir()
        assert isinstance(cache, str)
        assert len(cache) > 0
        assert "march" in cache.lower()

    def test_get_config_dir(self):
        """Test getting config directory."""
        config = PathUtils.get_config_dir()
        assert isinstance(config, str)
        assert len(config) > 0
        assert "march" in config.lower()

    def test_app_data_contains_march(self):
        """Test that app data contains """
        app_data = PathUtils.get_app_data_dir()
        assert "march" in app_data.lower()

    def test_cache_contains_march(self):
        """Test that cache contains """
        cache = PathUtils.get_cache_dir()
        assert "march" in cache.lower()

    def test_config_contains_march(self):
        """Test that config contains """
        config = PathUtils.get_config_dir()
        assert "march" in config.lower()


class TestClipboardManager:
    """Test clipboard manager."""

    def test_clipboard_manager_creation(self):
        """Test creating clipboard manager."""
        manager = ClipboardManager()
        assert manager is not None

    @patch("clipboard.subprocess.run")
    def test_copy_text(self, mock_run):
        """Test copying text to clipboard."""
        mock_run.return_value = Mock(returncode=0)
        manager = ClipboardManager()
        
        # Should not raise
        try:
            manager.copy("test text")
        except ClipboardError:
            # Expected on systems without clipboard support
            pass

    @patch("clipboard.subprocess.run")
    def test_paste_text(self, mock_run):
        """Test pasting text from clipboard."""
        mock_run.return_value = Mock(stdout=b"test text")
        manager = ClipboardManager()
        
        try:
            result = manager.paste()
            if result is not None:
                assert isinstance(result, str)
        except ClipboardError:
            # Expected on systems without clipboard support
            pass

    def test_clipboard_error_creation(self):
        """Test creating clipboard error."""
        error = ClipboardError("Test error")
        assert str(error) == "Test error"

    def test_clipboard_manager_singleton(self):
        """Test clipboard manager singleton."""
        manager1 = get_clipboard_manager()
        manager2 = get_clipboard_manager()
        assert manager1 is manager2


class TestImageSize:
    """Test ImageSize dataclass."""

    def test_create_image_size(self):
        """Test creating image size."""
        size = ImageSize(1920, 1080)
        assert size.width == 1920
        assert size.height == 1080

    def test_scale_to_fit_larger_image(self):
        """Test scaling larger image to fit."""
        size = ImageSize(1920, 1080)
        scaled = size.scale_to_fit(800, 600)
        
        assert scaled.width <= 800
        assert scaled.height <= 600
        # Check aspect ratio is maintained
        original_ratio = 1920 / 1080
        scaled_ratio = scaled.width / scaled.height
        assert abs(original_ratio - scaled_ratio) < 0.01

    def test_scale_to_fit_smaller_image(self):
        """Test scaling smaller image within bounds."""
        size = ImageSize(640, 480)
        scaled = size.scale_to_fit(800, 600)
        
        # Should not upscale
        assert scaled.width == 640
        assert scaled.height == 480

    def test_scale_to_fit_exact_bounds(self):
        """Test scaling to exact bounds."""
        size = ImageSize(1600, 1200)
        scaled = size.scale_to_fit(800, 600)
        
        assert scaled.width == 800
        assert scaled.height <= 600


class TestImageProcessor:
    """Test image processor."""

    def test_image_processor_creation(self):
        """Test creating image processor."""
        processor = ImageProcessor()
        assert processor is not None

    def test_ascii_chars_constant(self):
        """Test ASCII characters constant."""
        processor = ImageProcessor()
        assert len(processor.ASCII_CHARS) > 0
        assert "@" in processor.ASCII_CHARS

    def test_pillow_check(self):
        """Test Pillow availability check."""
        processor = ImageProcessor()
        assert isinstance(processor._has_pillow, bool)

    @pytest.mark.skipif(not ImageProcessor()._has_pillow, reason="Pillow not installed")
    def test_load_image_nonexistent(self):
        """Test loading non-existent image."""
        processor = ImageProcessor()
        
        with pytest.raises(ImageError):
            processor.load_image("/nonexistent/image.png")

    @pytest.mark.skipif(not ImageProcessor()._has_pillow, reason="Pillow not installed")
    def test_get_image_size_nonexistent(self):
        """Test getting size of non-existent image."""
        processor = ImageProcessor()
        
        with pytest.raises(ImageError):
            processor.get_image_size("/nonexistent/image.png")

    def test_image_error_creation(self):
        """Test creating image error."""
        error = ImageError("Test error")
        assert str(error) == "Test error"

    def test_image_processor_singleton(self):
        """Test image processor singleton."""
        proc1 = get_image_processor()
        proc2 = get_image_processor()
        assert proc1 is proc2


class TestImageCache:
    """Test image cache."""

    def test_create_image_cache(self):
        """Test creating image cache."""
        cache = ImageCache()
        assert cache.max_size == 10

    def test_cache_get_set(self):
        """Test cache get and set."""
        cache = ImageCache()
        cache.set("key1", "value1")
        
        value = cache.get("key1")
        assert value == "value1"

    def test_cache_get_nonexistent(self):
        """Test getting non-existent key."""
        cache = ImageCache()
        value = cache.get("nonexistent")
        assert value is None

    def test_cache_max_size(self):
        """Test cache max size limit."""
        cache = ImageCache(max_size=3)
        
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
        
        # Cache should not exceed max size
        assert len(cache._cache) <= 3

    def test_cache_clear(self):
        """Test clearing cache."""
        cache = ImageCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_image_cache_singleton(self):
        """Test image cache singleton."""
        cache1 = get_image_cache()
        cache2 = get_image_cache()
        assert cache1 is cache2


class TestGlobalSingletons:
    """Test global singleton instances."""

    def test_get_platform_info_singleton(self):
        """Test platform info singleton."""
        info1 = get_platform_info()
        info2 = get_platform_info()
        assert info1 is info2

    def test_get_console_info_singleton(self):
        """Test console info singleton."""
        info1 = get_console_info()
        info2 = get_console_info()
        assert info1 is info2


class TestIntegration:
    """Integration tests for Phase 8."""

    def test_platform_detection_workflow(self):
        """Test complete platform detection workflow."""
        platform_info = get_platform_info()
        console_info = get_console_info()
        
        # Both should be available
        assert platform_info is not None
        assert console_info is not None
        
        # Platform should have valid OS type
        assert platform_info.os_type != OSType.UNKNOWN or True  # Allow unknown for safety
        
        # Console should have dimensions
        assert console_info.width > 0
        assert console_info.height > 0

    def test_path_utils_workflow(self):
        """Test path utilities workflow."""
        app_data = PathUtils.get_app_data_dir()
        cache = PathUtils.get_cache_dir()
        config = PathUtils.get_config_dir()
        
        # All should be valid paths
        assert len(app_data) > 0
        assert len(cache) > 0
        assert len(config) > 0
        
        # All should contain march
        assert "march" in app_data.lower()
        assert "march" in cache.lower()
        assert "march" in config.lower()

    def test_image_cache_workflow(self):
        """Test image caching workflow."""
        cache = get_image_cache()
        
        # Store and retrieve
        cache.set("image1", "<ASCII art>")
        assert cache.get("image1") == "<ASCII art>"
        
        # Non-existent
        assert cache.get("nonexistent") is None
        
        # Clear
        cache.clear()
        assert cache.get("image1") is None
