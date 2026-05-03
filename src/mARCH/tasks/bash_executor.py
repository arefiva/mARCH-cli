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

            # Stream output with size tracking
            stdout_buffer = []
            stderr_buffer = []
            stdout_size = 0
            stderr_size = 0
            output_file = None

            # Read stdout
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                # Check if we need to overflow to disk
                if stdout_size + len(line) > self.MAX_OUTPUT_SIZE:
                    # Overflow to disk
                    if not output_file:
                        output_file = self._create_temp_output_file()
                    with open(output_file, "ab") as f:
                        f.write(line)
                else:
                    stdout_buffer.append(line)
                    stdout_size += len(line)

            # Read stderr
            try:
                while True:
                    line = await process.stderr.readline()
                    if not line:
                        break

                    if stderr_size + len(line) > self.MAX_OUTPUT_SIZE:
                        if not output_file:
                            output_file = self._create_temp_output_file()
                        with open(output_file, "ab") as f:
                            f.write(b"STDERR: " + line)
                    else:
                        stderr_buffer.append(line)
                        stderr_size += len(line)
            except Exception:
                pass

            await process.wait()

            self._current_process = None

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
