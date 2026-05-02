"""Resilience patterns: circuit breaker, bulkhead, timeouts."""

import logging
import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """States for circuit breaker."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failures to trigger open state
            success_threshold: Successes to reset from half-open
            timeout_seconds: Time before trying again
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> CircuitState:
        """Get current state."""
        return self._state

    async def call_with_breaker(
        self, func: Callable, *args, **kwargs
    ) -> Dict[str, Any]:
        """Execute function with circuit protection.

        Args:
            func: Async function to execute
            args: Function arguments
            kwargs: Function keyword arguments

        Returns:
            Result dictionary
        """
        # Check if should transition from OPEN to HALF_OPEN
        if self._state == CircuitState.OPEN:
            time_since_failure = time.time() - self._last_failure_time
            if time_since_failure > self.timeout_seconds:
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
            else:
                return {
                    "status": "open",
                    "error": "Circuit breaker is OPEN",
                }

        # Execute function
        try:
            result = await func(*args, **kwargs)

            # Handle success
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    logger.info("Circuit breaker closing (recovered)")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            else:
                self._failure_count = 0

            return {"status": "success", "result": result}

        except Exception as e:
            logger.warning(f"Circuit breaker intercepted error: {e}")
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self.failure_threshold:
                logger.error("Circuit breaker opening")
                self._state = CircuitState.OPEN
                self._success_count = 0

            return {"status": "error", "error": str(e)}

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info("Circuit breaker reset")


class BulkheadExecutor:
    """Bulkhead pattern for limiting concurrent executions."""

    def __init__(self, max_concurrent: int = 5):
        """Initialize bulkhead executor.

        Args:
            max_concurrent: Maximum concurrent executions
        """
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        self._queue: list[tuple[Callable, tuple, dict]] = []

    async def execute(
        self, func: Callable, *args, **kwargs
    ) -> Dict[str, Any]:
        """Execute function with bulkhead protection.

        Args:
            func: Async function to execute
            args: Function arguments
            kwargs: Function keyword arguments

        Returns:
            Result dictionary
        """
        try:
            async with self._semaphore:
                self._active_count += 1
                logger.debug(
                    f"Bulkhead: {self._active_count}/{self.max_concurrent} slots in use"
                )

                try:
                    result = await func(*args, **kwargs)
                    return {"status": "success", "result": result}
                finally:
                    self._active_count -= 1

        except asyncio.CancelledError:
            logger.warning("Bulkhead execution cancelled")
            return {"status": "cancelled", "error": "Execution cancelled"}

    def get_status(self) -> Dict[str, int]:
        """Get bulkhead status.

        Returns:
            Status dictionary
        """
        return {
            "max_concurrent": self.max_concurrent,
            "active": self._active_count,
            "available": self.max_concurrent - self._active_count,
        }


class TimeoutManager:
    """Manages adaptive timeouts based on historical data."""

    def __init__(self, default_timeout_ms: int = 30000):
        """Initialize timeout manager.

        Args:
            default_timeout_ms: Default timeout in milliseconds
        """
        self.default_timeout_ms = default_timeout_ms
        self._execution_times: Dict[str, list[float]] = {}
        self._timeout_overrides: Dict[str, int] = {}

    def record_execution(self, operation: str, duration_ms: float) -> None:
        """Record execution duration.

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
        """
        if operation not in self._execution_times:
            self._execution_times[operation] = []

        self._execution_times[operation].append(duration_ms)

        # Keep only last 100 recordings
        if len(self._execution_times[operation]) > 100:
            self._execution_times[operation] = self._execution_times[operation][-100:]

    def get_adaptive_timeout(self, operation: str) -> int:
        """Get adaptive timeout for an operation.

        Args:
            operation: Operation name

        Returns:
            Timeout in milliseconds
        """
        # Check for override
        if operation in self._timeout_overrides:
            return self._timeout_overrides[operation]

        # Calculate from historical data
        if operation in self._execution_times:
            times = self._execution_times[operation]
            if times:
                # Use 95th percentile + 50% buffer
                sorted_times = sorted(times)
                idx = int(len(sorted_times) * 0.95)
                p95 = sorted_times[idx]
                adaptive = int(p95 * 1.5)
                return max(adaptive, self.default_timeout_ms)

        return self.default_timeout_ms

    def set_timeout_override(self, operation: str, timeout_ms: int) -> None:
        """Set a manual timeout override.

        Args:
            operation: Operation name
            timeout_ms: Timeout in milliseconds
        """
        self._timeout_overrides[operation] = timeout_ms
        logger.debug(f"Set timeout override for {operation}: {timeout_ms}ms")

    def clear_timeout_override(self, operation: str) -> None:
        """Clear timeout override.

        Args:
            operation: Operation name
        """
        if operation in self._timeout_overrides:
            del self._timeout_overrides[operation]

    def get_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for an operation.

        Args:
            operation: Operation name

        Returns:
            Statistics dictionary
        """
        if operation not in self._execution_times:
            return {"operation": operation, "recordings": 0}

        times = self._execution_times[operation]
        sorted_times = sorted(times)

        return {
            "operation": operation,
            "recordings": len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "avg_ms": sum(times) / len(times),
            "p50_ms": sorted_times[len(sorted_times) // 2],
            "p95_ms": sorted_times[int(len(sorted_times) * 0.95)],
            "p99_ms": sorted_times[int(len(sorted_times) * 0.99)],
        }
