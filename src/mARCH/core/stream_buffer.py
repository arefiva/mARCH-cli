"""
Stream buffer management for async I/O operations.

Provides StreamBuffer and StreamManager classes for handling stdin/stdout/stderr
streams with buffering, flow control, and event-driven callbacks.
"""

import asyncio
import io
from typing import Callable, Awaitable, Optional, Union
from enum import Enum


class StreamMode(Enum):
    """Enumeration of stream modes."""

    BINARY = "binary"
    TEXT = "text"


class StreamBuffer:
    """
    Handles buffered reading and writing for a single stream.

    Supports non-blocking I/O, backpressure handling, and configurable buffer sizes.
    """

    def __init__(
        self,
        buffer_size: int = 65536,
        mode: StreamMode = StreamMode.TEXT,
        encoding: str = "utf-8",
    ) -> None:
        """
        Initialize a StreamBuffer.

        Args:
            buffer_size: Size of the buffer in bytes (default: 64KB)
            mode: Stream mode (BINARY or TEXT)
            encoding: Text encoding when in TEXT mode (default: utf-8)
        """
        self.buffer_size = buffer_size
        self.mode = mode
        self.encoding = encoding
        self._buffer: asyncio.Queue = asyncio.Queue(maxsize=buffer_size)
        self._paused = False
        self._closed = False
        self._error: Optional[Exception] = None
        self._lock = asyncio.Lock()

    async def read(self, size: int = -1) -> Union[bytes, str]:
        """
        Read from the buffer.

        Args:
            size: Number of bytes/chars to read. -1 means read all available.

        Returns:
            Bytes or str depending on stream mode.

        Raises:
            RuntimeError: If buffer is closed or in error state.
        """
        if self._closed:
            raise RuntimeError("Stream buffer is closed")
        if self._error:
            raise RuntimeError(f"Stream buffer in error state: {self._error}")

        if size == -1:
            # Read all available data
            data = []
            try:
                while True:
                    chunk = self._buffer.get_nowait()
                    data.append(chunk)
            except asyncio.QueueEmpty:
                pass
            result = b"".join(data) if self.mode == StreamMode.BINARY else "".join(data)
            return result

        # Read specific size
        data = []
        bytes_read = 0
        while bytes_read < size:
            try:
                chunk = await asyncio.wait_for(self._buffer.get(), timeout=1.0)
                data.append(chunk)
                if self.mode == StreamMode.BINARY:
                    bytes_read += len(chunk)
                else:
                    bytes_read += len(chunk)
            except asyncio.TimeoutError:
                break

        if self.mode == StreamMode.BINARY:
            return b"".join(data)
        else:
            return "".join(data)

    async def write(self, data: Union[bytes, str]) -> int:
        """
        Write to the buffer.

        Args:
            data: Data to write (bytes or str depending on mode)

        Returns:
            Number of bytes/chars written.

        Raises:
            RuntimeError: If buffer is closed or in error state.
            TypeError: If data type doesn't match stream mode.
        """
        if self._closed:
            raise RuntimeError("Stream buffer is closed")
        if self._error:
            raise RuntimeError(f"Stream buffer in error state: {self._error}")

        # Validate data type
        if self.mode == StreamMode.BINARY and not isinstance(data, bytes):
            raise TypeError(f"Expected bytes, got {type(data)}")
        if self.mode == StreamMode.TEXT and not isinstance(data, str):
            raise TypeError(f"Expected str, got {type(data)}")

        # Wait if paused
        while self._paused:
            await asyncio.sleep(0.01)

        try:
            await self._buffer.put(data)
            return len(data)
        except asyncio.QueueFull:
            raise RuntimeError("Buffer full, unable to write")

    async def flush(self) -> None:
        """Flush the buffer (wait for all data to be read)."""
        while not self._buffer.empty():
            await asyncio.sleep(0.01)

    def pause(self) -> None:
        """Pause reading/writing operations."""
        self._paused = True

    def resume(self) -> None:
        """Resume reading/writing operations."""
        self._paused = False

    async def close(self) -> None:
        """Close the buffer and clean up resources."""
        async with self._lock:
            self._closed = True
            # Clear any remaining data
            try:
                while True:
                    self._buffer.get_nowait()
            except asyncio.QueueEmpty:
                pass

    def set_error(self, error: Exception) -> None:
        """Set an error state on the buffer."""
        self._error = error

    @property
    def is_closed(self) -> bool:
        """Check if buffer is closed."""
        return self._closed

    @property
    def is_paused(self) -> bool:
        """Check if buffer is paused."""
        return self._paused

    @property
    def is_empty(self) -> bool:
        """Check if buffer has no data."""
        return self._buffer.empty()


class StreamManager:
    """
    Manages multiple streams (stdin, stdout, stderr) with unified interface.

    Provides event callbacks for data, errors, and stream close events.
    """

    def __init__(self) -> None:
        """Initialize a StreamManager."""
        self._streams: dict[str, StreamBuffer] = {}
        self._callbacks: dict[str, dict[str, list[Callable]]] = {
            "on_data": {},
            "on_error": {},
            "on_close": {},
        }
        self._lock = asyncio.Lock()

    async def attach_stream(
        self,
        name: str,
        stream: StreamBuffer,
        on_data: Optional[Callable[[Union[bytes, str]], Awaitable[None]]] = None,
        on_error: Optional[Callable[[Exception], Awaitable[None]]] = None,
        on_close: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        """
        Attach a stream to the manager.

        Args:
            name: Stream name (e.g., 'stdout', 'stderr')
            stream: StreamBuffer instance
            on_data: Callback for data events
            on_error: Callback for error events
            on_close: Callback for close events
        """
        async with self._lock:
            self._streams[name] = stream
            if on_data:
                self._callbacks["on_data"][name] = [on_data]
            if on_error:
                self._callbacks["on_error"][name] = [on_error]
            if on_close:
                self._callbacks["on_close"][name] = [on_close]

    async def detach_stream(self, name: str) -> None:
        """
        Detach a stream from the manager.

        Args:
            name: Stream name
        """
        async with self._lock:
            if name in self._streams:
                await self._streams[name].close()
                del self._streams[name]
                for callback_type in self._callbacks:
                    if name in self._callbacks[callback_type]:
                        del self._callbacks[callback_type][name]

    async def write_stream(self, name: str, data: Union[bytes, str]) -> int:
        """
        Write data to a specific stream.

        Args:
            name: Stream name
            data: Data to write

        Returns:
            Number of bytes/chars written

        Raises:
            ValueError: If stream doesn't exist
        """
        if name not in self._streams:
            raise ValueError(f"Stream '{name}' not attached")
        return await self._streams[name].write(data)

    async def read_stream(self, name: str, size: int = -1) -> Union[bytes, str]:
        """
        Read from a specific stream.

        Args:
            name: Stream name
            size: Number of bytes/chars to read

        Returns:
            Bytes or str depending on stream mode

        Raises:
            ValueError: If stream doesn't exist
        """
        if name not in self._streams:
            raise ValueError(f"Stream '{name}' not attached")
        return await self._streams[name].read(size)

    async def get_output(self) -> tuple[Union[bytes, str], Union[bytes, str]]:
        """
        Read all output from stdout and stderr.

        Returns:
            Tuple of (stdout, stderr)
        """
        stdout_data = ""
        stderr_data = ""

        if "stdout" in self._streams:
            stdout_data = await self._streams["stdout"].read()
        if "stderr" in self._streams:
            stderr_data = await self._streams["stderr"].read()

        return (stdout_data, stderr_data)

    def pause_stream(self, name: str) -> None:
        """
        Pause a stream.

        Args:
            name: Stream name
        """
        if name in self._streams:
            self._streams[name].pause()

    def resume_stream(self, name: str) -> None:
        """
        Resume a stream.

        Args:
            name: Stream name
        """
        if name in self._streams:
            self._streams[name].resume()

    async def close_all(self) -> None:
        """Close all attached streams."""
        async with self._lock:
            for name in list(self._streams.keys()):
                await self._streams[name].close()
            self._streams.clear()
            self._callbacks = {"on_data": {}, "on_error": {}, "on_close": {}}

    def get_stream(self, name: str) -> Optional[StreamBuffer]:
        """
        Get a stream by name.

        Args:
            name: Stream name

        Returns:
            StreamBuffer instance or None if not found
        """
        return self._streams.get(name)

    def get_all_streams(self) -> dict[str, StreamBuffer]:
        """Get all attached streams."""
        return dict(self._streams)
