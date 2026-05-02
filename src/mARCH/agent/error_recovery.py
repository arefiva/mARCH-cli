"""Error recovery strategies for agents."""

import logging
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Classification of errors."""
    TRANSIENT = "transient"  # Retriable
    PERMANENT = "permanent"  # Non-retriable
    AMBIGUOUS = "ambiguous"  # Requires strategy selection


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    backoff_multiplier: float = 2.0
    jitter_enabled: bool = True
    retriable_errors: List[type] = None

    def __post_init__(self):
        """Initialize retriable errors."""
        if self.retriable_errors is None:
            self.retriable_errors = [
                TimeoutError,
                ConnectionError,
                RuntimeError,
            ]


class ErrorRecoveryStrategy(ABC):
    """Abstract base for error recovery strategies."""

    @abstractmethod
    async def recover(
        self, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt error recovery.

        Args:
            error: The exception that occurred
            context: Error context

        Returns:
            Recovery result dictionary
        """
        pass


class AutoRetryStrategy(ErrorRecoveryStrategy):
    """Automatically retry with exponential backoff."""

    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize auto-retry strategy.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()

    async def recover(
        self, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt automatic retry.

        Args:
            error: The exception that occurred
            context: Error context

        Returns:
            Recovery result
        """
        error_type = type(error)
        should_retry = error_type in self.config.retriable_errors

        if not should_retry:
            logger.warning(f"Error not retriable: {error_type.__name__}")
            return {
                "strategy": "auto_retry",
                "recovered": False,
                "reason": "Error type not retriable",
            }

        attempt = context.get("attempt", 0)
        if attempt >= self.config.max_attempts:
            logger.error("Max retry attempts reached")
            return {
                "strategy": "auto_retry",
                "recovered": False,
                "reason": "Max attempts reached",
                "attempt": attempt,
            }

        # Calculate backoff
        delay_ms = min(
            self.config.base_delay_ms * (self.config.backoff_multiplier ** attempt),
            self.config.max_delay_ms,
        )

        if self.config.jitter_enabled:
            import random
            jitter = random.uniform(0, delay_ms * 0.1)
            delay_ms += jitter

        logger.info(
            f"Retrying after {delay_ms:.0f}ms (attempt {attempt + 1}/{self.config.max_attempts})"
        )

        await asyncio.sleep(delay_ms / 1000.0)

        return {
            "strategy": "auto_retry",
            "recovered": True,
            "delay_ms": delay_ms,
            "next_attempt": attempt + 1,
        }


class ManualInterventionStrategy(ErrorRecoveryStrategy):
    """Wait for manual intervention."""

    async def recover(
        self, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Request manual intervention.

        Args:
            error: The exception that occurred
            context: Error context

        Returns:
            Recovery result (waiting for input)
        """
        logger.warning(f"Manual intervention required for error: {error}")
        logger.info("Waiting for manual recovery...")

        # In a real system, this would wait for user input
        # For now, just log and return

        return {
            "strategy": "manual_intervention",
            "recovered": False,
            "reason": "Awaiting manual intervention",
            "error": str(error),
        }


class GracefulDegradationStrategy(ErrorRecoveryStrategy):
    """Fall back to simpler operations."""

    async def recover(
        self, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt graceful degradation.

        Args:
            error: The exception that occurred
            context: Error context

        Returns:
            Recovery result
        """
        operation = context.get("operation", "unknown")
        logger.warning(f"Degrading operation: {operation}")

        # Simple degradation strategy: reduce scope/complexity
        degraded_context = context.copy()
        degraded_context["degraded"] = True
        degraded_context["original_error"] = str(error)

        return {
            "strategy": "graceful_degradation",
            "recovered": True,
            "degraded_context": degraded_context,
            "recommendation": f"Retry with reduced scope for {operation}",
        }


class HybridRecoveryManager:
    """Manages error recovery with strategy selection."""

    def __init__(self):
        """Initialize recovery manager."""
        self._strategies = {
            "auto_retry": AutoRetryStrategy(),
            "manual_intervention": ManualInterventionStrategy(),
            "graceful_degradation": GracefulDegradationStrategy(),
        }
        self._recovery_log: List[Dict[str, Any]] = []

    def classify_error(self, error: Exception) -> ErrorType:
        """Classify an error.

        Args:
            error: Exception to classify

        Returns:
            ErrorType classification
        """
        # Transient errors
        if isinstance(error, (TimeoutError, ConnectionError)):
            return ErrorType.TRANSIENT

        # Permanent errors
        if isinstance(error, (FileNotFoundError, ValueError, TypeError)):
            return ErrorType.PERMANENT

        # Ambiguous errors
        if isinstance(error, RuntimeError):
            return ErrorType.AMBIGUOUS

        return ErrorType.AMBIGUOUS

    async def choose_strategy(
        self, error: Exception, execution_count: int = 0
    ) -> str:
        """Choose recovery strategy based on error type and context.

        Args:
            error: Exception that occurred
            execution_count: How many times this operation has been attempted

        Returns:
            Strategy name
        """
        error_type = self.classify_error(error)

        if error_type == ErrorType.TRANSIENT:
            return "auto_retry" if execution_count < 3 else "graceful_degradation"
        elif error_type == ErrorType.PERMANENT:
            return "graceful_degradation"
        else:
            # Ambiguous: use retry first, then degrade
            return "auto_retry" if execution_count < 2 else "graceful_degradation"

    async def recover_from_error(
        self, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt to recover from an error.

        Args:
            error: Exception that occurred
            context: Error context

        Returns:
            Recovery result
        """
        strategy_name = await self.choose_strategy(error, context.get("attempt", 0))
        strategy = self._strategies.get(strategy_name)

        if not strategy:
            logger.error(f"Unknown strategy: {strategy_name}")
            return {"recovered": False, "error": "Unknown recovery strategy"}

        logger.info(f"Using {strategy_name} recovery strategy")

        result = await strategy.recover(error, context)
        result["strategy"] = strategy_name
        result["error_type"] = self.classify_error(error).value

        # Log recovery attempt
        self._recovery_log.append(result)

        return result

    def get_recovery_log(self) -> List[Dict[str, Any]]:
        """Get log of all recovery attempts.

        Returns:
            List of recovery attempts
        """
        return self._recovery_log.copy()

    def clear_recovery_log(self) -> None:
        """Clear recovery log."""
        self._recovery_log.clear()
