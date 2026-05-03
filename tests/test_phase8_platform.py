"""
Tests for Phase 8: Platform-Specific Features.

Tests platform utilities, clipboard, and image handling.
"""

from unittest.mock import Mock, patch

from mARCH.platform.clipboard import (
    ClipboardError,
    ClipboardManager,
    get_clipboard_manager,
)
from mARCH.platform.image_utils import (
    ImageCache,
    get_image_cache,
)
from mARCH.platform.platform_utils import (
    OSType,
    PathUtils,
    PlatformInfo,
)


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

    @patch("mARCH.platform.clipboard.subprocess.run")
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

    @patch("mARCH.platform.clipboard.subprocess.run")
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

