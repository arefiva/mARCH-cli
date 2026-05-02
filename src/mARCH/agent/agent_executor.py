"""Agent execution engine.

Manages individual agent execution lifecycle with async/parallel support.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


class ExecutionStatus(str, Enum):
    """Status of an execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


@dataclass
class ExecutionConfig:
    """Configuration for agent execution."""
    timeout_ms: int = 30000  # 30 seconds default
    max_retries: int = 3
    retry_backoff_ms: int = 1000
    max_retry_backoff_ms: int = 30000
    retry_backoff_multiplier: float = 2.0
    error_recovery_enabled: bool = True
    inherit_context: bool = True
    jitter_enabled: bool = True


@dataclass
class ExecutionResult:
    """Result of an execution."""
    status: ExecutionStatus
    data: Any = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    execution_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def is_success(self) -> bool:
        """Check if execution succeeded."""
        return self.status == ExecutionStatus.SUCCESS

    def is_failure(self) -> bool:
        """Check if execution failed."""
        return self.status == ExecutionStatus.FAILURE

    def is_timeout(self) -> bool:
        """Check if execution timed out."""
        return self.status == ExecutionStatus.TIMEOUT


class AgentExecutor:
    """Main agent execution engine."""

    def __init__(self, agent_id: str, config: Optional[ExecutionConfig] = None):
        """Initialize the executor.

        Args:
            agent_id: Unique identifier for the agent
            config: Execution configuration
        """
        self.agent_id = agent_id
        self.config = config or ExecutionConfig()
        self._execution_count = 0
        self._last_execution_time = 0.0

    async def execute(
        self, command: str, context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute a command.

        Args:
            command: Command to execute
            context: Optional execution context

        Returns:
            ExecutionResult with status and output
        """
        return await self.execute_with_timeout(
            command, context, self.config.timeout_ms
        )

    async def execute_with_timeout(
        self,
        command: str,
        context: Optional[Dict[str, Any]] = None,
        timeout_ms: Optional[int] = None,
    ) -> ExecutionResult:
        """Execute a command with timeout.

        Args:
            command: Command to execute
            context: Optional execution context
            timeout_ms: Timeout in milliseconds

        Returns:
            ExecutionResult with status and output
        """
        timeout_ms = timeout_ms or self.config.timeout_ms
        start_time = time.time()
        execution_id = f"{self.agent_id}-{self._execution_count}-{int(start_time * 1000)}"
        self._execution_count += 1

        try:
            # Pre-execution setup
            await self._pre_execute(command, context)

            # Execute with timeout
            timeout_sec = timeout_ms / 1000.0
            result = await asyncio.wait_for(
                self._execute_command(command, context), timeout=timeout_sec
            )

            # Post-execution
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms
            result.execution_id = execution_id

            await self._post_execute(result)

            self._last_execution_time = duration_ms
            return result

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            result = ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                errors=[f"Execution timed out after {timeout_ms}ms"],
                duration_ms=duration_ms,
                execution_id=execution_id,
            )
            await self._handle_timeout(result, command, context)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = ExecutionResult(
                status=ExecutionStatus.FAILURE,
                errors=[str(e)],
                duration_ms=duration_ms,
                execution_id=execution_id,
            )
            await self._handle_error(result, e, command, context)
            return result

    async def execute_with_retry(
        self,
        command: str,
        context: Optional[Dict[str, Any]] = None,
        retry_config: Optional[ExecutionConfig] = None,
    ) -> ExecutionResult:
        """Execute a command with retry logic.

        Args:
            command: Command to execute
            context: Optional execution context
            retry_config: Retry configuration (uses self.config if not provided)

        Returns:
            ExecutionResult with status and output
        """
        config = retry_config or self.config
        last_result = None

        for attempt in range(config.max_retries):
            result = await self.execute_with_timeout(
                command, context, config.timeout_ms
            )

            if result.is_success():
                return result

            last_result = result

            # Don't retry on the last attempt
            if attempt < config.max_retries - 1:
                # Calculate backoff with optional jitter
                backoff_ms = min(
                    config.retry_backoff_ms * (config.retry_backoff_multiplier ** attempt),
                    config.max_retry_backoff_ms,
                )

                if config.jitter_enabled:
                    import random
                    jitter = random.uniform(0, backoff_ms * 0.1)
                    backoff_ms += jitter

                result.warnings.append(
                    f"Retrying after {backoff_ms:.0f}ms (attempt {attempt + 1}/{config.max_retries})"
                )
                await asyncio.sleep(backoff_ms / 1000.0)

        return last_result or ExecutionResult(
            status=ExecutionStatus.FAILURE,
            errors=["All retry attempts failed"],
        )

    async def execute_parallel(
        self, commands: List[str], context: Optional[Dict[str, Any]] = None
    ) -> List[ExecutionResult]:
        """Execute multiple commands in parallel.

        Args:
            commands: List of commands to execute
            context: Optional execution context

        Returns:
            List of ExecutionResults in the same order as commands
        """
        tasks = [self.execute(cmd, context) for cmd in commands]
        return await asyncio.gather(*tasks, return_exceptions=True)

    # Private methods

    async def _pre_execute(self, command: str, context: Optional[Dict[str, Any]]):
        """Pre-execution setup hook."""
        # Can be overridden by subclasses
        pass

    async def _execute_command(
        self, command: str, context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute the actual command.

        Args:
            command: Command to execute
            context: Optional execution context

        Returns:
            ExecutionResult with status and output
        """
        # This would be implemented by subclasses or specialized executors
        # For now, return a simple success result
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            data={"command": command, "output": "Mock execution"},
        )

    async def _post_execute(self, result: ExecutionResult):
        """Post-execution cleanup hook."""
        # Can be overridden by subclasses
        pass

    async def _handle_error(
        self,
        result: ExecutionResult,
        error: Exception,
        command: str,
        context: Optional[Dict[str, Any]],
    ):
        """Handle execution errors.

        Args:
            result: The execution result
            error: The exception that occurred
            command: The command that failed
            context: Optional execution context
        """
        if self.config.error_recovery_enabled:
            result.warnings.append("Error recovery is enabled but no strategy configured")

    async def _handle_timeout(
        self,
        result: ExecutionResult,
        command: str,
        context: Optional[Dict[str, Any]],
    ):
        """Handle execution timeouts.

        Args:
            result: The execution result
            command: The command that timed out
            context: Optional execution context
        """
        # Can be overridden by subclasses
        pass
