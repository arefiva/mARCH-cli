"""Tests for extension protocol handler."""

import asyncio
import json

import pytest

from mARCH.extension.protocol import ExtensionProtocolHandler, RpcMessage, RpcError


class TestRpcMessage:
    """Test RPC message handling."""

    def test_message_creation_request(self):
        """Test creating a request message."""
        msg = RpcMessage(method="test", params={"key": "value"}, id="1")
        assert msg.method == "test"
        assert msg.params == {"key": "value"}
        assert msg.id == "1"

    def test_message_creation_response(self):
        """Test creating a response message."""
        msg = RpcMessage(result=42, id="1")
        assert msg.result == 42
        assert msg.id == "1"
        assert msg.method is None

    def test_message_to_json(self):
        """Test converting message to JSON."""
        msg = RpcMessage(method="test", params={"x": 1}, id="msg-1")
        json_str = msg.to_json()

        data = json.loads(json_str)
        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "test"
        assert data["id"] == "msg-1"

    def test_message_from_json(self):
        """Test parsing message from JSON."""
        json_str = '{"jsonrpc": "2.0", "method": "test", "params": {"x": 1}, "id": "1"}'
        msg = RpcMessage.from_json(json_str)

        assert msg.method == "test"
        assert msg.params == {"x": 1}
        assert msg.id == "1"

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "jsonrpc": "2.0",
            "method": "calculate",
            "params": {"a": 10, "b": 20},
            "id": "calc-1",
        }
        msg = RpcMessage.from_dict(data)

        assert msg.method == "calculate"
        assert msg.params == {"a": 10, "b": 20}

    def test_message_to_dict_excludes_none(self):
        """Test that None values are excluded."""
        msg = RpcMessage(method="test", id="1")
        data = msg.to_dict()

        assert "result" not in data
        assert "error" not in data
        assert "params" not in data

    def test_message_invalid_json(self):
        """Test parsing invalid JSON."""
        with pytest.raises(ValueError):
            RpcMessage.from_json("{invalid json}")


class TestRpcError:
    """Test RPC error handling."""

    def test_parse_error(self):
        """Test parse error."""
        error = RpcError.error_dict(
            RpcError.PARSE_ERROR, "Invalid JSON was received"
        )
        assert error["code"] == -32700

    def test_method_not_found(self):
        """Test method not found error."""
        error = RpcError.error_dict(
            RpcError.METHOD_NOT_FOUND, "The method does not exist"
        )
        assert error["code"] == -32601

    def test_error_with_data(self):
        """Test error with additional data."""
        error = RpcError.error_dict(
            RpcError.INTERNAL_ERROR, "Server error", data={"details": "out of memory"}
        )
        assert error["data"]["details"] == "out of memory"


class TestExtensionProtocolHandler:
    """Test protocol handler."""

    @pytest.fixture
    def handler(self):
        """Create a protocol handler."""
        return ExtensionProtocolHandler("test-ext")

    def test_handler_creation(self, handler):
        """Test creating handler."""
        assert handler.extension_name == "test-ext"
        assert handler.timeout_seconds == 30

    def test_generate_id(self, handler):
        """Test ID generation."""
        id1 = handler._generate_id()
        id2 = handler._generate_id()

        assert "test-ext" in id1
        assert "test-ext" in id2
        assert id1 != id2  # Should be unique

    def test_parse_message_valid_request(self, handler):
        """Test parsing valid request."""
        json_str = '{"jsonrpc": "2.0", "method": "test", "id": "1"}'
        msg = handler.parse_message(json_str)

        assert msg.method == "test"
        assert msg.jsonrpc == "2.0"

    def test_parse_message_invalid_json(self, handler):
        """Test parsing invalid JSON."""
        with pytest.raises(ValueError):
            handler.parse_message("{invalid}")

    def test_handle_response(self, handler):
        """Test handling response."""
        msg_id = "test-msg-1"
        handler.pending_requests[msg_id] = asyncio.Event()

        response = RpcMessage(result=42, id=msg_id)
        handler.handle_response(response)

        assert handler.request_results[msg_id] == 42
        assert handler.pending_requests[msg_id].is_set()

    def test_handle_response_with_error(self, handler):
        """Test handling error response."""
        msg_id = "error-msg-1"
        handler.pending_requests[msg_id] = asyncio.Event()

        error = RpcError.error_dict(-32600, "Invalid request")
        response = RpcMessage(error=error, id=msg_id)
        handler.handle_response(response)

        assert "error" in handler.request_results[msg_id]
        assert handler.request_results[msg_id]["error"]["code"] == -32600

    def test_subscribe_event(self, handler):
        """Test subscribing to events."""
        called = []

        def on_event(data):
            called.append(data)

        handler.subscribe_event("test_event", on_event)
        assert "test_event" in handler.event_handlers

    def test_unsubscribe_event(self, handler):
        """Test unsubscribing from events."""
        called = []

        def on_event(data):
            called.append(data)

        handler.subscribe_event("test_event", on_event)
        handler.unsubscribe_event("test_event", on_event)

        assert "test_event" not in handler.event_handlers or len(handler.event_handlers["test_event"]) == 0

    def test_handle_event(self, handler):
        """Test handling events."""
        called = []

        def on_event(data):
            called.append(data)

        handler.subscribe_event("my_event", on_event)

        event_msg = RpcMessage(method="my_event", params={"value": 123})
        handler.handle_event(event_msg)

        assert len(called) == 1
        assert called[0] == {"value": 123}
