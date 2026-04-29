"""
State persistence layer for saving and restoring session state.

Handles conversation history, user preferences, and session data.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from copilot.exceptions import ConfigurationError


@dataclass
class SessionState:
    """Represents persisted session state."""

    session_id: str
    created_at: str
    last_activity: str
    model: str
    experimental_mode: bool = False
    theme: str = "dark"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ConversationSnapshot:
    """Snapshot of conversation for persistence."""

    conversation_id: str
    created_at: str
    last_message_at: str
    model: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationSnapshot":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class UserPreferences:
    """User preferences that persist across sessions."""

    recent_models: list[str] = field(default_factory=list)
    default_model: str = "claude-sonnet-4.5"
    theme: str = "dark"
    show_banner: bool = True
    enable_experimental: bool = False
    auto_save_conversations: bool = True
    max_conversation_history: int = 100
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPreferences":
        """Create from dictionary."""
        return cls(**data)


class StatePersistenceManager:
    """Manages persistence of user state, preferences, and conversations."""

    STATE_DIR_NAME = ".copilot"
    PREFERENCES_FILE = "preferences.json"
    SESSIONS_DIR = "sessions"
    CONVERSATIONS_DIR = "conversations"
    STATE_FILE = "state.json"

    def __init__(self, base_path: Path | None = None) -> None:
        """
        Initialize state persistence manager.

        Args:
            base_path: Base path for state storage (default: ~/.copilot)
        """
        if base_path:
            self.base_dir = base_path
        else:
            self.base_dir = Path.home() / self.STATE_DIR_NAME

        self.preferences_file = self.base_dir / self.PREFERENCES_FILE
        self.sessions_dir = self.base_dir / self.SESSIONS_DIR
        self.conversations_dir = self.base_dir / self.CONVERSATIONS_DIR
        self.state_file = self.base_dir / self.STATE_FILE

        self._preferences: UserPreferences | None = None
        self._current_session: SessionState | None = None

    def ensure_dirs(self) -> None:
        """Ensure all required directories exist."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.conversations_dir.mkdir(parents=True, exist_ok=True)

    def load_preferences(self) -> UserPreferences:
        """Load user preferences from storage."""
        if self._preferences is not None:
            return self._preferences

        self.ensure_dirs()

        if not self.preferences_file.exists():
            self._preferences = UserPreferences()
            return self._preferences

        try:
            with open(self.preferences_file) as f:
                data = json.load(f)
            self._preferences = UserPreferences.from_dict(data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise ConfigurationError(
                f"Failed to load preferences from {self.preferences_file}",
                details=str(e),
            )

        return self._preferences

    def save_preferences(self, preferences: UserPreferences) -> None:
        """Save user preferences to storage."""
        self.ensure_dirs()

        try:
            with open(self.preferences_file, "w") as f:
                json.dump(preferences.to_dict(), f, indent=2)
            self._preferences = preferences
        except OSError as e:
            raise ConfigurationError(
                f"Failed to save preferences to {self.preferences_file}",
                details=str(e),
            )

    def add_recent_model(self, model: str, max_recent: int = 10) -> None:
        """Add a model to recent models list."""
        prefs = self.load_preferences()

        # Remove if already exists (will be re-added to top)
        if model in prefs.recent_models:
            prefs.recent_models.remove(model)

        # Add to front
        prefs.recent_models.insert(0, model)

        # Limit list size
        prefs.recent_models = prefs.recent_models[:max_recent]

        self.save_preferences(prefs)

    def get_recent_models(self) -> list[str]:
        """Get list of recently used models."""
        return self.load_preferences().recent_models

    def update_default_model(self, model: str) -> None:
        """Update default AI model."""
        prefs = self.load_preferences()
        prefs.default_model = model
        self.add_recent_model(model)
        self.save_preferences(prefs)

    def load_session(self, session_id: str) -> SessionState | None:
        """Load session state."""
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return None

        try:
            with open(session_file) as f:
                data = json.load(f)
            return SessionState.from_dict(data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise ConfigurationError(
                f"Failed to load session {session_id}",
                details=str(e),
            )

    def save_session(self, session: SessionState) -> None:
        """Save session state."""
        self.ensure_dirs()

        session_file = self.sessions_dir / f"{session.session_id}.json"

        try:
            with open(session_file, "w") as f:
                json.dump(session.to_dict(), f, indent=2)
            self._current_session = session
        except OSError as e:
            raise ConfigurationError(
                f"Failed to save session {session.session_id}",
                details=str(e),
            )

    def list_sessions(self) -> list[str]:
        """List all saved session IDs."""
        self.ensure_dirs()

        if not self.sessions_dir.exists():
            return []

        return [
            f.stem for f in self.sessions_dir.glob("*.json")
        ]

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        session_file = self.sessions_dir / f"{session_id}.json"

        if session_file.exists():
            session_file.unlink()

    def save_conversation(self, snapshot: ConversationSnapshot) -> None:
        """Save conversation snapshot."""
        self.ensure_dirs()

        conv_file = self.conversations_dir / f"{snapshot.conversation_id}.json"

        try:
            with open(conv_file, "w") as f:
                json.dump(snapshot.to_dict(), f, indent=2)
        except OSError as e:
            raise ConfigurationError(
                f"Failed to save conversation {snapshot.conversation_id}",
                details=str(e),
            )

    def load_conversation(self, conversation_id: str) -> ConversationSnapshot | None:
        """Load conversation snapshot."""
        conv_file = self.conversations_dir / f"{conversation_id}.json"

        if not conv_file.exists():
            return None

        try:
            with open(conv_file) as f:
                data = json.load(f)
            return ConversationSnapshot.from_dict(data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise ConfigurationError(
                f"Failed to load conversation {conversation_id}",
                details=str(e),
            )

    def list_conversations(self) -> list[str]:
        """List all saved conversation IDs."""
        self.ensure_dirs()

        if not self.conversations_dir.exists():
            return []

        return [
            f.stem for f in self.conversations_dir.glob("*.json")
        ]

    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation."""
        conv_file = self.conversations_dir / f"{conversation_id}.json"

        if conv_file.exists():
            conv_file.unlink()

    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """
        Remove sessions older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of sessions deleted
        """
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=max_age_days)
        deleted_count = 0

        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                created_at = datetime.fromisoformat(data.get("created_at", ""))
                if created_at < cutoff:
                    session_file.unlink()
                    deleted_count += 1
            except (json.JSONDecodeError, ValueError):
                pass

        return deleted_count


# Global state manager instance
_state_manager: StatePersistenceManager | None = None


def get_state_manager() -> StatePersistenceManager:
    """Get or create global state persistence manager."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StatePersistenceManager()
        _state_manager.ensure_dirs()
    return _state_manager
