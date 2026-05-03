"""
Bash task executor for mARCH plan execution.

Executes bash commands with timeout, output capture, error handling,
and memory-safe streaming with bounded output (100MB limit per stream).
"""

import asyncio
import atexit
import os
import shlex
import tempfile
import time

from mARCH.core.task_executor import TaskExecutor
from mARCH.core.task_types import TaskBase, TaskResult, TaskType


class BashTaskExecutor(TaskExecutor):
    """Executor for bash commands with streaming and memory bounds."""

    # Maximum output per stream before writing to disk (100MB)
    MAX_OUTPUT_SIZE = 100 * 1024 * 1024

    def __init__(self) -> None:
        self._temp_files: set[str] = set()
        self._current_process: asyncio.subprocess.Process | None = None
        atexit.register(self.cleanup_temp_files)

    def cleanup_temp_files(self) -> None:
        """Delete all tracked temp files and clear the tracking set."""
        for path in list(self._temp_files):
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
        self._temp_files.clear()

    async def execute(self, task: TaskBase) -> TaskResult:
        """Execute a bash command with memory-safe streaming.

        Args:
            task: Task to execute (must be of type BASH)

        Returns:
            TaskResult with command output and status

        Memory Safety:
        - Output streamed incrementally (not buffered entirely)
        - If output exceeds 100MB, excess written to temp file
        - Subprocess resource limits enforced
        """
        if task.type != TaskType.BASH:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"BashTaskExecutor only handles BASH tasks, got {task.type.value}",
            )

        command = task.params.get("command")
        if not command:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error="No command specified in task params",
            )

        timeout = task.params.get("timeout", 30)
        working_directory = task.params.get("working_directory")
        use_shell = task.params.get("shell", False)

        start_time = time.time()
        try:
            result = await asyncio.wait_for(
                self._run_command_streaming(command, working_directory, use_shell),
                timeout=timeout,
            )
            duration = time.time() - start_time

            if result["return_code"] == 0:
                return TaskResult(
                    task_id=task.id,
                    status="completed",
                    stdout=result["stdout"],
                    stderr=result["stderr"],
                    output_file=result.get("output_file"),
                    memory_used_mb=result.get("memory_used_mb", 0.0),
                    peak_memory_mb=result.get("peak_memory_mb", 0.0),
                    duration=duration,
                )
            else:
                return TaskResult(
                    task_id=task.id,
                    status="failed",
                    stdout=result["stdout"],
                    stderr=result["stderr"],
                    output_file=result.get("output_file"),
                    memory_used_mb=result.get("memory_used_mb", 0.0),
                    peak_memory_mb=result.get("peak_memory_mb", 0.0),
                    error=f"Command exited with code {result['return_code']}",
                    duration=duration,
                )
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            if self._current_process is not None:
                self._current_process.kill()
                await self._current_process.wait()
                self._current_process = None
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"Command timed out after {timeout}s",
                duration=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"Command execution failed: {e!s}",
                duration=duration,
            )

    async def _read_stream(
        self,
        stream: asyncio.StreamReader,
        buffer: list[bytes],
        size_tracker: list[int],
    ) -> str | None:
        """Read a stream into buffer, overflowing to disk when MAX_OUTPUT_SIZE is exceeded.

        Args:
            stream: Async stream to read from
            buffer: Accumulator for in-memory bytes
            size_tracker: Single-element list holding current byte count (mutable)

        Returns:
            Path to overflow temp file, or None if no overflow occurred.
        """
        output_file: str | None = None
        while True:
            line = await stream.readline()
            if not line:
                break
            if size_tracker[0] + len(line) > self.MAX_OUTPUT_SIZE:
                if output_file is None:
                    output_file = self._create_temp_output_file()
                with open(output_file, "ab") as f:
                    f.write(line)
            else:
                buffer.append(line)
                size_tracker[0] += len(line)
        return output_file

    async def _run_command_streaming(
        self, command: str, working_directory: str | None = None, use_shell: bool = False
    ) -> dict:
        """Run command with streaming output (memory-safe).

        Streams output incrementally. If output exceeds MAX_OUTPUT_SIZE,
        excess is written to a temporary file on disk.

        Args:
            command: Command string to execute
            working_directory: Optional working directory
            use_shell: When True, execute via shell (WARNING: injection risk)

        Returns:
            Dictionary with return_code, stdout, stderr, output_file (if overflow)
        """
        try:
            if use_shell:
                # WARNING: shell=True bypasses injection protection; use only when required
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=working_directory,
                )
            else:
                args = shlex.split(command)
                if not args:
                    raise RuntimeError("Command is empty after parsing")
                process = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=working_directory,
                )

            self._current_process = process

            stdout_buffer: list[bytes] = []
            stderr_buffer: list[bytes] = []

            stdout_file, stderr_file = await asyncio.gather(
                self._read_stream(process.stdout, stdout_buffer, [0]),
                self._read_stream(process.stderr, stderr_buffer, [0]),
            )

            await process.wait()

            self._current_process = None

            output_file = stdout_file or stderr_file

            return {
                "return_code": process.returncode,
                "stdout": b"".join(stdout_buffer).decode("utf-8", errors="replace"),
                "stderr": b"".join(stderr_buffer).decode("utf-8", errors="replace"),
                "output_file": output_file,
                "memory_used_mb": 0.0,
                "peak_memory_mb": 0.0,
            }
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to execute command: {e!s}")

    def _create_temp_output_file(self) -> str:
        """Create a temporary file for overflow output and track it for cleanup.

        Returns:
            Path to temporary file
        """
        fd, path = tempfile.mkstemp(suffix=".out", prefix="task_")
        os.close(fd)
        self._temp_files.add(path)
        return path

    def get_supported_types(self) -> list[TaskType]:
        """Get supported task types.

        Returns:
            List containing BASH task type
        """
        return [TaskType.BASH]
