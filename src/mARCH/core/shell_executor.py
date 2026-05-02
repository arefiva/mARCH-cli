"""
Shell command execution with error handling and I/O control.

Provides ShellExecutor for executing shell commands with timeout, output capture,
and streaming capabilities.
"""

import asyncio
import shlex
import subprocess
import signal
import os
from dataclasses import dataclass
from typing import Callable, Awaitable, Optional, Union
from enum import Enum

from mARCH.core.stream_buffer import StreamBuffer, StreamMode


class CaptureMode(Enum):
    """Enumeration of output capture modes."""

    NONE = "none"
    STDOUT = "stdout"
    STDERR = "stderr"
    BOTH = "both"


class ShellType(Enum):
    """Enumeration of shell types."""

    SH = "sh"
    BASH = "bash"
    ZSH = "zsh"


@dataclass
class CommandOptions:
    """Options for command execution."""

    shell: ShellType = ShellType.BASH
    timeout: Optional[float] = None
    capture_mode: CaptureMode = CaptureMode.BOTH
    working_directory: Optional[str] = None
    environment: Optional[dict[str, str]] = None
    streaming: bool = False
    merge_stderr: bool = False


@dataclass
class CommandResult:
    """Result of a command execution."""

    return_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: str
    metadata: dict


class ShellExecutor:
    """
    Executes shell commands with controlled I/O and error handling.

    Supports timeout, output capture, and streaming callbacks.
    """

    def __init__(self) -> None:
        """Initialize the ShellExecutor."""
        self._running_processes: dict[int, asyncio.subprocess.Process] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def validate_command(command: str) -> bool:
        """
        Validate command syntax.

        Args:
            command: Command string to validate

        Returns:
            True if command appears valid, False otherwise
        """
        if not command or not isinstance(command, str):
            return False
        # Try to parse the command
        try:
            shlex.split(command)
            return True
        except ValueError:
            return False

    async def execute(
        self,
        command: str,
        options: Optional[CommandOptions] = None,
    ) -> CommandResult:
        """
        Execute a shell command and wait for completion.

        Args:
            command: Command string to execute
            options: CommandOptions for execution parameters

        Returns:
            CommandResult with return code, output, and timing

        Raises:
            ValueError: If command is invalid
            TimeoutError: If command exceeds timeout
            RuntimeError: If execution fails
        """
        if not self.validate_command(command):
            raise ValueError(f"Invalid command syntax: {command}")

        if options is None:
            options = CommandOptions()

        import time

        start_time = time.time()

        try:
            # Prepare subprocess arguments
            shell_cmd = f"{options.shell.value} -c"
            full_command = [options.shell.value, "-c", command]

            # Set environment
            env = None
            if options.environment:
                env = os.environ.copy()
                env.update(options.environment)

            # Determine stdout/stderr handling
            stdout_pipe = subprocess.PIPE if options.capture_mode != CaptureMode.NONE else None
            stderr_pipe = subprocess.PIPE if options.capture_mode != CaptureMode.NONE else None

            if options.merge_stderr or options.capture_mode == CaptureMode.BOTH:
                stderr_pipe = subprocess.STDOUT if stdout_pipe else None

            # Start the process
            proc = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=stdout_pipe,
                stderr=stderr_pipe,
                env=env,
                cwd=options.working_directory,
            )

            # Register process
            async with self._lock:
                self._running_processes[proc.pid] = proc

            try:
                # Wait for completion with timeout
                stdout_data, stderr_data = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=options.timeout,
                )

                return_code = proc.returncode
            except asyncio.TimeoutError:
                # Kill process on timeout
                proc.kill()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if graceful kill fails
                    os.kill(proc.pid, signal.SIGKILL)
                    await proc.wait()

                raise TimeoutError(f"Command exceeded timeout of {options.timeout}s: {command}")
            finally:
                # Unregister process
                async with self._lock:
                    if proc.pid in self._running_processes:
                        del self._running_processes[proc.pid]

            # Decode output
            stdout_str = (
                stdout_data.decode("utf-8", errors="replace") if stdout_data else ""
            )
            stderr_str = (
                stderr_data.decode("utf-8", errors="replace") if stderr_data else ""
            )

            execution_time = time.time() - start_time

            return CommandResult(
                return_code=return_code,
                stdout=stdout_str,
                stderr=stderr_str,
                execution_time=execution_time,
                command=command,
                metadata={"shell": options.shell.value},
            )

        except asyncio.TimeoutError as e:
            raise TimeoutError(str(e))
        except Exception as e:
            raise RuntimeError(f"Command execution failed: {str(e)}")

    async def execute_streaming(
        self,
        command: str,
        on_stdout: Optional[Callable[[str], Awaitable[None]]] = None,
        on_stderr: Optional[Callable[[str], Awaitable[None]]] = None,
        options: Optional[CommandOptions] = None,
    ) -> CommandResult:
        """
        Execute a command with streaming output callbacks.

        Args:
            command: Command string to execute
            on_stdout: Callback for stdout data
            on_stderr: Callback for stderr data
            options: CommandOptions for execution parameters

        Returns:
            CommandResult with aggregated output

        Raises:
            ValueError: If command is invalid
            TimeoutError: If command exceeds timeout
        """
        if not self.validate_command(command):
            raise ValueError(f"Invalid command syntax: {command}")

        if options is None:
            options = CommandOptions()

        import time

        start_time = time.time()

        try:
            # Start the process
            proc = await asyncio.create_subprocess_exec(
                options.shell.value,
                "-c",
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=options.working_directory,
            )

            # Register process
            async with self._lock:
                self._running_processes[proc.pid] = proc

            stdout_data = []
            stderr_data = []

            async def read_stream(
                stream,
                callback: Optional[Callable[[str], Awaitable[None]]],
                data_list: list,
            ) -> None:
                """Helper to read from stream and invoke callback."""
                while True:
                    try:
                        line = await asyncio.wait_for(
                            stream.readline(),
                            timeout=options.timeout if options.timeout else 300,
                        )
                        if not line:
                            break
                        text = line.decode("utf-8", errors="replace")
                        data_list.append(text)
                        if callback:
                            await callback(text)
                    except asyncio.TimeoutError:
                        break

            try:
                # Read streams concurrently
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(proc.stdout, on_stdout, stdout_data),
                        read_stream(proc.stderr, on_stderr, stderr_data),
                        return_exceptions=False,
                    ),
                    timeout=options.timeout,
                )

                return_code = await proc.wait()
            except asyncio.TimeoutError:
                proc.kill()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    os.kill(proc.pid, signal.SIGKILL)
                    await proc.wait()

                raise TimeoutError(f"Command exceeded timeout of {options.timeout}s: {command}")
            finally:
                # Unregister process
                async with self._lock:
                    if proc.pid in self._running_processes:
                        del self._running_processes[proc.pid]

            execution_time = time.time() - start_time

            return CommandResult(
                return_code=return_code,
                stdout="".join(stdout_data),
                stderr="".join(stderr_data),
                execution_time=execution_time,
                command=command,
                metadata={"shell": options.shell.value, "streaming": True},
            )

        except Exception as e:
            raise RuntimeError(f"Streaming command execution failed: {str(e)}")

    async def cancel_pending(self) -> None:
        """Cancel all pending processes."""
        async with self._lock:
            for pid, proc in list(self._running_processes.items()):
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
            self._running_processes.clear()

    async def terminate_process(self, pid: int, timeout: float = 5.0) -> bool:
        """
        Terminate a specific process.

        Args:
            pid: Process ID to terminate
            timeout: Timeout for graceful termination

        Returns:
            True if terminated successfully, False otherwise
        """
        async with self._lock:
            proc = self._running_processes.get(pid)
            if not proc:
                return False

            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=timeout)
                del self._running_processes[pid]
                return True
            except asyncio.TimeoutError:
                # Force kill
                try:
                    os.kill(pid, signal.SIGKILL)
                    await proc.wait()
                    del self._running_processes[pid]
                    return True
                except ProcessLookupError:
                    if pid in self._running_processes:
                        del self._running_processes[pid]
                    return True

    def get_running_processes(self) -> list[int]:
        """Get list of running process IDs."""
        return list(self._running_processes.keys())
