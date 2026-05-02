"""Session management framework.

Provides session lifecycle management, persistence, and recovery.
"""

from .session_manager import SessionManager
from .models import Session, SessionConfig, ExecutionHistoryEntry
from .persistence import JSONPersistence, SQLitePersistence, HybridPersistence
from .recovery import SessionSnapshot, SnapshotManager

__all__ = [
    "SessionManager",
    "Session",
    "SessionConfig",
    "ExecutionHistoryEntry",
    "JSONPersistence",
    "SQLitePersistence",
    "HybridPersistence",
    "SessionSnapshot",
    "SnapshotManager",
]
