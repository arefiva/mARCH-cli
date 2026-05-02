"""Unit tests for HTTP client module."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from mARCH.networking.http_client import (
    HttpClient,
    WebSocketClient,
    ConnectionPool,
)


class TestHttpClient:
    """Tests for HTTP client."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connect and disconnect."""
        client = HttpClient()
        assert client._client is None

        await client.connect()
        assert client._client is not None

        await client.disconnect()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager."""
        async with HttpClient() as client:
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_ensure_connected(self):
        """Test automatic connection on request."""
        client = HttpClient()
        assert client._client is None

        # Mock the request to avoid actual HTTP call
        with patch.object(client._resilient_client, 'call_async', new_callable=AsyncMock):
            client._resilient_client.call_async.return_value = httpx.Response(200)
            await client._ensure_connected()
            assert client._client is not None

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_default_timeout(self):
        """Test default timeout setting."""
        client = HttpClient(timeout=15.0)
        assert client.timeout == 15.0

    @pytest.mark.asyncio
    async def test_custom_limits(self):
        """Test custom connection limits."""
        limits = httpx.Limits(max_connections=50, max_keepalive_connections=10)
        client = HttpClient(limits=limits)
        assert client.limits == limits


class TestWebSocketClient:
    """Tests for WebSocket client."""

    def test_initialization(self):
        """Test initialization."""
        client = WebSocketClient("ws://localhost:8000")
        assert client.url == "ws://localhost:8000"
        assert client.timeout == 30.0
        assert not client.is_connected

    def test_initialization_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = WebSocketClient("ws://localhost:8000", timeout=15.0)
        assert client.timeout == 15.0

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager initialization."""
        with patch('asyncio.wait_for', new_callable=AsyncMock):
            client = WebSocketClient("ws://localhost:8000")
            # Note: We're not actually testing connect due to websockets dependency
            # This just tests the interface


class TestConnectionPool:
    """Tests for connection pool."""

    def test_initialization(self):
        """Test initialization."""
        pool = ConnectionPool(max_connections=50, max_keepalive=10)
        assert pool.max_connections == 50
        assert pool.max_keepalive == 10

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager."""
        async with ConnectionPool() as pool:
            assert pool._client._client is not None

    @pytest.mark.asyncio
    async def test_client_property(self):
        """Test client property."""
        pool = ConnectionPool()
        client = pool.client
        assert isinstance(client, HttpClient)

    @pytest.mark.asyncio
    async def test_default_settings(self):
        """Test default pool settings."""
        pool = ConnectionPool()
        assert pool.max_connections == 100
        assert pool.max_keepalive == 20
        assert pool.timeout == 30.0


class TestHttpClientIntegration:
    """Integration tests for HTTP client."""

    @pytest.mark.asyncio
    async def test_request_methods_exist(self):
        """Test that all HTTP methods are available."""
        client = HttpClient()
        assert hasattr(client, 'get')
        assert hasattr(client, 'post')
        assert hasattr(client, 'put')
        assert hasattr(client, 'patch')
        assert hasattr(client, 'delete')
        assert hasattr(client, 'request')
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_connection_pool_delegation(self):
        """Test connection pool delegates to client."""
        pool = ConnectionPool()
        await pool.connect()

        # Verify pool can make requests (mocked)
        assert hasattr(pool, 'get')
        assert hasattr(pool, 'post')
        assert hasattr(pool, 'request')

        await pool.disconnect()
