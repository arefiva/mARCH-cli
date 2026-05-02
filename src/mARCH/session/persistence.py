"""Persistence layer for sessions.

Hybrid JSON + SQLite persistence with conflict resolution.
"""

import asyncio
import json
import logging
import sqlite3
import gzip
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

from .models import Session, ExecutionHistoryEntry

logger = logging.getLogger(__name__)


class PersistenceBackend(ABC):
    """Abstract base for persistence backends."""

    @abstractmethod
    async def save(self, session: Session) -> None:
        """Save session to storage."""
        pass

    @abstractmethod
    async def load(self, session_id: str) -> Optional[Session]:
        """Load session from storage."""
        pass

    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete session."""
        pass

    @abstractmethod
    async def list_all(self) -> List[str]:
        """List all session IDs."""
        pass


class JSONPersistence(PersistenceBackend):
    """File-based JSON persistence."""

    def __init__(self, storage_dir: Optional[Path] = None, compression: bool = False):
        """Initialize JSON persistence.

        Args:
            storage_dir: Directory for storing sessions (default: ~/.mARCH/sessions)
            compression: Whether to gzip compress files
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".mARCH" / "sessions"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.compression = compression

    async def save(self, session: Session) -> None:
        """Save session to JSON file."""
        try:
            # Serialize session
            data = {
                "session_id": session.session_id,
                "agent_id": session.agent_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "status": session.status,
                "metadata": session.metadata,
                "context": session.context,
                "execution_history": [
                    {
                        "command": e.command,
                        "result": e.result,
                        "duration_ms": e.duration_ms,
                        "timestamp": e.timestamp.isoformat(),
                    }
                    for e in session.execution_history
                ],
            }

            # Write to file
            filepath = self.storage_dir / f"{session.session_id}.json"
            content = json.dumps(data, indent=2).encode("utf-8")

            if self.compression:
                filepath = Path(str(filepath) + ".gz")
                content = gzip.compress(content)

            with open(filepath, "wb") as f:
                f.write(content)

            logger.debug(f"Saved session {session.session_id} to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save session to JSON: {e}")
            raise

    async def load(self, session_id: str) -> Optional[Session]:
        """Load session from JSON file."""
        try:
            filepath = self.storage_dir / f"{session_id}.json"
            if self.compression:
                filepath = Path(str(filepath) + ".gz")

            if not filepath.exists():
                return None

            with open(filepath, "rb") as f:
                content = f.read()

            if self.compression:
                content = gzip.decompress(content)

            data = json.loads(content.decode("utf-8"))

            # Deserialize session
            from datetime import datetime
            session = Session(
                session_id=data["session_id"],
                agent_id=data["agent_id"],
                created_at=datetime.fromisoformat(data["created_at"]),
                last_activity=datetime.fromisoformat(data["last_activity"]),
                status=data["status"],
                metadata=data["metadata"],
                context=data["context"],
            )

            # Restore execution history
            for entry_data in data.get("execution_history", []):
                entry = ExecutionHistoryEntry(
                    command=entry_data["command"],
                    result=entry_data["result"],
                    duration_ms=entry_data["duration_ms"],
                    timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                )
                session.execution_history.append(entry)

            logger.debug(f"Loaded session {session_id} from {filepath}")
            return session
        except Exception as e:
            logger.error(f"Failed to load session from JSON: {e}")
            return None

    async def exists(self, session_id: str) -> bool:
        """Check if session file exists."""
        filepath = self.storage_dir / f"{session_id}.json"
        if self.compression:
            filepath = Path(str(filepath) + ".gz")
        return filepath.exists()

    async def delete(self, session_id: str) -> None:
        """Delete session file."""
        try:
            filepath = self.storage_dir / f"{session_id}.json"
            if self.compression:
                filepath = Path(str(filepath) + ".gz")
            if filepath.exists():
                filepath.unlink()
                logger.debug(f"Deleted session file {filepath}")
        except Exception as e:
            logger.error(f"Failed to delete session file: {e}")
            raise

    async def list_all(self) -> List[str]:
        """List all session IDs."""
        try:
            session_ids = []
            pattern = "*.json.gz" if self.compression else "*.json"
            for filepath in self.storage_dir.glob(pattern):
                session_id = filepath.stem
                if self.compression:
                    session_id = session_id[:-5]  # Remove .json
                session_ids.append(session_id)
            return session_ids
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []


class SQLitePersistence(PersistenceBackend):
    """SQLite-based persistence."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize SQLite persistence.

        Args:
            db_path: Path to SQLite database (default: ~/.mARCH/sessions.db)
        """
        if db_path is None:
            db_path = Path.home() / ".mARCH" / "sessions.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Create tables
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                agent_id TEXT,
                created_at TEXT,
                last_activity TEXT,
                status TEXT,
                metadata TEXT,
                context TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                command TEXT,
                result TEXT,
                duration_ms REAL,
                timestamp TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_index (
                session_id TEXT,
                agent_id TEXT,
                created_at TEXT,
                status TEXT,
                PRIMARY KEY (session_id)
            )
            """
        )

        # Create indices
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent ON session_index(agent_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_created ON session_index(created_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_status ON session_index(status)"
        )

        conn.commit()
        conn.close()

    async def save(self, session: Session) -> None:
        """Save session to SQLite."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Save session
            cursor.execute(
                """
                INSERT OR REPLACE INTO sessions
                (session_id, agent_id, created_at, last_activity, status, metadata, context)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.agent_id,
                    session.created_at.isoformat(),
                    session.last_activity.isoformat(),
                    session.status,
                    json.dumps(session.metadata),
                    json.dumps(session.context),
                ),
            )

            # Update index
            cursor.execute(
                """
                INSERT OR REPLACE INTO session_index
                (session_id, agent_id, created_at, status)
                VALUES (?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.agent_id,
                    session.created_at.isoformat(),
                    session.status,
                ),
            )

            conn.commit()
            conn.close()
            logger.debug(f"Saved session {session.session_id} to SQLite")
        except Exception as e:
            logger.error(f"Failed to save session to SQLite: {e}")
            raise

    async def load(self, session_id: str) -> Optional[Session]:
        """Load session from SQLite."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Load session
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            )
            row = cursor.fetchone()

            if not row:
                conn.close()
                return None

            from datetime import datetime
            session = Session(
                session_id=row["session_id"],
                agent_id=row["agent_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                last_activity=datetime.fromisoformat(row["last_activity"]),
                status=row["status"],
                metadata=json.loads(row["metadata"]),
                context=json.loads(row["context"]),
            )

            # Load execution history
            cursor.execute(
                "SELECT * FROM execution_history WHERE session_id = ? ORDER BY timestamp",
                (session_id,),
            )

            for row in cursor.fetchall():
                entry = ExecutionHistoryEntry(
                    command=row["command"],
                    result=json.loads(row["result"]),
                    duration_ms=row["duration_ms"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
                session.execution_history.append(entry)

            conn.close()
            logger.debug(f"Loaded session {session_id} from SQLite")
            return session
        except Exception as e:
            logger.error(f"Failed to load session from SQLite: {e}")
            return None

    async def exists(self, session_id: str) -> bool:
        """Check if session exists in SQLite."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)
            )
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except Exception as e:
            logger.error(f"Failed to check session existence: {e}")
            return False

    async def delete(self, session_id: str) -> None:
        """Delete session from SQLite."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM execution_history WHERE session_id = ?",
                         (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            cursor.execute(
                "DELETE FROM session_index WHERE session_id = ?", (session_id,)
            )
            conn.commit()
            conn.close()
            logger.debug(f"Deleted session {session_id} from SQLite")
        except Exception as e:
            logger.error(f"Failed to delete session from SQLite: {e}")
            raise

    async def list_all(self) -> List[str]:
        """List all session IDs from SQLite."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM sessions")
            session_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            return session_ids
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []


class HybridPersistence(PersistenceBackend):
    """Hybrid persistence using both JSON and SQLite."""

    def __init__(
        self,
        json_backend: Optional[JSONPersistence] = None,
        sqlite_backend: Optional[SQLitePersistence] = None,
        read_preference: str = "sqlite",
    ):
        """Initialize hybrid persistence.

        Args:
            json_backend: JSON backend instance
            sqlite_backend: SQLite backend instance
            read_preference: "sqlite" or "json" for read preference
        """
        self.json_backend = json_backend or JSONPersistence()
        self.sqlite_backend = sqlite_backend or SQLitePersistence()
        self.read_preference = read_preference

    async def save(self, session: Session) -> None:
        """Save to both backends."""
        errors = []
        try:
            await self.json_backend.save(session)
        except Exception as e:
            errors.append(f"JSON: {e}")
            logger.warning(f"Failed to save to JSON backend: {e}")

        try:
            await self.sqlite_backend.save(session)
        except Exception as e:
            errors.append(f"SQLite: {e}")
            logger.warning(f"Failed to save to SQLite backend: {e}")

        if errors:
            logger.error(f"Hybrid persistence errors: {errors}")

    async def load(self, session_id: str) -> Optional[Session]:
        """Load with fallback preference."""
        if self.read_preference == "sqlite":
            session = await self.sqlite_backend.load(session_id)
            if session:
                return session
            return await self.json_backend.load(session_id)
        else:
            session = await self.json_backend.load(session_id)
            if session:
                return session
            return await self.sqlite_backend.load(session_id)

    async def exists(self, session_id: str) -> bool:
        """Check existence in either backend."""
        json_exists = await self.json_backend.exists(session_id)
        sqlite_exists = await self.sqlite_backend.exists(session_id)
        return json_exists or sqlite_exists

    async def delete(self, session_id: str) -> None:
        """Delete from both backends."""
        try:
            await self.json_backend.delete(session_id)
        except Exception as e:
            logger.warning(f"Failed to delete from JSON: {e}")

        try:
            await self.sqlite_backend.delete(session_id)
        except Exception as e:
            logger.warning(f"Failed to delete from SQLite: {e}")

    async def list_all(self) -> List[str]:
        """List all sessions from primary backend."""
        if self.read_preference == "sqlite":
            return await self.sqlite_backend.list_all()
        else:
            return await self.json_backend.list_all()
