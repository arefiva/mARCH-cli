"""Extension protocol handler for RPC communication."""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class RpcMessage:
    """JSON-RPC 2.0 message."""

    jsonrpc: str = "2.0"
    method: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[dict[str, Any]] = None
    id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RpcMessage":
        """Create from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
            id=data.get("id"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "RpcMessage":
        """Create from JSON string."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            raise


class RpcError:
    """RPC error codes and messages."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR_START = -32099
    SERVER_ERROR_END = -32000

    @staticmethod
    def error_dict(code: int, message: str, data: Optional[Any] = None) -> dict[str, Any]:
        """Create error object."""
        error = {"code": code, "message": message}
        if data:
            error["data"] = data
        return error


class ExtensionProtocolHandler:
    """Handles RPC communication with extensions."""

    DEFAULT_TIMEOUT_SECONDS = 30

    def __init__(self, extension_name: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS):
        """Initialize protocol handler.

        Args:
            extension_name: Name of extension
            timeout_seconds: RPC timeout
        """
        self.extension_name = extension_name
        self.timeout_seconds = timeout_seconds
        self.pending_requests: dict[str, asyncio.Event] = {}
        self.request_results: dict[str, Any] = {}
        self.event_handlers: dict[str, list[Callable]] = {}
        self._id_counter = 0

    def _generate_id(self) -> str:
        """Generate unique message ID."""
        self._id_counter += 1
        return f"{self.extension_name}:{self._id_counter}:{uuid.uuid4()}"

    async def invoke_method(
        self, method: str, params: Optional[dict[str, Any]] = None
    ) -> Any:
        """Invoke a method on the extension.

        Args:
            method: Method name
            params: Method parameters

        Returns:
            Result from extension

        Raises:
            TimeoutError: If request times out
            RuntimeError: If extension returns error
        """
        msg_id = self._generate_id()
        request = RpcMessage(method=method, params=params, id=msg_id)

        # Set up event for waiting on response
        event = asyncio.Event()
        self.pending_requests[msg_id] = event

        try:
            # TODO: Send message to extension
            logger.debug(f"Sending RPC: {request.to_json()}")

            # Wait for response with timeout
            try:
                await asyncio.wait_for(event.wait(), timeout=self.timeout_seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(f"RPC timeout for {method}")

            # Get result
            result = self.request_results.get(msg_id)

            # Check for error
            if isinstance(result, dict) and "error" in result:
                error = result["error"]
                raise RuntimeError(f"RPC error {error.get('code')}: {error.get('message')}")

            return result

        finally:
            # Clean up
            self.pending_requests.pop(msg_id, None)
            self.request_results.pop(msg_id, None)

    def handle_response(self, message: RpcMessage) -> None:
        """Handle RPC response from extension.

        Args:
            message: RPC response message
        """
        if not message.id:
            logger.warning("Received message without ID")
            return

        # Store result
        if message.result is not None:
            self.request_results[message.id] = message.result
        elif message.error:
            self.request_results[message.id] = {"error": message.error}

        # Signal waiting coroutine
        if message.id in self.pending_requests:
            self.pending_requests[message.id].set()

    def handle_event(self, message: RpcMessage) -> None:
        """Handle event from extension.

        Args:
            message: Event message (no ID, method is event type)
        """
        if not message.method:
            logger.warning("Received event without method")
            return

        event_type = message.method
        handlers = self.event_handlers.get(event_type, [])

        logger.debug(f"Handling event {event_type} with {len(handlers)} handlers")

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    # TODO: Schedule async handler
                    pass
                else:
                    handler(message.params)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")

    def subscribe_event(self, event_type: str, handler: Callable) -> None:
        """Subscribe to events.

        Args:
            event_type: Type of event
            handler: Handler function or coroutine
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def unsubscribe_event(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from events.

        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
            except ValueError:
                pass

    def parse_message(self, data: str) -> RpcMessage:
        """Parse incoming message.

        Args:
            data: Raw message data

        Returns:
            Parsed RPC message

        Raises:
            ValueError: If message is invalid
        """
        try:
            msg = RpcMessage.from_json(data)

            # Validate message
            if msg.jsonrpc != "2.0":
                raise ValueError("Invalid JSON-RPC version")

            if not msg.method and not msg.id:
                raise ValueError("Message must have method or id")

            return msg
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
