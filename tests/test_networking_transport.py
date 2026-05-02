"""Unit tests for transport layer module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mARCH.networking.transport import (
    Transport,
    TransportError,
    HttpTransport,
    WebSocketTransport,
    UnixSocketTransport,
    TransportFactory,
)
from mARCH.networking.payload import PayloadSerializer


class TestTransport:
    """Tests for Transport abstract class."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager interface."""
        # Create a concrete implementation for testing
        class TestTransport(Transport):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def send(self, data):
                pass

            async def receive(self, timeout=None):
                return b"test"

            @property
            def is_connected(self):
                return True

        async with TestTransport() as transport:
            assert transport.is_connected


class TestHttpTransport:
    """Tests for HTTP transport."""

    def test_initialization(self):
        """Test HTTP transport initialization."""
        transport = HttpTransport("http://localhost:8000")
        assert transport.endpoint == "http://localhost:8000"
        assert transport.timeout == 30.0
        assert isinstance(transport.serializer, PayloadSerializer)

    def test_initialization_custom_timeout(self):
        """Test custom timeout."""
        transport = HttpTransport("http://localhost:8000", timeout=15.0)
        assert transport.timeout == 15.0

    def test_initialization_custom_serializer(self):
        """Test custom serializer."""
        serializer = PayloadSerializer()
        transport = HttpTransport("http://localhost:8000", serializer=serializer)
        assert transport.serializer is serializer

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connect and disconnect."""
        transport = HttpTransport("http://localhost:8000")
        await transport.connect()
        assert transport.is_connected
        await transport.disconnect()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager."""
        async with HttpTransport("http://localhost:8000") as transport:
            assert transport.is_connected

    @pytest.mark.asyncio
    async def test_send_error(self):
        """Test send error handling."""
        transport = HttpTransport("http://localhost:8000")
        await transport.connect()

        with patch.object(transport._client, 'post', side_effect=Exception("Network error")):
            with pytest.raises(TransportError):
                await transport.send(b"test data")

        await transport.disconnect()

    @pytest.mark.asyncio
    async def test_receive_error(self):
        """Test receive error handling."""
        transport = HttpTransport("http://localhost:8000")
        await transport.connect()

        with patch.object(transport._client, 'get', side_effect=Exception("Network error")):
            with pytest.raises(TransportError):
                await transport.receive()

        await transport.disconnect()


class TestWebSocketTransport:
    """Tests for WebSocket transport."""

    def test_initialization(self):
        """Test WebSocket transport initialization."""
        transport = WebSocketTransport("ws://localhost:8000")
        assert transport.endpoint == "ws://localhost:8000"
        assert transport.timeout == 30.0

    def test_initialization_custom_timeout(self):
        """Test custom timeout."""
        transport = WebSocketTransport("ws://localhost:8000", timeout=15.0)
        assert transport.timeout == 15.0

    @pytest.mark.asyncio
    async def test_initialization_error(self):
        """Test initialization error."""
        transport = WebSocketTransport("ws://invalid")
        with patch.object(transport._client, 'connect', side_effect=Exception("Connection failed")):
            with pytest.raises(TransportError):
                await transport.connect()

    @pytest.mark.asyncio
    async def test_send_error(self):
        """Test send error handling."""
        transport = WebSocketTransport("ws://localhost:8000")
        with patch.object(transport._client, 'send', side_effect=Exception("Send failed")):
            with pytest.raises(TransportError):
                await transport.send(b"test")

    @pytest.mark.asyncio
    async def test_receive_error(self):
        """Test receive error handling."""
        transport = WebSocketTransport("ws://localhost:8000")
        with patch.object(transport._client, 'receive', side_effect=Exception("Receive failed")):
            with pytest.raises(TransportError):
                await transport.receive()

    @pytest.mark.asyncio
    async def test_receive_bytes_conversion(self):
        """Test string to bytes conversion in receive."""
        transport = WebSocketTransport("ws://localhost:8000")
        with patch.object(transport._client, 'receive', new_callable=AsyncMock, return_value="test string"):
            data = await transport.receive()
            assert data == b"test string"

    @pytest.mark.asyncio
    async def test_is_connected(self):
        """Test is_connected property."""
        transport = WebSocketTransport("ws://localhost:8000")
        assert not transport.is_connected


class TestUnixSocketTransport:
    """Tests for Unix socket transport."""

    def test_initialization(self):
        """Test Unix socket transport initialization."""
        transport = UnixSocketTransport("/tmp/test.sock")
        assert transport.socket_path == "/tmp/test.sock"
        assert transport.timeout == 30.0

    def test_initialization_custom_timeout(self):
        """Test custom timeout."""
        transport = UnixSocketTransport("/tmp/test.sock", timeout=15.0)
        assert transport.timeout == 15.0

    @pytest.mark.asyncio
    async def test_send_not_connected(self):
        """Test send when not connected."""
        transport = UnixSocketTransport("/tmp/test.sock")
        with pytest.raises(TransportError, match="not connected"):
            await transport.send(b"test")

    @pytest.mark.asyncio
    async def test_receive_not_connected(self):
        """Test receive when not connected."""
        transport = UnixSocketTransport("/tmp/test.sock")
        with pytest.raises(TransportError, match="not connected"):
            await transport.receive()

    @pytest.mark.asyncio
    async def test_is_connected(self):
        """Test is_connected property."""
        transport = UnixSocketTransport("/tmp/test.sock")
        assert not transport.is_connected


class TestTransportFactory:
    """Tests for TransportFactory."""

    def test_create_http_transport(self):
        """Test creating HTTP transport."""
        transport = TransportFactory.create("http", "http://localhost:8000")
        assert isinstance(transport, HttpTransport)

    def test_create_websocket_transport(self):
        """Test creating WebSocket transport."""
        transport = TransportFactory.create("websocket", "ws://localhost:8000")
        assert isinstance(transport, WebSocketTransport)

    def test_create_unix_transport(self):
        """Test creating Unix socket transport."""
        transport = TransportFactory.create("unix", "/tmp/test.sock")
        assert isinstance(transport, UnixSocketTransport)

    def test_create_unknown_transport(self):
        """Test creating unknown transport type."""
        with pytest.raises(KeyError):
            TransportFactory.create("unknown", "endpoint")

    def test_register_custom_transport(self):
        """Test registering custom transport."""
        class CustomTransport(Transport):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def send(self, data):
                pass

            async def receive(self, timeout=None):
                pass

            @property
            def is_connected(self):
                return False

        TransportFactory.register("custom", CustomTransport)
        transport = TransportFactory.create("custom", "endpoint")
        assert isinstance(transport, CustomTransport)

    def test_create_with_kwargs(self):
        """Test creating transport with kwargs."""
        serializer = PayloadSerializer()
        transport = TransportFactory.create(
            "http",
            "http://localhost:8000",
            timeout=15.0,
            serializer=serializer
        )
        assert transport.timeout == 15.0
        assert transport.serializer is serializer


class TestTransportIntegration:
    """Integration tests for transport layer."""

    @pytest.mark.asyncio
    async def test_transport_serialization(self):
        """Test transport with serialization."""
        transport = HttpTransport("http://localhost:8000")
        await transport.connect()

        data = {"message": "test", "value": 42}
        serialized = transport.serializer.serialize(data)
        assert isinstance(serialized, bytes)

        await transport.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_transports(self):
        """Test managing multiple transport instances."""
        http_transport = HttpTransport("http://localhost:8000")
        ws_transport = WebSocketTransport("ws://localhost:8000")
        unix_transport = UnixSocketTransport("/tmp/test.sock")

        await http_transport.connect()
        assert http_transport.is_connected

        # WebSocket would fail due to no server, so we just check it's created
        assert ws_transport.endpoint == "ws://localhost:8000"
        assert unix_transport.socket_path == "/tmp/test.sock"

        await http_transport.disconnect()
