"""Unit tests for RPC protocol module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from mARCH.networking.rpc import (
    RpcMessage,
    RpcError,
    RpcParseError,
    RpcInvalidRequest,
    RpcMethodNotFound,
    RpcInvalidParams,
    RpcInternalError,
    RpcRegistry,
    RpcServer,
    RpcClient,
)
from mARCH.networking.transport import Transport
from mARCH.networking.payload import PayloadSerializer


class TestRpcMessage:
    """Tests for RpcMessage class."""

    def test_create_request(self):
        """Test creating a request message."""
        msg = RpcMessage.create_request("test_method", {"key": "value"})
        assert msg.method == "test_method"
        assert msg.params == {"key": "value"}
        assert msg.id is not None
        assert msg.is_request()
        assert not msg.is_notification()

    def test_create_notification(self):
        """Test creating a notification."""
        msg = RpcMessage.create_notification("test_method", {"key": "value"})
        assert msg.method == "test_method"
        assert msg.id is None
        assert msg.is_request()
        assert msg.is_notification()

    def test_create_response(self):
        """Test creating a response."""
        msg = RpcMessage.create_response("req-123", {"result": "success"})
        assert msg.id == "req-123"
        assert msg.result == {"result": "success"}
        assert msg.is_response()

    def test_create_error_response(self):
        """Test creating error response."""
        error = RpcInvalidRequest()
        msg = RpcMessage.create_error_response("req-123", error)
        assert msg.id == "req-123"
        assert msg.error is not None
        assert msg.error["code"] == -32600

    def test_to_dict(self):
        """Test converting message to dict."""
        msg = RpcMessage.create_request("test", {"a": 1})
        data = msg.to_dict()
        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "test"
        assert data["params"] == {"a": 1}
        assert "id" in data

    def test_from_dict(self):
        """Test parsing message from dict."""
        data = {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"a": 1},
            "id": "req-123",
        }
        msg = RpcMessage.from_dict(data)
        assert msg.method == "test"
        assert msg.params == {"a": 1}
        assert msg.id == "req-123"

    def test_from_dict_invalid(self):
        """Test parsing invalid message."""
        with pytest.raises(RpcInvalidRequest):
            RpcMessage.from_dict("not a dict")

    def test_from_dict_wrong_version(self):
        """Test parsing message with wrong version."""
        with pytest.raises(RpcInvalidRequest):
            RpcMessage.from_dict({"jsonrpc": "1.0"})


class TestRpcError:
    """Tests for RPC error classes."""

    def test_rpc_error(self):
        """Test RpcError exception."""
        error = RpcError(999, "Test error", {"data": "value"})
        assert error.code == 999
        assert error.message == "Test error"
        assert error.data == {"data": "value"}

    def test_parse_error(self):
        """Test parse error."""
        error = RpcParseError()
        assert error.code == -32700
        assert "Parse error" in error.message

    def test_invalid_request_error(self):
        """Test invalid request error."""
        error = RpcInvalidRequest()
        assert error.code == -32600

    def test_method_not_found_error(self):
        """Test method not found error."""
        error = RpcMethodNotFound("unknown_method")
        assert error.code == -32601
        assert "unknown_method" in error.message

    def test_invalid_params_error(self):
        """Test invalid params error."""
        error = RpcInvalidParams()
        assert error.code == -32602

    def test_internal_error(self):
        """Test internal error."""
        error = RpcInternalError()
        assert error.code == -32603


class TestRpcRegistry:
    """Tests for RpcRegistry."""

    def test_register_method(self):
        """Test registering a method."""
        registry = RpcRegistry()

        def test_handler():
            return "result"

        registry.register("test_method", test_handler)
        assert registry.get("test_method") is test_handler

    def test_unregister_method(self):
        """Test unregistering a method."""
        registry = RpcRegistry()
        registry.register("test", lambda: "result")
        registry.unregister("test")
        assert registry.get("test") is None

    def test_list_methods(self):
        """Test listing registered methods."""
        registry = RpcRegistry()
        registry.register("method1", lambda: "result")
        registry.register("method2", lambda: "result")
        methods = registry.list_methods()
        assert "method1" in methods
        assert "method2" in methods
        assert len(methods) >= 2


class TestRpcServer:
    """Tests for RpcServer."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test server initialization."""
        transport = AsyncMock(spec=Transport)
        server = RpcServer(transport)
        assert server.transport is transport
        assert isinstance(server.registry, RpcRegistry)

    @pytest.mark.asyncio
    async def test_register_method(self):
        """Test registering method with server."""
        transport = AsyncMock(spec=Transport)
        server = RpcServer(transport)

        def handler():
            return "success"

        server.registry.register("test_method", handler)
        assert server.registry.get("test_method") is handler

    @pytest.mark.asyncio
    async def test_call_handler_sync(self):
        """Test calling sync handler."""
        transport = AsyncMock(spec=Transport)
        server = RpcServer(transport)

        def handler():
            return "success"

        result = await server._call_handler(handler)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_call_handler_async(self):
        """Test calling async handler."""
        transport = AsyncMock(spec=Transport)
        server = RpcServer(transport)

        async def handler():
            return "success"

        result = await server._call_handler(handler)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_call_handler_with_args(self):
        """Test calling handler with arguments."""
        transport = AsyncMock(spec=Transport)
        server = RpcServer(transport)

        def handler(a, b, c=None):
            return a + b + (c or 0)

        result = await server._call_handler(handler, 1, 2, c=3)
        assert result == 6


class TestRpcClient:
    """Tests for RpcClient."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test client initialization."""
        transport = AsyncMock(spec=Transport)
        client = RpcClient(transport)
        assert client.transport is transport
        assert isinstance(client.serializer, PayloadSerializer)

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connect and disconnect."""
        transport = AsyncMock(spec=Transport)
        transport.receive = AsyncMock(side_effect=asyncio.TimeoutError)
        client = RpcClient(transport)

        await client.connect()
        assert client._receive_task is not None

        await client.disconnect()
        assert client._receive_task is None

    @pytest.mark.asyncio
    async def test_notify(self):
        """Test sending notification."""
        transport = AsyncMock(spec=Transport)
        client = RpcClient(transport)

        await client.notify("test_method", {"key": "value"})
        transport.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_loop_timeout(self):
        """Test receive loop handles timeouts."""
        transport = AsyncMock(spec=Transport)
        transport.receive = AsyncMock(side_effect=asyncio.TimeoutError)

        client = RpcClient(transport)
        task = asyncio.create_task(client._receive_loop())

        # Let it run briefly
        await asyncio.sleep(0.05)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass


class TestRpcIntegration:
    """Integration tests for RPC."""

    def test_message_serialization(self):
        """Test message serialization and deserialization."""
        msg = RpcMessage.create_request("test", {"a": 1}, request_id="123")
        serializer = PayloadSerializer()

        # Serialize
        data = serializer.serialize(msg.to_dict())

        # Deserialize
        decoded_dict = serializer.deserialize(data)
        decoded_msg = RpcMessage.from_dict(decoded_dict)

        assert decoded_msg.method == "test"
        assert decoded_msg.params == {"a": 1}
        assert decoded_msg.id == "123"

    def test_error_response_serialization(self):
        """Test error response serialization."""
        error = RpcMethodNotFound("unknown")
        msg = RpcMessage.create_error_response("req-1", error)
        serializer = PayloadSerializer()

        data = serializer.serialize(msg.to_dict())
        decoded_dict = serializer.deserialize(data)
        decoded_msg = RpcMessage.from_dict(decoded_dict)

        assert decoded_msg.error is not None
        assert decoded_msg.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_registry_multiple_methods(self):
        """Test registry with multiple methods."""
        registry = RpcRegistry()

        async def async_handler(x):
            return x * 2

        def sync_handler(x):
            return x + 1

        registry.register("async_method", async_handler)
        registry.register("sync_method", sync_handler)

        methods = registry.list_methods()
        assert len(methods) == 2

    def test_message_with_list_params(self):
        """Test message with list parameters."""
        msg = RpcMessage.create_request("add", [1, 2, 3])
        assert msg.params == [1, 2, 3]
        assert msg.is_request()

    def test_message_without_params(self):
        """Test message without parameters."""
        msg = RpcMessage.create_request("test_no_params")
        assert msg.params is None
        assert msg.is_request()
