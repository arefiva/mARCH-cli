"""Session lifecycle management.

Manages session creation, persistence, and recovery.
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from .models import Session, SessionConfig

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages session lifecycle.

    Singleton pattern for application-wide session management.
    """

    _instance: Optional["SessionManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the session manager."""
        if not hasattr(self, "_initialized"):
            self._sessions: Dict[str, Session] = {}
            self._session_lock = asyncio.Lock()
            self._persistence_backend = None
            self._snapshot_manager = None
            self._initialized = True

    async def create_session(
        self, agent_id: str, config: Optional[SessionConfig] = None
    ) -> Session:
        """Create a new session.

        Args:
            agent_id: ID of the agent owning this session
            config: Session configuration

        Returns:
            Newly created session
        """
        async with self._session_lock:
            config = config or SessionConfig()
            session = Session(agent_id=agent_id)
            self._sessions[session.session_id] = session
            logger.info(
                f"Created session {session.session_id} for agent {agent_id}"
            )

            # Auto-persist if enabled
            if config.auto_persist:
                await self.persist_session(session)

            return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session if found, None otherwise
        """
        async with self._session_lock:
            # Try memory first
            if session_id in self._sessions:
                return self._sessions[session_id]

            # Try persistence backend
            if self._persistence_backend:
                session = await self._persistence_backend.load(session_id)
                if session:
                    self._sessions[session_id] = session
                    return session

            return None

    async def list_sessions(
        self, filter_params: Optional[Dict[str, Any]] = None
    ) -> List[Session]:
        """List sessions with optional filtering.

        Args:
            filter_params: Optional filter criteria

        Returns:
            List of matching sessions
        """
        async with self._session_lock:
            sessions = list(self._sessions.values())

            if not filter_params:
                return sessions

            # Apply filters
            for key, value in filter_params.items():
                if key == "agent_id":
                    sessions = [s for s in sessions if s.agent_id == value]
                elif key == "status":
                    sessions = [s for s in sessions if s.status == value]
                elif key == "active_only":
                    if value:
                        sessions = [s for s in sessions if s.is_active()]

            return sessions

    async def persist_session(self, session: Session) -> bool:
        """Save session to storage.

        Args:
            session: Session to persist

        Returns:
            True if successful, False otherwise
        """
        if not self._persistence_backend:
            logger.debug("No persistence backend configured")
            return False

        try:
            await self._persistence_backend.save(session)
            logger.debug(f"Persisted session {session.session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist session: {e}")
            return False

    async def restore_session(self, session_id: str) -> Optional[Session]:
        """Load session from storage.

        Args:
            session_id: Session ID to restore

        Returns:
            Restored session if found, None otherwise
        """
        if not self._persistence_backend:
            logger.debug("No persistence backend configured")
            return None

        try:
            session = await self._persistence_backend.load(session_id)
            if session:
                async with self._session_lock:
                    self._sessions[session_id] = session
                logger.info(f"Restored session {session_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to restore session: {e}")
            return None

    async def cleanup_session(self, session_id: str) -> bool:
        """Clean up a session.

        Args:
            session_id: Session ID to clean up

        Returns:
            True if successful, False otherwise
        """
        async with self._session_lock:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found for cleanup")
                return False

            session = self._sessions.pop(session_id)
            session.status = "completed"

            # Persist final state
            if self._persistence_backend:
                try:
                    await self._persistence_backend.save(session)
                except Exception as e:
                    logger.error(f"Failed to persist cleanup: {e}")

            logger.info(f"Cleaned up session {session_id}")
            return True

    async def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """Clean up expired sessions.

        Args:
            max_age_seconds: Maximum age for sessions

        Returns:
            Number of sessions cleaned up
        """
        async with self._session_lock:
            now = datetime.utcnow()
            expired = []

            for session_id, session in self._sessions.items():
                age = (now - session.last_activity).total_seconds()
                if age > max_age_seconds:
                    expired.append(session_id)

            for session_id in expired:
                self._sessions.pop(session_id)
                logger.info(f"Cleaned up expired session {session_id}")

            return len(expired)

    async def migrate_session(
        self, session_id: str, from_version: str, to_version: str
    ) -> bool:
        """Migrate session to new schema version.

        Args:
            session_id: Session ID to migrate
            from_version: Current version
            to_version: Target version

        Returns:
            True if successful, False otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for migration")
            return False

        logger.info(f"Migrating session {session_id} from {from_version} to {to_version}")

        # Placeholder for migration logic
        # Actual migrations would be version-specific

        return True

    def set_persistence_backend(self, backend: Any) -> None:
        """Set the persistence backend.

        Args:
            backend: Persistence backend instance
        """
        self._persistence_backend = backend
        logger.info(f"Set persistence backend: {type(backend).__name__}")

    def set_snapshot_manager(self, manager: Any) -> None:
        """Set the snapshot manager.

        Args:
            manager: Snapshot manager instance
        """
        self._snapshot_manager = manager
        logger.info(f"Set snapshot manager: {type(manager).__name__}")

    @classmethod
    async def get_instance(cls) -> "SessionManager":
        """Get singleton instance.

        Returns:
            SessionManager instance
        """
        return cls()
