"""Resilience patterns for network communication.

Implements retry logic, circuit breaker pattern, and error recovery strategies.
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Optional, Set, Type, TypeVar

T = TypeVar("T")


class CircuitBreakerState(Enum):
    """States of a circuit breaker."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class BackoffStrategy(ABC):
    """Abstract base class for backoff strategies."""

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Get delay for attempt number.

        Args:
            attempt: Attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        pass


class ExponentialBackoff(BackoffStrategy):
    """Exponential backoff strategy with jitter."""

    def __init__(
        self,
        base: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        """Initialize exponential backoff.

        Args:
            base: Base delay in seconds.
            max_delay: Maximum delay in seconds.
            jitter: Whether to add random jitter.
        """
        self.base = base
        self.max_delay = max_delay
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: Attempt number (0-indexed).

        Returns:
            Delay in seconds, capped at max_delay.
        """
        delay = self.base * (2 ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add jitter: ±10% of delay
            jitter_amount = delay * 0.1
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)


class LinearBackoff(BackoffStrategy):
    """Linear backoff strategy."""

    def __init__(self, base: float = 1.0, max_delay: float = 60.0):
        """Initialize linear backoff.

        Args:
            base: Base delay in seconds.
            max_delay: Maximum delay in seconds.
        """
        self.base = base
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        """Calculate linear backoff delay.

        Args:
            attempt: Attempt number (0-indexed).

        Returns:
            Delay in seconds, capped at max_delay.
        """
        delay = self.base * (attempt + 1)
        return min(delay, self.max_delay)


class RetryPolicy:
    """Configurable retry strategy."""

    def __init__(
        self,
        max_retries: int = 3,
        backoff: Optional[BackoffStrategy] = None,
        retriable_exceptions: Optional[Set[Type[Exception]]] = None,
        timeout: float = 30.0,
    ):
        """Initialize retry policy.

        Args:
            max_retries: Maximum number of retries.
            backoff: Backoff strategy to use. Defaults to ExponentialBackoff.
            retriable_exceptions: Set of exceptions that trigger retries.
            timeout: Total timeout for all attempts in seconds.
        """
        self.max_retries = max_retries
        self.backoff = backoff or ExponentialBackoff()
        self.retriable_exceptions = retriable_exceptions or {
            TimeoutError,
            ConnectionError,
            OSError,
        }
        self.timeout = timeout

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if request should be retried.

        Args:
            exception: The exception that occurred.
            attempt: Current attempt number (0-indexed).

        Returns:
            True if should retry, False otherwise.
        """
        if attempt >= self.max_retries:
            return False
        return type(exception) in self.retriable_exceptions

    def get_delay(self, attempt: int) -> float:
        """Get retry delay for attempt.

        Args:
            attempt: Attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        return self.backoff.get_delay(attempt)


class CircuitBreaker:
    """Circuit breaker implementation.

    Protects against cascading failures by stopping requests when
    error rate exceeds threshold.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit.
            recovery_timeout: Seconds before transitioning to half-open.
            success_threshold: Successes in half-open before closing circuit.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result of func.

        Raises:
            CircuitBreakerOpenError: If circuit is open.
            Exception: Any exception raised by func (if circuit not open).
        """
        self._check_state()

        if self.state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    async def call_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute async function with circuit breaker protection.

        Args:
            func: Async function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result of func.

        Raises:
            CircuitBreakerOpenError: If circuit is open.
            Exception: Any exception raised by func (if circuit not open).
        """
        self._check_state()

        if self.state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def _check_state(self) -> None:
        """Check and update circuit breaker state."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            return

        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time is None:
                return

            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0

    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.success_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class ResilientClient:
    """Wrapper combining retry logic and circuit breaker patterns."""

    def __init__(
        self,
        retry_policy: Optional[RetryPolicy] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        """Initialize resilient client.

        Args:
            retry_policy: Retry policy to use. Defaults to RetryPolicy().
            circuit_breaker: Circuit breaker to use. Defaults to CircuitBreaker().
        """
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with retry and circuit breaker protection.

        Args:
            func: Function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result of func.

        Raises:
            Exception: Last exception encountered or CircuitBreakerOpenError.
        """
        start_time = time.time()
        last_exception = None

        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                return self.circuit_breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpenError:
                raise
            except Exception as e:
                last_exception = e
                elapsed = time.time() - start_time

                if elapsed >= self.retry_policy.timeout:
                    raise TimeoutError(
                        f"Operation exceeded timeout of {self.retry_policy.timeout}s"
                    ) from e

                if not self.retry_policy.should_retry(e, attempt):
                    raise

                delay = self.retry_policy.get_delay(attempt)
                time.sleep(delay)

        raise last_exception or RuntimeError("Unknown error during retry")

    async def call_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute async function with retry and circuit breaker protection.

        Args:
            func: Async function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result of func.

        Raises:
            Exception: Last exception encountered or CircuitBreakerOpenError.
        """
        start_time = time.time()
        last_exception = None

        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                return await self.circuit_breaker.call_async(func, *args, **kwargs)
            except CircuitBreakerOpenError:
                raise
            except Exception as e:
                last_exception = e
                elapsed = time.time() - start_time

                if elapsed >= self.retry_policy.timeout:
                    raise TimeoutError(
                        f"Operation exceeded timeout of {self.retry_policy.timeout}s"
                    ) from e

                if not self.retry_policy.should_retry(e, attempt):
                    raise

                delay = self.retry_policy.get_delay(attempt)
                await asyncio.sleep(delay)

        raise last_exception or RuntimeError("Unknown error during retry")
