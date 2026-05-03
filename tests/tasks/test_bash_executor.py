"""
Unit tests for BashTaskExecutor covering US-002 (timeout/cleanup) and
US-003 (concurrent stream reading).
"""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mARCH.core.task_types import TaskBase, TaskType
from mARCH.tasks.bash_executor import BashTaskExecutor


def _make_task(command: str, timeout: float = 30, shell: bool = False) -> TaskBase:
    params: dict = {"command": command, "timeout": timeout}
    if shell:
        params["shell"] = True
    return TaskBase(id="test-1", description="test", type=TaskType.BASH, params=params)


# ---------------------------------------------------------------------------
# US-002: Kill subprocess on timeout and clean up temp files
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_called_on_timeout():
    """process.kill() must be called when a command times out."""
    executor = BashTaskExecutor()

    mock_process = MagicMock()
    mock_process.kill = MagicMock()
    mock_process.wait = AsyncMock()

    async def slow_command(*args, **kwargs):
        executor._current_process = mock_process
        await asyncio.sleep(10)

    with patch.object(executor, "_run_command_streaming", slow_command):
        result = await executor.execute(_make_task("sleep 10", timeout=0.05))

    assert result.status == "failed"
    assert "timed out" in result.error
    mock_process.kill.assert_called_once()


@pytest.mark.asyncio
async def test_wait_called_on_timeout():
    """process.wait() must be awaited after kill() to reap the zombie."""
    executor = BashTaskExecutor()

    mock_process = MagicMock()
    mock_process.kill = MagicMock()
    mock_process.wait = AsyncMock()

    async def slow_command(*args, **kwargs):
        executor._current_process = mock_process
        await asyncio.sleep(10)

    with patch.object(executor, "_run_command_streaming", slow_command):
        await executor.execute(_make_task("sleep 10", timeout=0.05))

    mock_process.wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_temp_files_deletes_tracked_files():
    """cleanup_temp_files() must remove all tracked temp files from disk."""
    executor = BashTaskExecutor()

    fd1, path1 = tempfile.mkstemp(suffix=".out", prefix="task_")
    os.close(fd1)
    fd2, path2 = tempfile.mkstemp(suffix=".out", prefix="task_")
    os.close(fd2)
    executor._temp_files.add(path1)
    executor._temp_files.add(path2)

    assert os.path.exists(path1)
    assert os.path.exists(path2)

    executor.cleanup_temp_files()

    assert not os.path.exists(path1)
    assert not os.path.exists(path2)
    assert len(executor._temp_files) == 0


@pytest.mark.asyncio
async def test_cleanup_is_idempotent():
    """Calling cleanup_temp_files() twice must not raise any error."""
    executor = BashTaskExecutor()

    fd, path = tempfile.mkstemp(suffix=".out", prefix="task_")
    os.close(fd)
    executor._temp_files.add(path)

    executor.cleanup_temp_files()
    executor.cleanup_temp_files()  # second call — must not raise


@pytest.mark.asyncio
async def test_cleanup_handles_already_deleted_files():
    """cleanup_temp_files() must not raise FileNotFoundError for missing files."""
    executor = BashTaskExecutor()

    executor._temp_files.add("/tmp/this_file_does_not_exist_at_all_xyz.out")

    # Should complete without raising
    executor.cleanup_temp_files()


# ---------------------------------------------------------------------------
# US-003: Read stdout and stderr concurrently to prevent deadlock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_large_stderr_does_not_deadlock():
    """A subprocess writing >64KB to stderr must complete within 5 seconds."""
    executor = BashTaskExecutor()
    big_data = "x" * (65 * 1024)  # 65 KB
    task = _make_task(
        f'python3 -c "import sys; sys.stderr.write({big_data!r})"',
        timeout=5,
    )
    result = await executor.execute(task)
    assert result.status in ("completed", "failed")  # not a timeout
    assert "timed out" not in (result.error or "")


@pytest.mark.asyncio
async def test_both_streams_captured_concurrently():
    """Both stdout and stderr must be fully captured when both produce output."""
    executor = BashTaskExecutor()
    task = _make_task(
        'python3 -c "import sys; print(\'hello\'); sys.stderr.write(\'world\')"',
        timeout=10,
    )
    result = await executor.execute(task)
    assert "hello" in result.stdout
    assert "world" in result.stderr


@pytest.mark.asyncio
async def test_no_output_returns_empty_strings():
    """A subprocess with no output on either stream must return empty strings."""
    executor = BashTaskExecutor()
    task = _make_task("true", timeout=10)
    result = await executor.execute(task)
    assert result.status == "completed"
    assert result.stdout == ""
    assert result.stderr == ""


@pytest.mark.asyncio
async def test_overflow_to_disk_when_output_exceeds_limit():
    """When stdout exceeds MAX_OUTPUT_SIZE, overflow file must be created."""
    executor = BashTaskExecutor()
    executor.MAX_OUTPUT_SIZE = 10  # tiny limit for testing

    task = _make_task('echo "hello world this is a long line"', timeout=10)
    result = await executor.execute(task)

    assert result.output_file is not None
    assert os.path.exists(result.output_file)

    # Cleanup
    executor.cleanup_temp_files()
    assert not os.path.exists(result.output_file)
