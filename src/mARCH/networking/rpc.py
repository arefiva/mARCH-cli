"""JSON-RPC 2.0 protocol implementation.

Provides RPC message framing, server, client, and request/response routing.
"""

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel

from mARCH.networking.payload import PayloadSerializer, get_serializer
from mARCH.networking.transport import Transport


class RpcError(Exception):
    """Base exception for RPC errors."""

    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        """Initialize RPC error.

        Args:
            code: Error code.
            message: Error message.
            data: Optional error data.
        """
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"RPC Error {code}: {message}")


class RpcParseError(RpcError):
    """Parse error."""

    def __init__(self, data: Optional[Any] = None):
        super().__init__(-32700, "Parse error", data)


class RpcInvalidRequest(RpcError):
    """Invalid request error."""

    def __init__(self, data: Optional[Any] = None):
        super().__init__(-32600, "Invalid Request", data)


class RpcMethodNotFound(RpcError):
    """Method not found error."""

    def __init__(self, method: str):
        super().__init__(-32601, f"Method not found: {method}")


class RpcInvalidParams(RpcError):
    """Invalid parameters error."""

    def __init__(self, data: Optional[Any] = None):
        super().__init__(-32602, "Invalid params", data)


class RpcInternalError(RpcError):
    """Internal error."""

    def __init__(self, data: Optional[Any] = None):
        super().__init__(-32603, "Internal error", data)


@dataclass
class RpcMessage:
    """JSON-RPC 2.0 message.

    Attributes:
        method: Method name.
        params: Method parameters (dict or list).
        id: Request ID (None for notifications).
        result: Result (for responses).
        error: Error object (for error responses).
    """

    jsonrpc: str = "2.0"
    method: Optional[str] = None
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    id: Optional[Union[int, str]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def is_request(self) -> bool:
        """Check if message is a request."""
        return self.method is not None and self.error is None and self.result is None

    def is_notification(self) -> bool:
        """Check if message is a notification."""
        return self.is_request() and self.id is None

    def is_response(self) -> bool:
        """Check if message is a response."""
        return self.result is not None or self.error is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation.
        """
        msg = {"jsonrpc": self.jsonrpc}

        if self.method:
            msg["method"] = self.method
        if self.params is not None:
            msg["params"] = self.params
        if self.id is not None:
            msg["id"] = self.id
        if self.result is not None:
            msg["result"] = self.result
        if self.error is not None:
            msg["error"] = self.error

        return msg

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RpcMessage":
        """Create from dictionary.

        Args:
            data: Dictionary to parse.

        Returns:
            RpcMessage instance.

        Raises:
            RpcInvalidRequest: If message is invalid.
        """
        if not isinstance(data, dict):
            raise RpcInvalidRequest("Message must be a dict")

        if data.get("jsonrpc") != "2.0":
            raise RpcInvalidRequest("Invalid jsonrpc version")

        return RpcMessage(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data.get("method"),
            params=data.get("params"),
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error"),
        )

    @staticmethod
    def create_request(
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
        request_id: Optional[Union[int, str]] = None,
    ) -> "RpcMessage":
        """Create a request message.

        Args:
            method: Method name.
            params: Optional parameters.
            request_id: Optional request ID. Generated if not provided.

        Returns:
            RpcMessage instance.
        """
        msg_id = request_id or str(uuid.uuid4())
        return RpcMessage(method=method, params=params, id=msg_id)

    @staticmethod
    def create_notification(
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
    ) -> "RpcMessage":
        """Create a notification message (no response expected).

        Args:
            method: Method name.
            params: Optional parameters.

        Returns:
            RpcMessage instance.
        """
        return RpcMessage(method=method, params=params, id=None)

    @staticmethod
    def create_response(
        request_id: Union[int, str],
        result: Any,
    ) -> "RpcMessage":
        """Create a response message.

        Args:
            request_id: ID of request being responded to.
            result: Result data.

        Returns:
            RpcMessage instance.
        """
        return RpcMessage(id=request_id, result=result)

    @staticmethod
    def create_error_response(
        request_id: Optional[Union[int, str]],
        error: RpcError,
    ) -> "RpcMessage":
        """Create an error response message.

        Args:
            request_id: ID of request being responded to.
            error: RpcError instance.

        Returns:
            RpcMessage instance.
        """
        error_obj = {
            "code": error.code,
            "message": error.message,
        }
        if error.data is not None:
            error_obj["data"] = error.data

        return RpcMessage(id=request_id, error=error_obj)


class RpcRegistry:
    """Registry for RPC method handlers."""

    def __init__(self):
        """Initialize registry."""
        self._methods: Dict[str, Callable[..., Any]] = {}

    def register(self, method_name: str, handler: Callable[..., Any]) -> None:
        """Register a method handler.

        Args:
            method_name: Name of the method.
            handler: Callable handler for the method.
        """
        self._methods[method_name] = handler

    def unregister(self, method_name: str) -> None:
        """Unregister a method handler.

        Args:
            method_name: Name of the method.
        """
        self._methods.pop(method_name, None)

    def get(self, method_name: str) -> Optional[Callable[..., Any]]:
        """Get a method handler.

        Args:
            method_name: Name of the method.

        Returns:
            Handler callable or None if not found.
        """
        return self._methods.get(method_name)

    def list_methods(self) -> List[str]:
        """List all registered methods.

        Returns:
            List of method names.
        """
        return list(self._methods.keys())


class RpcServer:
    """RPC server for handling incoming requests."""

    def __init__(
        self,
        transport: Transport,
        registry: Optional[RpcRegistry] = None,
        serializer: Optional[PayloadSerializer] = None,
    ):
        """Initialize RPC server.

        Args:
            transport: Transport for communication.
            registry: Method registry. Creates new if not provided.
            serializer: Payload serializer.
        """
        self.transport = transport
        self.registry = registry or RpcRegistry()
        self.serializer = serializer or get_serializer()
        self._running = False

    async def start(self) -> None:
        """Start the RPC server."""
        await self.transport.connect()
        self._running = True
        await self._receive_loop()

    async def stop(self) -> None:
        """Stop the RPC server."""
        self._running = False
        await self.transport.disconnect()

    async def _receive_loop(self) -> None:
        """Main receive loop for processing requests."""
        while self._running:
            try:
                data = await self.transport.receive(timeout=1.0)
                await self._handle_message(data)
            except TimeoutError:
                continue
            except Exception:
                break

    async def _handle_message(self, data: bytes) -> None:
        """Handle incoming message.

        Args:
            data: Raw message bytes.
        """
        try:
            msg_dict = self.serializer.deserialize(data)
            msg = RpcMessage.from_dict(msg_dict)

            if not msg.is_request():
                return

            handler = self.registry.get(msg.method)
            if not handler:
                error = RpcMethodNotFound(msg.method)
                response = RpcMessage.create_error_response(msg.id, error)
            else:
                try:
                    if isinstance(msg.params, dict):
                        result = await self._call_handler(handler, **msg.params)
                    elif isinstance(msg.params, list):
                        result = await self._call_handler(handler, *msg.params)
                    else:
                        result = await self._call_handler(handler)

                    response = RpcMessage.create_response(msg.id, result)
                except RpcError as e:
                    response = RpcMessage.create_error_response(msg.id, e)
                except TypeError as e:
                    error = RpcInvalidParams(str(e))
                    response = RpcMessage.create_error_response(msg.id, error)
                except Exception as e:
                    error = RpcInternalError(str(e))
                    response = RpcMessage.create_error_response(msg.id, error)

            # Only send response for requests (not notifications)
            if msg.id is not None:
                response_data = self.serializer.serialize(response.to_dict())
                await self.transport.send(response_data)

        except RpcError as e:
            error_response = RpcMessage.create_error_response(None, e)
            response_data = self.serializer.serialize(error_response.to_dict())
            await self.transport.send(response_data)

    async def _call_handler(self, handler: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Call a handler function (sync or async).

        Args:
            handler: Handler function.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Handler result.
        """
        import asyncio
        import inspect

        if asyncio.iscoroutinefunction(handler):
            return await handler(*args, **kwargs)
        else:
            return handler(*args, **kwargs)


class RpcClient:
    """RPC client for making requests."""

    def __init__(
        self,
        transport: Transport,
        serializer: Optional[PayloadSerializer] = None,
        timeout: float = 30.0,
    ):
        """Initialize RPC client.

        Args:
            transport: Transport for communication.
            serializer: Payload serializer.
            timeout: Request timeout in seconds.
        """
        self.transport = transport
        self.serializer = serializer or get_serializer()
        self.timeout = timeout
        self._pending_requests: Dict[str, asyncio.Future[Any]] = {}
        self._receive_task: Optional[asyncio.Task[None]] = None

    async def connect(self) -> None:
        """Connect the RPC client."""
        await self.transport.connect()
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def disconnect(self) -> None:
        """Disconnect the RPC client."""
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        await self.transport.disconnect()

    async def call(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Make an RPC call and wait for response.

        Args:
            method: Method name to call.
            params: Optional parameters.
            timeout: Optional timeout (uses default if not provided).

        Returns:
            Result from the RPC call.

        Raises:
            RpcError: If RPC error returned.
            TimeoutError: If timeout exceeded.
        """
        msg = RpcMessage.create_request(method, params)
        request_id = str(msg.id)

        # Create future for response
        future: asyncio.Future[Any] = asyncio.Future()
        self._pending_requests[request_id] = future

        try:
            # Send request
            request_data = self.serializer.serialize(msg.to_dict())
            await self.transport.send(request_data)

            # Wait for response
            actual_timeout = timeout or self.timeout
            return await asyncio.wait_for(future, timeout=actual_timeout)
        finally:
            self._pending_requests.pop(request_id, None)

    async def notify(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
    ) -> None:
        """Send a notification (no response expected).

        Args:
            method: Method name to call.
            params: Optional parameters.
        """
        msg = RpcMessage.create_notification(method, params)
        request_data = self.serializer.serialize(msg.to_dict())
        await self.transport.send(request_data)

    async def _receive_loop(self) -> None:
        """Main receive loop for responses."""
        while True:
            try:
                data = await self.transport.receive(timeout=1.0)
                msg_dict = self.serializer.deserialize(data)
                msg = RpcMessage.from_dict(msg_dict)

                if msg.is_response() and msg.id:
                    request_id = str(msg.id)
                    future = self._pending_requests.get(request_id)

                    if future and not future.done():
                        if msg.error:
                            error_code = msg.error.get("code", -1)
                            error_msg = msg.error.get("message", "Unknown error")
                            error = RpcError(error_code, error_msg)
                            future.set_exception(error)
                        else:
                            future.set_result(msg.result)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                break
