"""
Tests for Phase 7: Configuration & State Management.

Tests state persistence, user preferences, and LSP configuration.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from mARCH.config.lsp_config import (
    get_lsp_config_manager,
)
from mARCH.exceptions import ConfigurationError
from mARCH.state.state_persistence import (
    ConversationSnapshot,
    SessionState,
    StatePersistenceManager,
    UserPreferences,
    get_state_manager,
)


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

