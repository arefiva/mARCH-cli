"""Abstract message transport layer.

Provides pluggable transport implementations for different protocols
(HTTP, WebSocket, Unix sockets, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from mARCH.networking.http_client import HttpClient, WebSocketClient
from mARCH.networking.payload import PayloadSerializer, get_serializer


class Transport(ABC):
    """Abstract base class for message transport."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the transport endpoint."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the transport endpoint."""
        pass

    @abstractmethod
    async def send(self, data: bytes) -> None:
        """Send data through the transport.

        Args:
            data: Raw bytes to send.

        Raises:
            TransportError: If send fails.
        """
        pass

    @abstractmethod
    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """Receive data from the transport.

        Args:
            timeout: Optional receive timeout in seconds.

        Returns:
            Raw bytes received.

        Raises:
            TransportError: If receive fails.
            TimeoutError: If timeout exceeded.
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected.

        Returns:
            True if connected, False otherwise.
        """
        pass

    async def __aenter__(self) -> "Transport":
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        await self.disconnect()


class TransportError(Exception):
    """Exception raised for transport errors."""

    pass


class HttpTransport(Transport):
    """HTTP-based message transport.

    Sends messages via HTTP POST requests and polls for responses.
    """

    def __init__(
        self,
        endpoint: str,
        timeout: float = 30.0,
        serializer: Optional[PayloadSerializer] = None,
    ):
        """Initialize HTTP transport.

        Args:
            endpoint: HTTP endpoint URL.
            timeout: Request timeout in seconds.
            serializer: Payload serializer. Defaults to global serializer.
        """
        self.endpoint = endpoint
        self.timeout = timeout
        self.serializer = serializer or get_serializer()
        self._client = HttpClient(timeout=timeout)
        self._response_queue: Dict[str, bytes] = {}

    async def connect(self) -> None:
        """Initialize HTTP client."""
        await self._client.connect()

    async def disconnect(self) -> None:
        """Close HTTP client."""
        await self._client.disconnect()

    async def send(self, data: bytes) -> None:
        """Send data via HTTP POST.

        Args:
            data: Raw bytes to send.

        Raises:
            TransportError: If request fails.
        """
        try:
            response = await self._client.post(
                self.endpoint,
                content=data,
                headers={"Content-Type": "application/octet-stream"},
            )
            response.raise_for_status()
        except Exception as e:
            raise TransportError(f"HTTP transport send failed: {e}") from e

    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """Receive data via HTTP polling.

        Args:
            timeout: Receive timeout in seconds.

        Returns:
            Raw bytes received.

        Raises:
            TransportError: If receive fails.
            TimeoutError: If timeout exceeded.
        """
        try:
            response = await self._client.get(
                f"{self.endpoint}?wait",
                timeout=timeout or self.timeout,
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise TransportError(f"HTTP transport receive failed: {e}") from e

    @property
    def is_connected(self) -> bool:
        """Check if HTTP client is connected.

        Returns:
            True if connected, False otherwise.
        """
        return self._client._client is not None


class WebSocketTransport(Transport):
    """WebSocket-based message transport."""

    def __init__(
        self,
        endpoint: str,
        timeout: float = 30.0,
        serializer: Optional[PayloadSerializer] = None,
    ):
        """Initialize WebSocket transport.

        Args:
            endpoint: WebSocket endpoint URL.
            timeout: Connection timeout in seconds.
            serializer: Payload serializer. Defaults to global serializer.
        """
        self.endpoint = endpoint
        self.timeout = timeout
        self.serializer = serializer or get_serializer()
        self._client = WebSocketClient(endpoint, timeout=timeout)

    async def connect(self) -> None:
        """Connect to WebSocket server.

        Raises:
            TransportError: If connection fails.
        """
        try:
            await self._client.connect()
        except Exception as e:
            raise TransportError(f"WebSocket connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        await self._client.disconnect()

    async def send(self, data: bytes) -> None:
        """Send data via WebSocket.

        Args:
            data: Raw bytes to send.

        Raises:
            TransportError: If send fails.
        """
        try:
            await self._client.send(data)
        except Exception as e:
            raise TransportError(f"WebSocket send failed: {e}") from e

    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """Receive data from WebSocket.

        Args:
            timeout: Receive timeout in seconds.

        Returns:
            Raw bytes received.

        Raises:
            TransportError: If receive fails.
            TimeoutError: If timeout exceeded.
        """
        try:
            data = await self._client.receive()
            if isinstance(data, str):
                data = data.encode("utf-8")
            return data
        except Exception as e:
            raise TransportError(f"WebSocket receive failed: {e}") from e

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected.

        Returns:
            True if connected, False otherwise.
        """
        return self._client.is_connected


class UnixSocketTransport(Transport):
    """Unix socket transport for IPC.

    Used for inter-process communication on Unix-like systems.
    """

    def __init__(
        self,
        socket_path: str,
        timeout: float = 30.0,
        serializer: Optional[PayloadSerializer] = None,
    ):
        """Initialize Unix socket transport.

        Args:
            socket_path: Path to Unix socket.
            timeout: Operation timeout in seconds.
            serializer: Payload serializer.
        """
        self.socket_path = socket_path
        self.timeout = timeout
        self.serializer = serializer or get_serializer()
        self._reader: Any = None
        self._writer: Any = None

    async def connect(self) -> None:
        """Connect to Unix socket.

        Raises:
            TransportError: If connection fails.
        """
        import asyncio

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self.socket_path),
                timeout=self.timeout,
            )
        except Exception as e:
            raise TransportError(f"Unix socket connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Unix socket."""
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None

    async def send(self, data: bytes) -> None:
        """Send data via Unix socket.

        Args:
            data: Raw bytes to send.

        Raises:
            TransportError: If send fails.
        """
        if not self._writer:
            raise TransportError("Unix socket not connected")

        try:
            import asyncio

            # Send length prefix + data
            length = len(data).to_bytes(4, byteorder="big")
            self._writer.write(length + data)
            await asyncio.wait_for(self._writer.drain(), timeout=self.timeout)
        except Exception as e:
            raise TransportError(f"Unix socket send failed: {e}") from e

    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """Receive data from Unix socket.

        Args:
            timeout: Receive timeout in seconds.

        Returns:
            Raw bytes received.

        Raises:
            TransportError: If receive fails.
            TimeoutError: If timeout exceeded.
        """
        if not self._reader:
            raise TransportError("Unix socket not connected")

        try:
            import asyncio

            actual_timeout = timeout or self.timeout
            # Read length prefix
            length_bytes = await asyncio.wait_for(
                self._reader.readexactly(4), timeout=actual_timeout
            )
            length = int.from_bytes(length_bytes, byteorder="big")

            # Read message
            data = await asyncio.wait_for(
                self._reader.readexactly(length), timeout=actual_timeout
            )
            return data
        except asyncio.TimeoutError:
            raise TimeoutError("Unix socket receive timeout")
        except Exception as e:
            raise TransportError(f"Unix socket receive failed: {e}") from e

    @property
    def is_connected(self) -> bool:
        """Check if Unix socket is connected.

        Returns:
            True if connected, False otherwise.
        """
        return self._reader is not None and self._writer is not None


class TransportFactory:
    """Factory for creating transport instances."""

    _transports = {
        "http": HttpTransport,
        "websocket": WebSocketTransport,
        "unix": UnixSocketTransport,
    }

    @classmethod
    def create(
        cls,
        transport_type: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Transport:
        """Create a transport instance.

        Args:
            transport_type: Type of transport ('http', 'websocket', 'unix').
            endpoint: Transport endpoint.
            **kwargs: Additional arguments for transport.

        Returns:
            Transport instance.

        Raises:
            KeyError: If transport type not found.
        """
        if transport_type not in cls._transports:
            raise KeyError(
                f"Unknown transport type: {transport_type}. "
                f"Available: {list(cls._transports.keys())}"
            )

        transport_class = cls._transports[transport_type]
        return transport_class(endpoint, **kwargs)

    @classmethod
    def register(cls, name: str, transport_class: type) -> None:
        """Register a custom transport class.

        Args:
            name: Name for the transport.
            transport_class: Transport class to register.
        """
        cls._transports[name] = transport_class
