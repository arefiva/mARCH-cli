"""mARCH networking module.

Provides HTTP/WebSocket clients, RPC protocol, connection management,
and reliable message transport.
"""

from mARCH.networking.connection import (
    Connection,
    ConnectionManager,
    ConnectionPoolManager,
    ConnectionState,
)
from mARCH.networking.http_client import (
    ConnectionPool,
    HttpClient,
    WebSocketClient,
)
from mARCH.networking.payload import (
    JsonCodec,
    PayloadCodec,
    PayloadCodecError,
    PayloadSerializer,
    deserialize,
    get_serializer,
    serialize,
)
from mARCH.networking.resilience import (
    BackoffStrategy,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerState,
    ExponentialBackoff,
    LinearBackoff,
    ResilientClient,
    RetryPolicy,
)
from mARCH.networking.rpc import (
    RpcClient,
    RpcError,
    RpcInternalError,
    RpcInvalidParams,
    RpcInvalidRequest,
    RpcMessage,
    RpcMethodNotFound,
    RpcParseError,
    RpcRegistry,
    RpcServer,
)
from mARCH.networking.transport import (
    HttpTransport,
    Transport,
    TransportError,
    TransportFactory,
    UnixSocketTransport,
    WebSocketTransport,
)

__all__ = [
    # Connection management
    "Connection",
    "ConnectionManager",
    "ConnectionPoolManager",
    "ConnectionState",
    # HTTP client
    "HttpClient",
    "WebSocketClient",
    "ConnectionPool",
    # Payload serialization
    "PayloadCodec",
    "JsonCodec",
    "PayloadSerializer",
    "PayloadCodecError",
    "serialize",
    "deserialize",
    "get_serializer",
    # Resilience
    "BackoffStrategy",
    "ExponentialBackoff",
    "LinearBackoff",
    "RetryPolicy",
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerOpenError",
    "ResilientClient",
    # Transport
    "Transport",
    "HttpTransport",
    "WebSocketTransport",
    "UnixSocketTransport",
    "TransportFactory",
    "TransportError",
    # RPC
    "RpcMessage",
    "RpcRegistry",
    "RpcServer",
    "RpcClient",
    "RpcError",
    "RpcParseError",
    "RpcInvalidRequest",
    "RpcMethodNotFound",
    "RpcInvalidParams",
    "RpcInternalError",
]
