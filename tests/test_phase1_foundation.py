"""
Basic tests for Phase 1 foundation modules.
"""

import pytest
from pathlib import Path

from mARCH.exceptions import ConfigurationError, mARCHError
from mARCH.config.config import ConfigManager, ConfigFile
from mARCH.logging_config import setup_logging, get_logger


class TestExceptions:
    """Test exception hierarchy."""

    def test_march_error_basic(self):
        """Test basic mARCHError creation."""
        err = mARCHError("Test error")
        assert str(err) == "Test error"

    def test_march_error_with_details(self):
        """Test mARCHError with details."""
        err = mARCHError("Test error", details="More info")
        assert "Test error" in str(err)
        assert "More info" in str(err)

    def test_configuration_error_inheritance(self):
        """Test ConfigurationError is a mARCHError."""
        err = ConfigurationError("Config failed")
        assert isinstance(err, mARCHError)


class TestConfig:
    """Test configuration management."""

    def test_config_file_creation(self):
        """Test ConfigFile creation."""
        config = ConfigFile(model="test-model")
        assert config.model == "test-model"

    def test_config_file_extra_fields(self):
        """Test ConfigFile allows extra fields."""
        config = ConfigFile(custom_field="value")
        assert config.custom_field == "value"

    def test_config_manager_initialization(self):
        """Test ConfigManager initializes."""
        manager = ConfigManager()
        assert manager.user_config_dir is not None
        assert manager.user_config_file is not None

    def test_config_manager_default_settings(self):
        """Test ConfigManager loads default settings."""
        manager = ConfigManager()
        assert manager.settings.model == "claude-opus-4-1"
        assert manager.settings.experimental is False

    def test_config_manager_get_model(self, temp_config_dir):
        """Test getting model configuration."""
        manager = ConfigManager()
        # Just verify the method returns a string
        model = manager.get_model()
        assert isinstance(model, str)
        assert model in ["claude-opus-4-1", "claude-sonnet-4"]

    def test_config_manager_is_experimental_enabled(self, temp_config_dir):
        """Test checking experimental mode."""
        manager = ConfigManager()
        # Just verify the method returns a boolean
        result = manager.is_experimental_enabled()
        assert isinstance(result, bool)


class TestLogging:
    """Test logging configuration."""

    def test_setup_logging(self):
        """Test logging setup completes without error."""
        setup_logging()
        logger = get_logger("test")
        assert logger is not None

    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test_module")
        assert logger is not None
        assert "march" in logger.name
