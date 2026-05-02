"""Session snapshot and recovery.

Checkpoint and recover agent state for fault tolerance.
"""

import logging
import json
import gzip
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from .models import Session

logger = logging.getLogger(__name__)


@dataclass
class SessionSnapshot:
    """Snapshot of a session state."""
    session_id: str
    agent_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_state: Dict[str, Any] = field(default_factory=dict)
    execution_context: Dict[str, Any] = field(default_factory=dict)
    in_progress_commands: List[str] = field(default_factory=list)
    error_state: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_state": self.agent_state,
            "execution_context": self.execution_context,
            "in_progress_commands": self.in_progress_commands,
            "error_state": self.error_state,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionSnapshot":
        """Create snapshot from dictionary."""
        return cls(
            session_id=data["session_id"],
            agent_id=data["agent_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            agent_state=data.get("agent_state", {}),
            execution_context=data.get("execution_context", {}),
            in_progress_commands=data.get("in_progress_commands", []),
            error_state=data.get("error_state"),
        )


class SnapshotManager:
    """Manages session snapshots for fault tolerance."""

    def __init__(self, snapshots_dir: Optional[Path] = None):
        """Initialize snapshot manager.

        Args:
            snapshots_dir: Directory for storing snapshots (default: ~/.mARCH/snapshots)
        """
        if snapshots_dir is None:
            snapshots_dir = Path.home() / ".mARCH" / "snapshots"
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots: Dict[str, SessionSnapshot] = {}

    async def create_snapshot(self, session: Session) -> SessionSnapshot:
        """Create a snapshot of the current session state.

        Args:
            session: Session to snapshot

        Returns:
            Created snapshot
        """
        snapshot = SessionSnapshot(
            session_id=session.session_id,
            agent_id=session.agent_id,
            execution_context=session.context.copy(),
            agent_state={"status": session.status, "metadata": session.metadata.copy()},
        )

        # Store in memory
        self._snapshots[snapshot.session_id] = snapshot

        # Persist to disk
        await self._persist_snapshot(snapshot)

        logger.info(f"Created snapshot for session {session.session_id}")
        return snapshot

    async def restore_from_snapshot(self, snapshot_id: str) -> Optional[SessionSnapshot]:
        """Restore agent state from a snapshot.

        Args:
            snapshot_id: Snapshot ID to restore from

        Returns:
            Restored snapshot if found, None otherwise
        """
        # Try memory first
        if snapshot_id in self._snapshots:
            return self._snapshots[snapshot_id]

        # Load from disk
        snapshot = await self._load_snapshot(snapshot_id)
        if snapshot:
            self._snapshots[snapshot_id] = snapshot
            logger.info(f"Restored snapshot {snapshot_id}")
        return snapshot

    async def list_snapshots(self, session_id: str) -> List[SessionSnapshot]:
        """List all snapshots for a session.

        Args:
            session_id: Session ID to query

        Returns:
            List of snapshots for the session
        """
        snapshots = []
        session_dir = self.snapshots_dir / session_id
        if session_dir.exists():
            for snapshot_file in sorted(session_dir.glob("*.json*")):
                snapshot = await self._load_snapshot(snapshot_file.stem)
                if snapshot:
                    snapshots.append(snapshot)
        return snapshots

    async def cleanup_old_snapshots(self, retention_days: int = 30) -> int:
        """Clean up old snapshots based on retention policy.

        Args:
            retention_days: Keep snapshots from last N days

        Returns:
            Number of snapshots cleaned up
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        deleted_count = 0

        for snapshot_file in self.snapshots_dir.glob("*/*.json*"):
            try:
                # Extract timestamp from filename or snapshot data
                snapshot = await self._load_snapshot(snapshot_file.stem)
                if snapshot and snapshot.timestamp < cutoff_date:
                    snapshot_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old snapshot {snapshot_file}")
            except Exception as e:
                logger.warning(f"Error cleaning up snapshot {snapshot_file}: {e}")

        logger.info(f"Cleaned up {deleted_count} old snapshots")
        return deleted_count

    # Private methods

    async def _persist_snapshot(self, snapshot: SessionSnapshot) -> bool:
        """Persist snapshot to disk.

        Args:
            snapshot: Snapshot to persist

        Returns:
            True if successful, False otherwise
        """
        try:
            session_dir = self.snapshots_dir / snapshot.session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            # Create filename with timestamp
            timestamp_str = snapshot.timestamp.strftime("%Y%m%d_%H%M%S_%f")
            filepath = session_dir / f"snapshot_{timestamp_str}.json.gz"

            # Serialize and compress
            data = snapshot.to_dict()
            content = json.dumps(data, indent=2).encode("utf-8")
            compressed = gzip.compress(content)

            with open(filepath, "wb") as f:
                f.write(compressed)

            logger.debug(f"Persisted snapshot to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist snapshot: {e}")
            return False

    async def _load_snapshot(self, snapshot_id: str) -> Optional[SessionSnapshot]:
        """Load snapshot from disk.

        Args:
            snapshot_id: Snapshot ID (usually a path relative to snapshots_dir)

        Returns:
            Loaded snapshot if found, None otherwise
        """
        try:
            # Try as a file path first
            filepath = self.snapshots_dir / f"{snapshot_id}.json.gz"
            if not filepath.exists():
                filepath = self.snapshots_dir / f"{snapshot_id}.json"

            if not filepath.exists():
                return None

            with open(filepath, "rb") as f:
                content = f.read()

            if filepath.suffix == ".gz":
                content = gzip.decompress(content)

            data = json.loads(content.decode("utf-8"))
            snapshot = SessionSnapshot.from_dict(data)

            logger.debug(f"Loaded snapshot from {filepath}")
            return snapshot
        except Exception as e:
            logger.error(f"Failed to load snapshot: {e}")
            return None
