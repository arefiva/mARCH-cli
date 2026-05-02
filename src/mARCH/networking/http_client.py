"""HTTP and WebSocket client implementations.

Provides unified async HTTP/HTTPS client with connection pooling,
retry logic, and WebSocket support.
"""

import asyncio
from typing import Any, Dict, Optional, Union

import httpx

from mARCH.networking.resilience import ResilientClient, RetryPolicy


class HttpClient:
    """Async HTTP client with resilience features.

    Wraps httpx with retry logic, circuit breaker, and connection pooling.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        retry_policy: Optional[RetryPolicy] = None,
        limits: Optional[httpx.Limits] = None,
    ):
        """Initialize HTTP client.

        Args:
            timeout: Default request timeout in seconds.
            retry_policy: Retry policy for requests. Defaults to RetryPolicy.
            limits: httpx connection limits.
        """
        self.timeout = timeout
        self.retry_policy = retry_policy or RetryPolicy()
        self.limits = limits or httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
        )

        self._client: Optional[httpx.AsyncClient] = None
        self._resilient_client = ResilientClient(retry_policy=self.retry_policy)

    async def __aenter__(self) -> "HttpClient":
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Initialize HTTP client connection."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                limits=self.limits,
                timeout=httpx.Timeout(self.timeout),
            )

    async def disconnect(self) -> None:
        """Close HTTP client connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(
        self,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform GET request with resilience.

        Args:
            url: URL to request.
            **kwargs: Additional arguments for httpx.get().

        Returns:
            httpx.Response object.

        Raises:
            httpx.RequestError: If request fails after retries.
        """
        await self._ensure_connected()
        return await self._resilient_client.call_async(
            self._client.get,  # type: ignore
            url,
            **kwargs,
        )

    async def post(
        self,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform POST request with resilience.

        Args:
            url: URL to request.
            **kwargs: Additional arguments for httpx.post().

        Returns:
            httpx.Response object.

        Raises:
            httpx.RequestError: If request fails after retries.
        """
        await self._ensure_connected()
        return await self._resilient_client.call_async(
            self._client.post,  # type: ignore
            url,
            **kwargs,
        )

    async def put(
        self,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform PUT request with resilience.

        Args:
            url: URL to request.
            **kwargs: Additional arguments for httpx.put().

        Returns:
            httpx.Response object.

        Raises:
            httpx.RequestError: If request fails after retries.
        """
        await self._ensure_connected()
        return await self._resilient_client.call_async(
            self._client.put,  # type: ignore
            url,
            **kwargs,
        )

    async def patch(
        self,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform PATCH request with resilience.

        Args:
            url: URL to request.
            **kwargs: Additional arguments for httpx.patch().

        Returns:
            httpx.Response object.

        Raises:
            httpx.RequestError: If request fails after retries.
        """
        await self._ensure_connected()
        return await self._resilient_client.call_async(
            self._client.patch,  # type: ignore
            url,
            **kwargs,
        )

    async def delete(
        self,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform DELETE request with resilience.

        Args:
            url: URL to request.
            **kwargs: Additional arguments for httpx.delete().

        Returns:
            httpx.Response object.

        Raises:
            httpx.RequestError: If request fails after retries.
        """
        await self._ensure_connected()
        return await self._resilient_client.call_async(
            self._client.delete,  # type: ignore
            url,
            **kwargs,
        )

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform arbitrary HTTP request with resilience.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: URL to request.
            **kwargs: Additional arguments for httpx.request().

        Returns:
            httpx.Response object.

        Raises:
            httpx.RequestError: If request fails after retries.
        """
        await self._ensure_connected()
        return await self._resilient_client.call_async(
            self._client.request,  # type: ignore
            method,
            url,
            **kwargs,
        )

    async def _ensure_connected(self) -> None:
        """Ensure client is connected."""
        if self._client is None:
            await self.connect()


class WebSocketClient:
    """WebSocket client for bidirectional communication."""

    def __init__(self, url: str, timeout: float = 30.0):
        """Initialize WebSocket client.

        Args:
            url: WebSocket URL to connect to.
            timeout: Connection timeout in seconds.
        """
        self.url = url
        self.timeout = timeout
        self._websocket: Optional[Any] = None
        self._reader_task: Optional[asyncio.Task[None]] = None

    async def connect(self) -> None:
        """Connect to WebSocket server.

        Raises:
            ConnectionError: If connection fails.
        """
        try:
            import websockets

            self._websocket = await asyncio.wait_for(
                websockets.connect(self.url),  # type: ignore
                timeout=self.timeout,
            )
        except ImportError:
            raise ImportError("websockets library required for WebSocket support")
        except asyncio.TimeoutError:
            raise ConnectionError(f"WebSocket connection timeout to {self.url}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.url}: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self._websocket:
            await self._websocket.close()
            self._websocket = None

    async def send(self, data: Union[str, bytes]) -> None:
        """Send data to WebSocket server.

        Args:
            data: Data to send (string or bytes).

        Raises:
            ConnectionError: If not connected or send fails.
        """
        if not self._websocket:
            raise ConnectionError("WebSocket not connected")

        try:
            await self._websocket.send(data)
        except Exception as e:
            raise ConnectionError(f"Failed to send WebSocket message: {e}") from e

    async def receive(self) -> Union[str, bytes]:
        """Receive data from WebSocket server.

        Returns:
            Received data (string or bytes).

        Raises:
            ConnectionError: If not connected or receive fails.
        """
        if not self._websocket:
            raise ConnectionError("WebSocket not connected")

        try:
            return await asyncio.wait_for(
                self._websocket.recv(),  # type: ignore
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError("WebSocket receive timeout")
        except Exception as e:
            raise ConnectionError(f"Failed to receive WebSocket message: {e}") from e

    async def send_json(self, data: Dict[str, Any]) -> None:
        """Send JSON data to WebSocket server.

        Args:
            data: JSON-serializable data.

        Raises:
            ConnectionError: If send fails.
        """
        import json

        await self.send(json.dumps(data))

    async def receive_json(self) -> Dict[str, Any]:
        """Receive JSON data from WebSocket server.

        Returns:
            Parsed JSON data.

        Raises:
            ConnectionError: If receive fails or data is not valid JSON.
        """
        import json

        data = await self.receive()
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise ConnectionError(f"Invalid JSON received: {e}") from e

    async def __aenter__(self) -> "WebSocketClient":
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected.

        Returns:
            True if connected, False otherwise.
        """
        return self._websocket is not None


class ConnectionPool:
    """HTTP connection pool with lifecycle management."""

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive: int = 20,
        timeout: float = 30.0,
    ):
        """Initialize connection pool.

        Args:
            max_connections: Maximum total connections.
            max_keepalive: Maximum keep-alive connections per host.
            timeout: Default request timeout.
        """
        self.max_connections = max_connections
        self.max_keepalive = max_keepalive
        self.timeout = timeout
        self._client = HttpClient(
            timeout=timeout,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive,
            ),
        )

    async def connect(self) -> None:
        """Initialize the connection pool."""
        await self._client.connect()

    async def disconnect(self) -> None:
        """Close all connections in the pool."""
        await self._client.disconnect()

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute request using pooled connection.

        Args:
            method: HTTP method.
            url: URL to request.
            **kwargs: Additional arguments for HTTP request.

        Returns:
            httpx.Response object.
        """
        return await self._client.request(method, url, **kwargs)

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute GET request using pooled connection."""
        return await self._client.get(url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute POST request using pooled connection."""
        return await self._client.post(url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute PUT request using pooled connection."""
        return await self._client.put(url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute PATCH request using pooled connection."""
        return await self._client.patch(url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute DELETE request using pooled connection."""
        return await self._client.delete(url, **kwargs)

    async def __aenter__(self) -> "ConnectionPool":
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        await self.disconnect()

    @property
    def client(self) -> HttpClient:
        """Get underlying HTTP client.

        Returns:
            HttpClient instance.
        """
        return self._client
