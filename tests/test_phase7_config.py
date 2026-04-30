"""
Tests for Phase 7: Configuration & State Management.

Tests state persistence, user preferences, and LSP configuration.
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mARCH.state.state_persistence import (
    StatePersistenceManager,
    SessionState,
    ConversationSnapshot,
    UserPreferences,
    get_state_manager,
)
from mARCH.config.lsp_config import (
    LSPConfigManager,
    LSPServerConfig,
    get_lsp_config_manager,
)
from mARCH.exceptions import ConfigurationError


class TestUserPreferences:
    """Test UserPreferences dataclass."""

    def test_create_default_preferences(self):
        """Test creating preferences with defaults."""
        prefs = UserPreferences()
        assert prefs.default_model == "claude-sonnet-4.5"
        assert prefs.theme == "dark"
        assert prefs.show_banner is True
        assert prefs.enable_experimental is False
        assert prefs.auto_save_conversations is True
        assert prefs.max_conversation_history == 100

    def test_preferences_to_dict(self):
        """Test converting preferences to dictionary."""
        prefs = UserPreferences(theme="light", enable_experimental=True)
        data = prefs.to_dict()

        assert data["theme"] == "light"
        assert data["enable_experimental"] is True
        assert data["default_model"] == "claude-sonnet-4.5"

    def test_preferences_from_dict(self):
        """Test creating preferences from dictionary."""
        data = {
            "recent_models": ["gpt-4", "claude-opus"],
            "default_model": "gpt-4",
            "theme": "light",
            "show_banner": False,
            "enable_experimental": True,
            "auto_save_conversations": False,
            "max_conversation_history": 50,
            "metadata": {"custom": "value"},
        }
        prefs = UserPreferences.from_dict(data)

        assert prefs.recent_models == ["gpt-4", "claude-opus"]
        assert prefs.default_model == "gpt-4"
        assert prefs.theme == "light"
        assert prefs.show_banner is False
        assert prefs.enable_experimental is True
        assert prefs.max_conversation_history == 50


class TestSessionState:
    """Test SessionState dataclass."""

    def test_create_session_state(self):
        """Test creating session state."""
        now = datetime.now().isoformat()
        state = SessionState(
            session_id="test-session",
            created_at=now,
            last_activity=now,
            model="claude-sonnet-4.5",
        )

        assert state.session_id == "test-session"
        assert state.model == "claude-sonnet-4.5"
        assert state.experimental_mode is False
        assert state.theme == "dark"

    def test_session_state_to_dict(self):
        """Test converting session state to dictionary."""
        now = datetime.now().isoformat()
        state = SessionState(
            session_id="test",
            created_at=now,
            last_activity=now,
            model="gpt-4",
            experimental_mode=True,
        )
        data = state.to_dict()

        assert data["session_id"] == "test"
        assert data["model"] == "gpt-4"
        assert data["experimental_mode"] is True

    def test_session_state_from_dict(self):
        """Test creating session state from dictionary."""
        now = datetime.now().isoformat()
        data = {
            "session_id": "test",
            "created_at": now,
            "last_activity": now,
            "model": "claude-opus",
            "experimental_mode": True,
            "theme": "light",
            "metadata": {"key": "value"},
        }
        state = SessionState.from_dict(data)

        assert state.session_id == "test"
        assert state.model == "claude-opus"
        assert state.experimental_mode is True
        assert state.metadata["key"] == "value"


class TestConversationSnapshot:
    """Test ConversationSnapshot dataclass."""

    def test_create_conversation_snapshot(self):
        """Test creating conversation snapshot."""
        now = datetime.now().isoformat()
        snapshot = ConversationSnapshot(
            conversation_id="conv-1",
            created_at=now,
            last_message_at=now,
            model="claude-sonnet-4.5",
        )

        assert snapshot.conversation_id == "conv-1"
        assert snapshot.model == "claude-sonnet-4.5"
        assert snapshot.messages == []

    def test_snapshot_with_messages(self):
        """Test snapshot with messages."""
        now = datetime.now().isoformat()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        snapshot = ConversationSnapshot(
            conversation_id="conv-1",
            created_at=now,
            last_message_at=now,
            model="claude-sonnet-4.5",
            messages=messages,
        )

        assert len(snapshot.messages) == 2
        assert snapshot.messages[0]["role"] == "user"


class TestStatePersistenceManager:
    """Test state persistence manager."""

    @pytest.fixture
    def temp_state_dir(self):
        """Provide temporary state directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_create_manager(self, temp_state_dir):
        """Test creating state manager."""
        manager = StatePersistenceManager(temp_state_dir)
        assert manager.base_dir == temp_state_dir

    def test_ensure_dirs(self, temp_state_dir):
        """Test directory creation."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.ensure_dirs()

        assert manager.base_dir.exists()
        assert manager.sessions_dir.exists()
        assert manager.conversations_dir.exists()

    def test_load_default_preferences(self, temp_state_dir):
        """Test loading default preferences when no file exists."""
        manager = StatePersistenceManager(temp_state_dir)
        prefs = manager.load_preferences()

        assert isinstance(prefs, UserPreferences)
        assert prefs.default_model == "claude-sonnet-4.5"

    def test_save_and_load_preferences(self, temp_state_dir):
        """Test saving and loading preferences."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.ensure_dirs()

        prefs = UserPreferences(theme="light", enable_experimental=True)
        manager.save_preferences(prefs)

        loaded = manager.load_preferences()
        assert loaded.theme == "light"
        assert loaded.enable_experimental is True

    def test_add_recent_model(self, temp_state_dir):
        """Test adding recent models."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.add_recent_model("claude-opus")
        manager.add_recent_model("gpt-4")
        manager.add_recent_model("claude-sonnet")

        recent = manager.get_recent_models()
        assert recent[0] == "claude-sonnet"
        assert "claude-opus" in recent

    def test_recent_models_limit(self, temp_state_dir):
        """Test that recent models list is limited."""
        manager = StatePersistenceManager(temp_state_dir)

        for i in range(15):
            manager.add_recent_model(f"model-{i}")

        recent = manager.get_recent_models()
        assert len(recent) <= 10

    def test_update_default_model(self, temp_state_dir):
        """Test updating default model."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.update_default_model("gpt-4")

        prefs = manager.load_preferences()
        assert prefs.default_model == "gpt-4"
        assert "gpt-4" in prefs.recent_models

    def test_save_and_load_session(self, temp_state_dir):
        """Test saving and loading session."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.ensure_dirs()

        now = datetime.now().isoformat()
        session = SessionState(
            session_id="test-session",
            created_at=now,
            last_activity=now,
            model="claude-sonnet-4.5",
        )

        manager.save_session(session)
        loaded = manager.load_session("test-session")

        assert loaded is not None
        assert loaded.session_id == "test-session"
        assert loaded.model == "claude-sonnet-4.5"

    def test_load_nonexistent_session(self, temp_state_dir):
        """Test loading non-existent session returns None."""
        manager = StatePersistenceManager(temp_state_dir)
        result = manager.load_session("nonexistent")
        assert result is None

    def test_list_sessions(self, temp_state_dir):
        """Test listing sessions."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.ensure_dirs()

        now = datetime.now().isoformat()
        for i in range(3):
            session = SessionState(
                session_id=f"session-{i}",
                created_at=now,
                last_activity=now,
                model="claude-sonnet-4.5",
            )
            manager.save_session(session)

        sessions = manager.list_sessions()
        assert len(sessions) == 3
        assert "session-0" in sessions

    def test_delete_session(self, temp_state_dir):
        """Test deleting a session."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.ensure_dirs()

        now = datetime.now().isoformat()
        session = SessionState(
            session_id="temp-session",
            created_at=now,
            last_activity=now,
            model="claude-sonnet-4.5",
        )
        manager.save_session(session)
        manager.delete_session("temp-session")

        result = manager.load_session("temp-session")
        assert result is None

    def test_save_and_load_conversation(self, temp_state_dir):
        """Test saving and loading conversation."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.ensure_dirs()

        now = datetime.now().isoformat()
        snapshot = ConversationSnapshot(
            conversation_id="conv-1",
            created_at=now,
            last_message_at=now,
            model="claude-sonnet-4.5",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ],
        )

        manager.save_conversation(snapshot)
        loaded = manager.load_conversation("conv-1")

        assert loaded is not None
        assert loaded.conversation_id == "conv-1"
        assert len(loaded.messages) == 2

    def test_list_conversations(self, temp_state_dir):
        """Test listing conversations."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.ensure_dirs()

        now = datetime.now().isoformat()
        for i in range(3):
            snapshot = ConversationSnapshot(
                conversation_id=f"conv-{i}",
                created_at=now,
                last_message_at=now,
                model="claude-sonnet-4.5",
            )
            manager.save_conversation(snapshot)

        convs = manager.list_conversations()
        assert len(convs) == 3

    def test_delete_conversation(self, temp_state_dir):
        """Test deleting a conversation."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.ensure_dirs()

        now = datetime.now().isoformat()
        snapshot = ConversationSnapshot(
            conversation_id="temp-conv",
            created_at=now,
            last_message_at=now,
            model="claude-sonnet-4.5",
        )
        manager.save_conversation(snapshot)
        manager.delete_conversation("temp-conv")

        result = manager.load_conversation("temp-conv")
        assert result is None

    def test_cleanup_old_sessions(self, temp_state_dir):
        """Test cleaning up old sessions."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.ensure_dirs()

        now = datetime.now().isoformat()
        old_date = (datetime.now() - timedelta(days=31)).isoformat()

        # Add old session
        old_session = SessionState(
            session_id="old-session",
            created_at=old_date,
            last_activity=old_date,
            model="claude-sonnet-4.5",
        )
        manager.save_session(old_session)

        # Add recent session
        recent_session = SessionState(
            session_id="recent-session",
            created_at=now,
            last_activity=now,
            model="claude-sonnet-4.5",
        )
        manager.save_session(recent_session)

        deleted = manager.cleanup_old_sessions(max_age_days=30)
        assert deleted >= 1

        # Old session should be gone
        assert manager.load_session("old-session") is None
        # Recent session should remain
        assert manager.load_session("recent-session") is not None

    def test_invalid_preferences_file(self, temp_state_dir):
        """Test handling of invalid preferences file."""
        manager = StatePersistenceManager(temp_state_dir)
        manager.ensure_dirs()

        # Write invalid JSON
        with open(manager.preferences_file, "w") as f:
            f.write("invalid json {")

        with pytest.raises(ConfigurationError):
            manager.load_preferences()


class TestLSPServerConfig:
    """Test LSP server configuration."""

    def test_create_server_config(self):
        """Test creating server config."""
        config = LSPServerConfig(
            language="python",
            command="pylsp",
        )

        assert config.language == "python"
        assert config.command == "pylsp"
        assert config.enabled is True

    def test_server_config_with_args(self):
        """Test server config with arguments."""
        config = LSPServerConfig(
            language="typescript",
            command="typescript-language-server",
            args=["--stdio"],
        )

        assert config.args == ["--stdio"]

    def test_server_config_to_dict(self):
        """Test converting to dictionary."""
        config = LSPServerConfig(
            language="python",
            command="pylsp",
            enabled=False,
        )
        data = config.to_dict()

        assert data["language"] == "python"
        assert data["command"] == "pylsp"
        assert data["enabled"] is False

    def test_server_config_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "language": "go",
            "command": "gopls",
            "args": ["--debug", "localhost:6060"],
            "enabled": True,
            "initializationOptions": {"usePlaceholders": True},
            "settings": {},
            "env": {"GOFLAGS": "-mod=mod"},
        }
        config = LSPServerConfig.from_dict(data)

        assert config.language == "go"
        assert config.command == "gopls"
        assert config.args == ["--debug", "localhost:6060"]
        assert config.env["GOFLAGS"] == "-mod=mod"


class TestLSPConfigManager:
    """Test LSP configuration manager."""

    @pytest.fixture
    def temp_lsp_config(self):
        """Provide temporary LSP config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "lsp-config.json"
            yield config_file

    def test_create_manager(self, temp_lsp_config):
        """Test creating LSP config manager."""
        manager = LSPConfigManager(temp_lsp_config)
        assert manager.config_file == temp_lsp_config

    def test_default_servers_loaded(self, temp_lsp_config):
        """Test that default servers are loaded."""
        manager = LSPConfigManager(temp_lsp_config)
        servers = manager.list_servers()

        assert "python" in servers
        assert "javascript" in servers
        assert "go" in servers
        assert "rust" in servers

    def test_get_server_config(self, temp_lsp_config):
        """Test getting server config."""
        manager = LSPConfigManager(temp_lsp_config)
        config = manager.get_server_config("python")

        assert config is not None
        assert config.language == "python"
        assert config.command == "pylsp"

    def test_get_nonexistent_server(self, temp_lsp_config):
        """Test getting non-existent server."""
        manager = LSPConfigManager(temp_lsp_config)
        config = manager.get_server_config("nonexistent")
        assert config is None

    def test_set_server_config(self, temp_lsp_config):
        """Test setting server config."""
        manager = LSPConfigManager(temp_lsp_config)
        config = LSPServerConfig(
            language="custom",
            command="custom-lsp",
            args=["--mode", "stdio"],
        )

        manager.set_server_config("custom", config)
        loaded = manager.get_server_config("custom")

        assert loaded is not None
        assert loaded.command == "custom-lsp"

    def test_enable_disable_server(self, temp_lsp_config):
        """Test enabling and disabling servers."""
        manager = LSPConfigManager(temp_lsp_config)

        manager.disable_server("python")
        assert manager.is_server_enabled("python") is False

        manager.enable_server("python")
        assert manager.is_server_enabled("python") is True

    def test_list_enabled_servers(self, temp_lsp_config):
        """Test listing enabled servers."""
        manager = LSPConfigManager(temp_lsp_config)

        manager.disable_server("python")
        manager.disable_server("javascript")

        enabled = manager.list_enabled_servers()
        assert "python" not in enabled
        assert "javascript" not in enabled

    def test_update_server_command(self, temp_lsp_config):
        """Test updating server command."""
        manager = LSPConfigManager(temp_lsp_config)
        manager.update_server_command(
            "python",
            "pylsp-new",
            ["--debug"],
        )

        config = manager.get_server_config("python")
        assert config.command == "pylsp-new"
        assert config.args == ["--debug"]

    def test_reset_to_defaults(self, temp_lsp_config):
        """Test resetting to defaults."""
        manager = LSPConfigManager(temp_lsp_config)

        # Modify config
        manager.disable_server("python")
        config_before = manager.get_server_config("python")
        assert config_before.enabled is False

        # Reset
        manager.reset_to_defaults()

        # Verify reset
        config_after = manager.get_server_config("python")
        assert config_after.enabled is True
        assert config_after.command == "pylsp"

    def test_save_and_load_config(self, temp_lsp_config):
        """Test saving and loading configuration."""
        manager = LSPConfigManager(temp_lsp_config)

        config = LSPServerConfig(
            language="test-lang",
            command="test-lsp",
        )
        manager.set_server_config("test-lang", config)

        # Create new manager to load from file
        manager2 = LSPConfigManager(temp_lsp_config)
        loaded = manager2.get_server_config("test-lang")

        assert loaded is not None
        assert loaded.command == "test-lsp"

    def test_invalid_config_file(self, temp_lsp_config):
        """Test handling of invalid config file."""
        # Write invalid JSON
        temp_lsp_config.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_lsp_config, "w") as f:
            f.write("invalid json {")

        with pytest.raises(ConfigurationError):
            LSPConfigManager(temp_lsp_config)

    def test_get_all_servers(self, temp_lsp_config):
        """Test getting all servers."""
        manager = LSPConfigManager(temp_lsp_config)
        servers = manager.get_all_servers()

        assert isinstance(servers, dict)
        assert "python" in servers
        assert isinstance(servers["python"], LSPServerConfig)


class TestGlobalManagers:
    """Test global manager singleton instances."""

    def test_get_state_manager_singleton(self):
        """Test state manager singleton."""
        manager1 = get_state_manager()
        manager2 = get_state_manager()

        assert manager1 is manager2

    def test_get_lsp_config_manager_singleton(self):
        """Test LSP config manager singleton."""
        manager1 = get_lsp_config_manager()
        manager2 = get_lsp_config_manager()

        assert manager1 is manager2


class TestIntegration:
    """Integration tests for Phase 7."""

    @pytest.fixture
    def temp_state_dir(self):
        """Provide temporary state directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_complete_workflow(self, temp_state_dir):
        """Test complete state management workflow."""
        manager = StatePersistenceManager(temp_state_dir)

        # Create session
        now = datetime.now().isoformat()
        session = SessionState(
            session_id="workflow-test",
            created_at=now,
            last_activity=now,
            model="claude-sonnet-4.5",
        )
        manager.save_session(session)

        # Save conversation
        snapshot = ConversationSnapshot(
            conversation_id="conv-workflow",
            created_at=now,
            last_message_at=now,
            model="claude-sonnet-4.5",
            messages=[
                {"role": "user", "content": "Test message"},
                {"role": "assistant", "content": "Test response"},
            ],
        )
        manager.save_conversation(snapshot)

        # Update preferences
        prefs = manager.load_preferences()
        prefs.theme = "light"
        manager.save_preferences(prefs)

        # Verify all persisted
        assert manager.load_session("workflow-test") is not None
        assert manager.load_conversation("conv-workflow") is not None
        assert manager.load_preferences().theme == "light"

    def test_lsp_config_workflow(self):
        """Test LSP configuration workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "lsp.json"
            manager = LSPConfigManager(config_file)

            # Update Python server
            manager.update_server_command("python", "pylsp-custom", ["--log-level", "debug"])

            # Verify changes
            config = manager.get_server_config("python")
            assert config.command == "pylsp-custom"
            assert "--log-level" in config.args

            # Disable JavaScript
            manager.disable_server("javascript")
            assert manager.is_server_enabled("javascript") is False

            # List enabled (should include python since we didn't disable it)
            enabled = manager.list_enabled_servers()
            assert "javascript" not in enabled
            assert "python" in enabled  # Should be enabled since we only changed command
