"""Tests for extension manifest parsing and validation."""

import json
from pathlib import Path

import pytest
import yaml

from mARCH.extension.manifest import ManifestParseError, ManifestValidator
from mARCH.extension.types import ExtensionType, SandboxLevel


class TestManifestValidator:
    """Test manifest parsing and validation."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for test manifests."""
        return tmp_path

    def test_load_yaml_manifest(self, temp_dir):
        """Test loading YAML manifest."""
        manifest_path = temp_dir / "manifest.yaml"
        manifest_data = {
            "name": "test-ext",
            "version": "1.0.0",
            "display_name": "Test Extension",
            "description": "Test",
            "type": "cli_command",
            "entry_point": "main.py",
        }
        manifest_path.write_text(yaml.dump(manifest_data))

        manifest = ManifestValidator.load_manifest(manifest_path)
        assert manifest.name == "test-ext"
        assert manifest.version == "1.0.0"

    def test_load_json_manifest(self, temp_dir):
        """Test loading JSON manifest."""
        manifest_path = temp_dir / "manifest.json"
        manifest_data = {
            "name": "test-ext",
            "version": "1.0.0",
            "display_name": "Test Extension",
            "description": "Test",
            "type": "tool",
            "entry_point": "main.py",
        }
        manifest_path.write_text(json.dumps(manifest_data))

        manifest = ManifestValidator.load_manifest(manifest_path)
        assert manifest.name == "test-ext"
        assert manifest.type == ExtensionType.TOOL

    def test_load_yml_manifest(self, temp_dir):
        """Test loading .yml manifest."""
        manifest_path = temp_dir / "manifest.yml"
        manifest_data = {
            "name": "test-ext",
            "version": "1.0.0",
            "display_name": "Test Extension",
            "description": "Test",
            "type": "mcp_server",
            "entry_point": "server.py",
        }
        manifest_path.write_text(yaml.dump(manifest_data))

        manifest = ManifestValidator.load_manifest(manifest_path)
        assert manifest.name == "test-ext"
        assert manifest.type == ExtensionType.MCP_SERVER

    def test_load_nonexistent_manifest(self):
        """Test loading nonexistent manifest."""
        with pytest.raises(ManifestParseError, match="not found"):
            ManifestValidator.load_manifest(Path("/nonexistent/manifest.yaml"))

    def test_load_unsupported_format(self, temp_dir):
        """Test loading unsupported manifest format."""
        manifest_path = temp_dir / "manifest.txt"
        manifest_path.write_text("invalid")

        with pytest.raises(ManifestParseError, match="Unsupported"):
            ManifestValidator.load_manifest(manifest_path)

    def test_load_invalid_yaml(self, temp_dir):
        """Test loading invalid YAML."""
        manifest_path = temp_dir / "manifest.yaml"
        manifest_path.write_text("{ invalid: yaml: content: }")

        with pytest.raises(ManifestParseError, match="Invalid YAML"):
            ManifestValidator.load_manifest(manifest_path)

    def test_load_invalid_json(self, temp_dir):
        """Test loading invalid JSON."""
        manifest_path = temp_dir / "manifest.json"
        manifest_path.write_text("{ invalid json }")

        with pytest.raises(ManifestParseError, match="Invalid JSON"):
            ManifestValidator.load_manifest(manifest_path)

    def test_validate_manifest_missing_required(self):
        """Test validation of manifest with missing required fields."""
        data = {"name": "test"}

        with pytest.raises(ManifestParseError):
            ManifestValidator.validate_manifest(data)

    def test_validate_manifest_valid(self):
        """Test validation of valid manifest data."""
        data = {
            "name": "test",
            "version": "1.0.0",
            "display_name": "Test",
            "description": "Test extension",
            "type": "tool",
            "entry_point": "main.py",
        }

        manifest = ManifestValidator.validate_manifest(data)
        assert manifest.name == "test"

    def test_validate_dependencies_all_available(self):
        """Test dependency validation when all available."""
        manifest_data = {
            "name": "dependent",
            "version": "1.0.0",
            "display_name": "Dependent",
            "description": "Depends on others",
            "type": "tool",
            "entry_point": "main.py",
            "dependencies": ["base", "helper"],
        }

        from mARCH.extension.contracts import ExtensionManifest

        manifest = ExtensionManifest(**manifest_data)
        missing = ManifestValidator.validate_dependencies(
            manifest, ["base", "helper", "other"]
        )

        assert missing == []

    def test_validate_dependencies_missing(self):
        """Test dependency validation with missing dependencies."""
        manifest_data = {
            "name": "dependent",
            "version": "1.0.0",
            "display_name": "Dependent",
            "description": "Depends on others",
            "type": "tool",
            "entry_point": "main.py",
            "dependencies": ["base", "missing"],
        }

        from mARCH.extension.contracts import ExtensionManifest

        manifest = ExtensionManifest(**manifest_data)
        missing = ManifestValidator.validate_dependencies(manifest, ["base"])

        assert "missing" in missing

    def test_check_circular_dependencies_none(self):
        """Test circular dependency check with no cycles."""
        from mARCH.extension.contracts import ExtensionManifest

        manifest_a = ExtensionManifest(
            name="a",
            version="1.0.0",
            display_name="A",
            description="A",
            type=ExtensionType.TOOL,
            entry_point="a.py",
            dependencies=["b"],
        )

        manifest_b = ExtensionManifest(
            name="b",
            version="1.0.0",
            display_name="B",
            description="B",
            type=ExtensionType.TOOL,
            entry_point="b.py",
        )

        manifests = {"a": manifest_a, "b": manifest_b}
        cycles = ManifestValidator.check_circular_dependencies(manifests)

        assert cycles == []

    def test_check_circular_dependencies_found(self):
        """Test circular dependency check with cycles."""
        from mARCH.extension.contracts import ExtensionManifest

        manifest_a = ExtensionManifest(
            name="a",
            version="1.0.0",
            display_name="A",
            description="A",
            type=ExtensionType.TOOL,
            entry_point="a.py",
            dependencies=["b"],
        )

        manifest_b = ExtensionManifest(
            name="b",
            version="1.0.0",
            display_name="B",
            description="B",
            type=ExtensionType.TOOL,
            entry_point="b.py",
            dependencies=["a"],
        )

        manifests = {"a": manifest_a, "b": manifest_b}
        cycles = ManifestValidator.check_circular_dependencies(manifests)

        assert len(cycles) > 0
