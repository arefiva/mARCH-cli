"""Unit tests for agent executor."""

import pytest
import asyncio
from src.mARCH.agent.agent_executor import (
    AgentExecutor,
    ExecutionConfig,
    ExecutionResult,
    ExecutionStatus,
)


@pytest.fixture
def executor():
    """Create an executor for testing."""
    config = ExecutionConfig(timeout_ms=5000, max_retries=2)
    return AgentExecutor("test-agent", config)


@pytest.mark.asyncio
async def test_executor_initialization(executor):
    """Test executor initialization."""
    assert executor.agent_id == "test-agent"
    assert executor.config.timeout_ms == 5000
    assert executor.config.max_retries == 2


@pytest.mark.asyncio
async def test_execute_basic(executor):
    """Test basic execution."""
    result = await executor.execute("test command")
    assert result is not None
    assert isinstance(result, ExecutionResult)
    assert result.status in ExecutionStatus.__members__.values()


@pytest.mark.asyncio
async def test_execute_with_timeout(executor):
    """Test execution with timeout."""
    config = ExecutionConfig(timeout_ms=100)
    fast_executor = AgentExecutor("fast-test", config)
    
    # This should complete quickly
    result = await fast_executor.execute_with_timeout(
        "echo test", None, 1000
    )
    assert result is not None


@pytest.mark.asyncio
async def test_execute_parallel(executor):
    """Test parallel execution."""
    commands = ["cmd1", "cmd2", "cmd3"]
    results = await executor.execute_parallel(commands)
    
    assert len(results) == len(commands)
    assert all(isinstance(r, ExecutionResult) for r in results)


@pytest.mark.asyncio
async def test_execution_result_properties():
    """Test ExecutionResult properties."""
    result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        data={"output": "test"},
        duration_ms=100.0,
    )
    
    assert result.is_success() is True
    assert result.is_failure() is False
    assert result.is_timeout() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
