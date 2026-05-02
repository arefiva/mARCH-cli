"""Tests for extension contracts and types."""

import pytest
from pydantic import ValidationError

from mARCH.extension.contracts import (
    ExtensionCapability,
    ExtensionConfig,
    ExtensionManifest,
    ExtensionPermission,
)
from mARCH.extension.types import ExtensionType, SandboxLevel


class TestExtensionCapability:
    """Test ExtensionCapability model."""

    def test_capability_creation(self):
        """Test creating a capability."""
        cap = ExtensionCapability(name="test_capability")
        assert cap.name == "test_capability"
        assert cap.version == "1.0.0"
        assert cap.methods == []

    def test_capability_with_methods(self):
        """Test capability with methods."""
        cap = ExtensionCapability(
            name="calculator", methods=["add", "subtract", "multiply"]
        )
        assert len(cap.methods) == 3
        assert "add" in cap.methods


class TestExtensionPermission:
    """Test ExtensionPermission model."""

    def test_permission_creation(self):
        """Test creating a permission."""
        perm = ExtensionPermission(type="file_read")
        assert perm.type == "file_read"
        assert perm.resource is None

    def test_permission_with_resource(self):
        """Test permission with specific resource."""
        perm = ExtensionPermission(
            type="file_read", resource="/home/user/projects/**"
        )
        assert perm.resource == "/home/user/projects/**"


class TestExtensionManifest:
    """Test ExtensionManifest model."""

    def test_manifest_creation_minimal(self):
        """Test creating minimal manifest."""
        manifest = ExtensionManifest(
            name="test-extension",
            version="1.0.0",
            display_name="Test Extension",
            description="A test extension",
            type=ExtensionType.CLI_COMMAND,
            entry_point="test.py",
        )
        assert manifest.name == "test-extension"
        assert manifest.version == "1.0.0"
        assert manifest.type == ExtensionType.CLI_COMMAND
        assert manifest.sandbox_level == SandboxLevel.FILE_RESTRICTED

    def test_manifest_creation_full(self):
        """Test creating full manifest."""
        manifest = ExtensionManifest(
            name="full-extension",
            version="2.0.0",
            display_name="Full Extension",
            description="A full extension",
            author="Test Author",
            license="MIT",
            homepage="https://example.com",
            repository="https://github.com/example/repo",
            type=ExtensionType.TOOL,
            entry_point="main.py",
            dependencies=["base-extension"],
            required_version=">=0.1.0",
            sandbox_level=SandboxLevel.NONE,
            permissions=[
                ExtensionPermission(
                    type="file_read", resource="/home/user/**"
                )
            ],
            capabilities=[
                ExtensionCapability(
                    name="analyze", methods=["analyze_code"]
                )
            ],
        )
        assert manifest.author == "Test Author"
        assert len(manifest.dependencies) == 1
        assert manifest.sandbox_level == SandboxLevel.NONE

    def test_manifest_validation_missing_required(self):
        """Test manifest validation with missing required fields."""
        with pytest.raises(ValidationError):
            ExtensionManifest(name="incomplete")

    def test_manifest_default_values(self):
        """Test manifest default values."""
        manifest = ExtensionManifest(
            name="test",
            version="1.0.0",
            display_name="Test",
            description="Test",
            type=ExtensionType.SKILL,
            entry_point="main.py",
        )
        assert manifest.author is None
        assert manifest.dependencies == []
        assert manifest.permissions == []
        assert manifest.capabilities == []


class TestExtensionConfig:
    """Test ExtensionConfig model."""

    def test_config_creation(self):
        """Test creating extension config."""
        config = ExtensionConfig(extension_name="test-ext")
        assert config.extension_name == "test-ext"
        assert config.enabled is True
        assert config.auto_load is True

    def test_config_with_settings(self):
        """Test config with custom settings."""
        config = ExtensionConfig(
            extension_name="test-ext",
            enabled=False,
            settings={"timeout": 30, "debug": True},
        )
        assert config.enabled is False
        assert config.settings["timeout"] == 30


class TestExtensionTypes:
    """Test extension type enums."""

    def test_extension_types(self):
        """Test all extension types are defined."""
        assert ExtensionType.CLI_COMMAND.value == "cli_command"
        assert ExtensionType.TOOL.value == "tool"
        assert ExtensionType.MCP_SERVER.value == "mcp_server"
        assert ExtensionType.SCRIPT.value == "script"
        assert ExtensionType.SKILL.value == "skill"

    def test_sandbox_levels(self):
        """Test all sandbox levels are defined."""
        assert SandboxLevel.NONE.value == "none"
        assert SandboxLevel.FILE_RESTRICTED.value == "file_restricted"
        assert SandboxLevel.PROCESS_ISOLATED.value == "process_isolated"
