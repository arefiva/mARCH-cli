"""Connection lifecycle and state management.

Manages connection pooling, health checking, and resource cleanup.
"""

import asyncio
import time
from enum import Enum
from typing import Dict, List, Optional


class ConnectionState(Enum):
    """States of a network connection."""

    CLOSED = "closed"
    CONNECTING = "connecting"
    OPEN = "open"
    CLOSING = "closing"


class Connection:
    """Represents a single network connection."""

    def __init__(self, endpoint: str, connection_id: Optional[str] = None):
        """Initialize connection.

        Args:
            endpoint: Connection endpoint (e.g., URL, socket path).
            connection_id: Optional unique identifier for connection.
        """
        self.endpoint = endpoint
        self.connection_id = connection_id or id(self)
        self.state = ConnectionState.CLOSED
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.metadata: Dict[str, any] = {}

    def mark_used(self) -> None:
        """Mark connection as recently used."""
        self.last_used_at = time.time()

    def is_idle(self, idle_timeout: float) -> bool:
        """Check if connection is idle.

        Args:
            idle_timeout: Idle timeout in seconds.

        Returns:
            True if connection hasn't been used within idle_timeout.
        """
        return time.time() - self.last_used_at > idle_timeout

    def get_age(self) -> float:
        """Get connection age in seconds.

        Returns:
            Age of connection in seconds.
        """
        return time.time() - self.created_at

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Connection(endpoint={self.endpoint}, "
            f"id={self.connection_id}, state={self.state.value})"
        )


class ConnectionManager:
    """Manages multiple connections with pooling and health checking."""

    def __init__(
        self,
        max_connections_per_endpoint: int = 10,
        idle_timeout: float = 300.0,
        max_connection_age: float = 3600.0,
    ):
        """Initialize connection manager.

        Args:
            max_connections_per_endpoint: Maximum connections per endpoint.
            idle_timeout: Timeout for idle connections in seconds.
            max_connection_age: Maximum connection age in seconds.
        """
        self.max_connections_per_endpoint = max_connections_per_endpoint
        self.idle_timeout = idle_timeout
        self.max_connection_age = max_connection_age

        self._connections: Dict[str, List[Connection]] = {}
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task[None]] = None

    async def acquire(self, endpoint: str) -> Connection:
        """Acquire a connection to an endpoint.

        Reuses existing idle connections or creates new ones.

        Args:
            endpoint: Connection endpoint.

        Returns:
            Connection instance.
        """
        async with self._lock:
            # Clean expired connections
            await self._cleanup_expired_connections(endpoint)

            # Try to reuse idle connection
            connections = self._connections.get(endpoint, [])
            for conn in connections:
                if conn.state == ConnectionState.OPEN and conn.is_idle(0):
                    conn.mark_used()
                    return conn

            # Create new connection if under limit
            if len(connections) < self.max_connections_per_endpoint:
                conn = Connection(endpoint)
                conn.state = ConnectionState.OPEN
                conn.mark_used()

                if endpoint not in self._connections:
                    self._connections[endpoint] = []
                self._connections[endpoint].append(conn)
                return conn

            # Wait for a connection to become available
            return await self._wait_for_available_connection(endpoint)

    async def release(self, connection: Connection) -> None:
        """Release a connection back to the pool.

        Args:
            connection: Connection to release.
        """
        async with self._lock:
            connection.mark_used()
            # Connection remains in pool for reuse

    async def close(self, connection: Connection) -> None:
        """Close a connection.

        Args:
            connection: Connection to close.
        """
        async with self._lock:
            connection.state = ConnectionState.CLOSED
            if connection.endpoint in self._connections:
                try:
                    self._connections[connection.endpoint].remove(connection)
                except ValueError:
                    pass

    async def close_endpoint(self, endpoint: str) -> None:
        """Close all connections to an endpoint.

        Args:
            endpoint: Endpoint to close connections for.
        """
        async with self._lock:
            if endpoint in self._connections:
                for conn in self._connections[endpoint]:
                    conn.state = ConnectionState.CLOSED
                del self._connections[endpoint]

    async def close_all(self) -> None:
        """Close all connections."""
        async with self._lock:
            for connections in self._connections.values():
                for conn in connections:
                    conn.state = ConnectionState.CLOSED
            self._connections.clear()

    async def start_health_check(self, interval: float = 60.0) -> None:
        """Start background health check task.

        Args:
            interval: Health check interval in seconds.
        """
        if self._health_check_task and not self._health_check_task.done():
            return

        self._health_check_task = asyncio.create_task(
            self._health_check_loop(interval)
        )

    async def stop_health_check(self) -> None:
        """Stop background health check task."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

    async def get_stats(self) -> Dict[str, any]:
        """Get connection pool statistics.

        Returns:
            Dictionary with pool statistics.
        """
        async with self._lock:
            total_connections = sum(len(conns) for conns in self._connections.values())
            endpoints = len(self._connections)
            open_connections = sum(
                1
                for conns in self._connections.values()
                for conn in conns
                if conn.state == ConnectionState.OPEN
            )

            return {
                "total_connections": total_connections,
                "open_connections": open_connections,
                "endpoints": endpoints,
                "connections_per_endpoint": {
                    endpoint: len(conns)
                    for endpoint, conns in self._connections.items()
                },
            }

    async def _cleanup_expired_connections(self, endpoint: str) -> None:
        """Clean up expired connections for an endpoint.

        Args:
            endpoint: Endpoint to clean.
        """
        if endpoint not in self._connections:
            return

        connections = self._connections[endpoint]
        to_remove = []

        for conn in connections:
            # Remove idle connections
            if conn.is_idle(self.idle_timeout):
                to_remove.append(conn)
                conn.state = ConnectionState.CLOSED
            # Remove old connections
            elif conn.get_age() > self.max_connection_age:
                to_remove.append(conn)
                conn.state = ConnectionState.CLOSED

        for conn in to_remove:
            connections.remove(conn)

        if not connections:
            del self._connections[endpoint]

    async def _wait_for_available_connection(
        self, endpoint: str, timeout: float = 5.0
    ) -> Connection:
        """Wait for a connection to become available.

        Args:
            endpoint: Endpoint to wait for.
            timeout: Wait timeout in seconds.

        Returns:
            Available connection.

        Raises:
            TimeoutError: If no connection becomes available within timeout.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            await asyncio.sleep(0.1)

            async with self._lock:
                connections = self._connections.get(endpoint, [])
                for conn in connections:
                    if conn.state == ConnectionState.OPEN and conn.is_idle(0):
                        conn.mark_used()
                        return conn

        raise TimeoutError(
            f"No available connection to {endpoint} within {timeout}s"
        )

    async def _health_check_loop(self, interval: float) -> None:
        """Background health check loop.

        Args:
            interval: Check interval in seconds.
        """
        try:
            while True:
                await asyncio.sleep(interval)

                async with self._lock:
                    endpoints_to_clean = list(self._connections.keys())

                for endpoint in endpoints_to_clean:
                    await self._cleanup_expired_connections(endpoint)
        except asyncio.CancelledError:
            pass
        except Exception:
            # Silently ignore errors in background task
            pass


class ConnectionPoolManager:
    """High-level manager for multiple connection pools."""

    def __init__(
        self,
        max_connections_per_endpoint: int = 10,
        idle_timeout: float = 300.0,
        max_connection_age: float = 3600.0,
    ):
        """Initialize pool manager.

        Args:
            max_connections_per_endpoint: Max connections per endpoint.
            idle_timeout: Idle timeout for connections.
            max_connection_age: Max connection age.
        """
        self.config = {
            "max_connections_per_endpoint": max_connections_per_endpoint,
            "idle_timeout": idle_timeout,
            "max_connection_age": max_connection_age,
        }
        self._managers: Dict[str, ConnectionManager] = {}
        self._lock = asyncio.Lock()

    async def get_manager(self, pool_name: str = "default") -> ConnectionManager:
        """Get or create a connection manager.

        Args:
            pool_name: Name of the pool.

        Returns:
            ConnectionManager instance.
        """
        async with self._lock:
            if pool_name not in self._managers:
                self._managers[pool_name] = ConnectionManager(**self.config)
            return self._managers[pool_name]

    async def close_all(self) -> None:
        """Close all managers and their connections."""
        async with self._lock:
            for manager in self._managers.values():
                await manager.stop_health_check()
                await manager.close_all()
            self._managers.clear()
