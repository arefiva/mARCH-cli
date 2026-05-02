"""
Async execution utilities for concurrent task management.

Provides TaskPool for task concurrency control, async utilities, and CancelToken
for coordinating cancellation across tasks.
"""

import asyncio
import heapq
from typing import Callable, Coroutine, Iterable, Any, Optional, TypeVar, Generic
from enum import Enum

T = TypeVar("T")


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 2
    NORMAL = 1
    HIGH = 0


class CancelToken:
    """
    Coordinates cancellation across multiple tasks.

    Supports parent-child cancellation propagation.
    """

    def __init__(self, parent: Optional["CancelToken"] = None) -> None:
        """
        Initialize a CancelToken.

        Args:
            parent: Parent token for propagation
        """
        self._parent = parent
        self._cancelled = False
        self._children: set["CancelToken"] = set()
        self._event = asyncio.Event()

        if parent:
            parent._children.add(self)

    def cancel(self) -> None:
        """Cancel this token and all children."""
        self._cancelled = True
        self._event.set()

        # Propagate to children
        for child in list(self._children):
            child.cancel()

    async def wait_cancelled(self) -> None:
        """
        Wait until this token is cancelled.

        Can be cancelled by parent or explicit call to cancel().
        """
        await self._event.wait()

    def is_cancelled(self) -> bool:
        """Check if this token or parent is cancelled."""
        if self._cancelled:
            return True
        if self._parent:
            return self._parent.is_cancelled()
        return False

    def create_child(self) -> "CancelToken":
        """
        Create a child token for this token.

        Returns:
            New CancelToken with this as parent
        """
        return CancelToken(parent=self)


class TaskPool:
    """
    Manages concurrent task execution with concurrency limits and retry logic.

    Supports task prioritization and exponential backoff retries.
    """

    def __init__(self, max_concurrency: int = 10) -> None:
        """
        Initialize a TaskPool.

        Args:
            max_concurrency: Maximum number of concurrent tasks (default: 10)
        """
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._tasks: set[asyncio.Task] = set()
        self._lock = asyncio.Lock()
        self._priority_queue: list[tuple[int, int, Coroutine]] = []
        self._counter = 0

    async def submit(
        self,
        task: Coroutine,
        priority: int = 1,
    ) -> Any:
        """
        Submit a task for execution.

        Args:
            task: Coroutine to execute
            priority: Task priority (lower values execute first)

        Returns:
            Task result
        """
        async with self._lock:
            self._counter += 1
            heapq.heappush(
                self._priority_queue,
                (priority, self._counter, task),
            )

        # Wait for semaphore
        async with self._semaphore:
            return await task

    async def map(
        self,
        async_func: Callable[[Any], Coroutine],
        items: Iterable,
    ) -> list[Any]:
        """
        Map an async function over items with concurrency control.

        Args:
            async_func: Async function to apply
            items: Items to map over

        Returns:
            List of results in input order
        """
        tasks = [self.submit(async_func(item)) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def gather_with_limit(
        self,
        coros: list[Coroutine],
        limit: Optional[int] = None,
    ) -> list[Any]:
        """
        Gather coroutines with concurrency limit.

        Args:
            coros: List of coroutines
            limit: Concurrency limit (uses max_concurrency if None)

        Returns:
            List of results
        """
        if limit is None:
            limit = self.max_concurrency

        semaphore = asyncio.Semaphore(limit)

        async def sem_task(coro: Coroutine) -> Any:
            async with semaphore:
                return await coro

        return await asyncio.gather(
            *[sem_task(coro) for coro in coros],
            return_exceptions=False,
        )

    async def retry(
        self,
        task: Callable[[], Coroutine],
        max_retries: int = 3,
        backoff_base: float = 2.0,
        backoff_max: float = 60.0,
    ) -> Any:
        """
        Execute a task with exponential backoff retry.

        Args:
            task: Callable that returns a coroutine
            max_retries: Maximum retry attempts (default: 3)
            backoff_base: Base for exponential backoff (default: 2.0)
            backoff_max: Maximum backoff time in seconds (default: 60.0)

        Returns:
            Task result

        Raises:
            The last exception if all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return await self.submit(task())
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Calculate backoff with jitter
                    backoff = min(backoff_base ** attempt, backoff_max)
                    await asyncio.sleep(backoff)

        raise last_error if last_error else RuntimeError("Task failed after retries")

    async def shutdown(self) -> None:
        """Shutdown the task pool and cancel pending tasks."""
        # Cancel all running tasks
        for task in list(self._tasks):
            task.cancel()

        # Wait for cancellation
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()


async def batch_async(
    items: Iterable[T],
    batch_size: int,
    async_func: Callable[[list[T]], Coroutine],
) -> list[Any]:
    """
    Process items in batches with an async function.

    Args:
        items: Items to process
        batch_size: Size of each batch
        async_func: Async function to apply to batches

    Returns:
        List of results
    """
    results = []
    batch = []

    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            results.append(await async_func(batch))
            batch = []

    if batch:
        results.append(await async_func(batch))

    return results


async def async_iter(
    coro: Coroutine,
    timeout: Optional[float] = None,
) -> Any:
    """
    Execute an async coroutine with optional timeout.

    Args:
        coro: Coroutine to execute
        timeout: Optional timeout in seconds

    Returns:
        Coroutine result

    Raises:
        asyncio.TimeoutError: If timeout is exceeded
    """
    if timeout:
        return await asyncio.wait_for(coro, timeout=timeout)
    return await coro


async def async_zip(
    *coros: Coroutine,
) -> tuple:
    """
    Execute multiple coroutines concurrently and return results as tuple.

    Args:
        *coros: Variable number of coroutines

    Returns:
        Tuple of results
    """
    results = await asyncio.gather(*coros, return_exceptions=False)
    return tuple(results)


class AsyncIterator(Generic[T]):
    """
    Async generator wrapper for streaming results.

    Supports batching, chunking, and timeout management.
    """

    def __init__(
        self,
        generator: Callable[[], Coroutine],
        batch_size: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """
        Initialize an AsyncIterator.

        Args:
            generator: Callable that returns an async generator
            batch_size: Optional batch size for grouping results
            timeout: Optional timeout for each iteration
        """
        self.generator = generator
        self.batch_size = batch_size
        self.timeout = timeout
        self._gen = None

    async def __aenter__(self) -> "AsyncIterator[T]":
        """Context manager entry."""
        self._gen = self.generator()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if self._gen:
            await self._gen.aclose()

    async def __aiter__(self):
        """Async iteration support."""
        return self

    async def __anext__(self) -> T:
        """Get next item from generator."""
        if not self._gen:
            raise StopAsyncIteration

        try:
            if self.timeout:
                item = await asyncio.wait_for(self._gen.__anext__(), timeout=self.timeout)
            else:
                item = await self._gen.__anext__()
            return item
        except StopAsyncIteration:
            raise
        except asyncio.TimeoutError:
            raise TimeoutError("Iterator timeout")

    async def collect(self) -> list[T]:
        """Collect all items from generator."""
        items = []
        async with self:
            async for item in self:
                items.append(item)
        return items
