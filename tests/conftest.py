"""
Pytest configuration and fixtures.
"""

import pytest
from pathlib import Path


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory for testing."""
    config_dir = tmp_path / ".copilot"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_config_file(temp_config_dir):
    """Create a sample config file."""
    config_file = temp_config_dir / "config.json"
    config_file.write_text(
        """{
    "model": "claude-sonnet-4.5",
    "experimental": false
}"""
    )
    return config_file
