"""Unit tests for connection management module."""

import pytest
import time
import asyncio

from mARCH.networking.connection import (
    Connection,
    ConnectionState,
    ConnectionManager,
    ConnectionPoolManager,
)


class TestConnection:
    """Tests for Connection class."""

    def test_initialization(self):
        """Test connection initialization."""
        conn = Connection("http://localhost:8000")
        assert conn.endpoint == "http://localhost:8000"
        assert conn.state == ConnectionState.CLOSED
        assert conn.connection_id is not None

    def test_custom_id(self):
        """Test custom connection ID."""
        conn = Connection("http://localhost:8000", connection_id="custom-id")
        assert conn.connection_id == "custom-id"

    def test_mark_used(self):
        """Test marking connection as used."""
        conn = Connection("http://localhost:8000")
        old_time = conn.last_used_at
        time.sleep(0.01)
        conn.mark_used()
        assert conn.last_used_at > old_time

    def test_is_idle(self):
        """Test idle detection."""
        conn = Connection("http://localhost:8000")
        assert not conn.is_idle(1.0)  # Fresh connection
        time.sleep(0.1)
        assert conn.is_idle(0.05)  # Past timeout

    def test_get_age(self):
        """Test get connection age."""
        conn = Connection("http://localhost:8000")
        time.sleep(0.05)
        age = conn.get_age()
        assert age >= 0.05

    def test_repr(self):
        """Test string representation."""
        conn = Connection("http://localhost:8000")
        repr_str = repr(conn)
        assert "localhost:8000" in repr_str
        assert "CLOSED" in repr_str


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test manager initialization."""
        manager = ConnectionManager()
        assert manager.max_connections_per_endpoint == 10
        assert manager.idle_timeout == 300.0

    @pytest.mark.asyncio
    async def test_acquire_new_connection(self):
        """Test acquiring a new connection."""
        manager = ConnectionManager()
        conn = await manager.acquire("http://localhost:8000")
        assert conn.endpoint == "http://localhost:8000"
        assert conn.state == ConnectionState.OPEN
        await manager.close_all()

    @pytest.mark.asyncio
    async def test_acquire_reuses_idle_connection(self):
        """Test reusing idle connections."""
        manager = ConnectionManager(idle_timeout=10.0)
        endpoint = "http://localhost:8000"

        conn1 = await manager.acquire(endpoint)
        conn1_id = id(conn1)
        await manager.release(conn1)

        conn2 = await manager.acquire(endpoint)
        # Should reuse same connection
        assert id(conn2) == conn1_id
        await manager.close_all()

    @pytest.mark.asyncio
    async def test_max_connections_limit(self):
        """Test maximum connections per endpoint."""
        manager = ConnectionManager(max_connections_per_endpoint=2)
        endpoint = "http://localhost:8000"

        conn1 = await manager.acquire(endpoint)
        conn2 = await manager.acquire(endpoint)

        # Third acquire should wait and timeout
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(
                manager.acquire(endpoint),
                timeout=0.2
            )

        await manager.close_all()

    @pytest.mark.asyncio
    async def test_release_connection(self):
        """Test releasing connection."""
        manager = ConnectionManager()
        endpoint = "http://localhost:8000"

        conn = await manager.acquire(endpoint)
        await manager.release(conn)
        # Connection should still exist in pool
        stats = await manager.get_stats()
        assert stats["total_connections"] == 1

        await manager.close_all()

    @pytest.mark.asyncio
    async def test_close_connection(self):
        """Test closing a connection."""
        manager = ConnectionManager()
        endpoint = "http://localhost:8000"

        conn = await manager.acquire(endpoint)
        await manager.close(conn)
        assert conn.state == ConnectionState.CLOSED

        await manager.close_all()

    @pytest.mark.asyncio
    async def test_close_endpoint(self):
        """Test closing all connections to endpoint."""
        manager = ConnectionManager()
        endpoint = "http://localhost:8000"

        conn1 = await manager.acquire(endpoint)
        conn2 = await manager.acquire(endpoint)

        await manager.close_endpoint(endpoint)
        assert conn1.state == ConnectionState.CLOSED
        assert conn2.state == ConnectionState.CLOSED

    @pytest.mark.asyncio
    async def test_close_all(self):
        """Test closing all connections."""
        manager = ConnectionManager()

        conn1 = await manager.acquire("http://localhost:8000")
        conn2 = await manager.acquire("http://localhost:9000")

        await manager.close_all()
        assert conn1.state == ConnectionState.CLOSED
        assert conn2.state == ConnectionState.CLOSED

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting pool statistics."""
        manager = ConnectionManager()

        conn1 = await manager.acquire("http://localhost:8000")
        conn2 = await manager.acquire("http://localhost:8000")
        conn3 = await manager.acquire("http://localhost:9000")

        stats = await manager.get_stats()
        assert stats["total_connections"] == 3
        assert stats["open_connections"] == 3
        assert stats["endpoints"] == 2

        await manager.close_all()

    @pytest.mark.asyncio
    async def test_cleanup_expired_connections(self):
        """Test cleanup of expired connections."""
        manager = ConnectionManager(idle_timeout=0.05, max_connection_age=10.0)
        endpoint = "http://localhost:8000"

        conn = await manager.acquire(endpoint)
        stats = await manager.get_stats()
        assert stats["total_connections"] == 1

        # Wait for connection to become idle
        await asyncio.sleep(0.1)

        # Cleanup should remove it
        await manager._cleanup_expired_connections(endpoint)
        stats = await manager.get_stats()
        assert stats["total_connections"] == 0

    @pytest.mark.asyncio
    async def test_health_check_loop(self):
        """Test health check loop."""
        manager = ConnectionManager(idle_timeout=0.05)
        endpoint = "http://localhost:8000"

        conn = await manager.acquire(endpoint)
        stats = await manager.get_stats()
        assert stats["total_connections"] == 1

        await manager.start_health_check(interval=0.05)
        await asyncio.sleep(0.15)
        await manager.stop_health_check()

        # Health check should have cleaned up idle connection
        stats = await manager.get_stats()
        assert stats["total_connections"] == 0


class TestConnectionPoolManager:
    """Tests for ConnectionPoolManager class."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test pool manager initialization."""
        manager = ConnectionPoolManager()
        assert manager.config["max_connections_per_endpoint"] == 10

    @pytest.mark.asyncio
    async def test_get_manager(self):
        """Test getting connection manager."""
        pool_manager = ConnectionPoolManager()
        manager1 = await pool_manager.get_manager("pool1")
        manager2 = await pool_manager.get_manager("pool1")
        # Should return same instance
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_multiple_pools(self):
        """Test multiple independent pools."""
        pool_manager = ConnectionPoolManager()
        manager1 = await pool_manager.get_manager("pool1")
        manager2 = await pool_manager.get_manager("pool2")
        assert manager1 is not manager2

    @pytest.mark.asyncio
    async def test_close_all(self):
        """Test closing all managers."""
        pool_manager = ConnectionPoolManager()
        manager1 = await pool_manager.get_manager("pool1")
        conn = await manager1.acquire("http://localhost:8000")

        await pool_manager.close_all()
        assert conn.state == ConnectionState.CLOSED
