"""Session data models.

Dataclasses for session management and configuration.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


@dataclass
class ExecutionHistoryEntry:
    """Entry in execution history."""
    command: str
    result: Dict[str, Any]
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SessionConfig:
    """Configuration for session lifecycle."""
    max_lifetime_seconds: int = 3600  # 1 hour
    auto_persist: bool = True
    persist_interval_seconds: int = 30
    compression_enabled: bool = False
    cleanup_on_shutdown: bool = True
    max_history_entries: int = 1000


@dataclass
class Session:
    """Represents an agent session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"  # active, paused, completed, failed
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    execution_history: List[ExecutionHistoryEntry] = field(default_factory=list)

    def add_to_history(
        self, command: str, result: Dict[str, Any], duration_ms: float
    ) -> None:
        """Add an entry to execution history.

        Args:
            command: The command executed
            result: The result of execution
            duration_ms: Duration in milliseconds
        """
        self.execution_history.append(
            ExecutionHistoryEntry(
                command=command,
                result=result,
                duration_ms=duration_ms,
            )
        )
        self.last_activity = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status == "active"

    def update_context(self, updates: Dict[str, Any]) -> None:
        """Update session context.

        Args:
            updates: Dictionary of context updates
        """
        self.context.update(updates)
        self.last_activity = datetime.utcnow()

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Session(id={self.session_id[:8]}..., "
            f"agent={self.agent_id}, status={self.status})"
        )
