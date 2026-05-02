"""
Process lifecycle management and tracking.

Provides ProcessManager for registering, monitoring, and managing process lifecycles.
"""

import asyncio
import os
import psutil
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from datetime import datetime


class ProcessStatus(Enum):
    """Process status enumeration."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ResourceUsage:
    """Resource usage statistics for a process."""

    cpu_percent: float = 0.0
    memory_bytes: int = 0
    memory_percent: float = 0.0
    num_threads: int = 0


@dataclass
class ProcessInfo:
    """Information about a managed process."""

    pid: int
    status: ProcessStatus = ProcessStatus.RUNNING
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    return_code: Optional[int] = None
    metadata: dict = field(default_factory=dict)
    resource_usage: Optional[ResourceUsage] = None

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        end = self.end_time or datetime.now()
        delta = end - self.start_time
        return delta.total_seconds()


class ProcessManager:
    """
    Singleton process manager for tracking and managing processes.

    Maintains a registry of active processes and handles cleanup.
    """

    _instance: Optional["ProcessManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls) -> "ProcessManager":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the ProcessManager."""
        if self._initialized:
            return

        self._processes: dict[int, ProcessInfo] = {}
        self._process_lock = asyncio.Lock()
        self._monitoring_tasks: dict[int, asyncio.Task] = {}
        self._initialized = True

    async def register_process(
        self,
        pid: int,
        metadata: Optional[dict] = None,
    ) -> ProcessInfo:
        """
        Register a process with the manager.

        Args:
            pid: Process ID
            metadata: Optional metadata about the process

        Returns:
            ProcessInfo instance
        """
        async with self._process_lock:
            if pid in self._processes:
                return self._processes[pid]

            process_info = ProcessInfo(
                pid=pid,
                metadata=metadata or {},
            )
            self._processes[pid] = process_info

            # Start monitoring task
            self._monitoring_tasks[pid] = asyncio.create_task(self._monitor_process(pid))

            return process_info

    async def _monitor_process(self, pid: int) -> None:
        """
        Monitor a process and update its status.

        Args:
            pid: Process ID to monitor
        """
        try:
            while pid in self._processes:
                process_info = self._processes[pid]

                if process_info.status == ProcessStatus.COMPLETED:
                    break

                try:
                    # Check if process still exists
                    proc = psutil.Process(pid)

                    if proc.is_running():
                        # Update resource usage
                        try:
                            process_info.resource_usage = ResourceUsage(
                                cpu_percent=proc.cpu_percent(interval=0.1),
                                memory_bytes=proc.memory_info().rss,
                                memory_percent=proc.memory_percent(),
                                num_threads=proc.num_threads(),
                            )
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    else:
                        # Process has completed
                        try:
                            return_code = proc.wait(timeout=1)
                        except psutil.NoSuchProcess:
                            return_code = -1

                        async with self._process_lock:
                            if pid in self._processes:
                                process_info.status = ProcessStatus.COMPLETED
                                process_info.return_code = return_code
                                process_info.end_time = datetime.now()
                        break
                except psutil.NoSuchProcess:
                    # Process no longer exists
                    async with self._process_lock:
                        if pid in self._processes:
                            process_info.status = ProcessStatus.COMPLETED
                            process_info.end_time = datetime.now()
                    break

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass
        finally:
            # Clean up monitoring task
            if pid in self._monitoring_tasks:
                del self._monitoring_tasks[pid]

    async def wait_for_process(self, pid: int, timeout: Optional[float] = None) -> ProcessInfo:
        """
        Wait for a process to complete.

        Args:
            pid: Process ID to wait for
            timeout: Optional timeout in seconds

        Returns:
            ProcessInfo with final status

        Raises:
            TimeoutError: If timeout is exceeded
            ValueError: If process not found
        """
        if pid not in self._processes:
            raise ValueError(f"Process {pid} not registered")

        process_info = self._processes[pid]

        # Wait until process completes
        start_time = asyncio.get_event_loop().time()

        while process_info.status == ProcessStatus.RUNNING:
            if timeout:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(f"Timeout waiting for process {pid}")

            await asyncio.sleep(0.5)

        return process_info

    def get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """
        Get information about a process.

        Args:
            pid: Process ID

        Returns:
            ProcessInfo or None if not found
        """
        return self._processes.get(pid)

    async def terminate_process(
        self,
        pid: int,
        timeout: float = 5.0,
    ) -> bool:
        """
        Terminate a process gracefully.

        Args:
            pid: Process ID to terminate
            timeout: Timeout for graceful termination

        Returns:
            True if terminated successfully, False otherwise
        """
        if pid not in self._processes:
            return False

        try:
            proc = psutil.Process(pid)

            # Try graceful termination
            proc.terminate()

            try:
                proc.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                # Force kill
                proc.kill()
                proc.wait()

            # Update status
            async with self._process_lock:
                if pid in self._processes:
                    process_info = self._processes[pid]
                    process_info.status = ProcessStatus.CANCELLED
                    process_info.end_time = datetime.now()

            return True
        except psutil.NoSuchProcess:
            # Process doesn't exist
            async with self._process_lock:
                if pid in self._processes:
                    self._processes[pid].status = ProcessStatus.COMPLETED
                    self._processes[pid].end_time = datetime.now()
            return True

    async def cleanup_all(self) -> None:
        """
        Cleanup all managed processes and cancel monitoring.

        Terminates running processes gracefully.
        """
        async with self._process_lock:
            # Terminate all running processes
            for pid in list(self._processes.keys()):
                process_info = self._processes[pid]
                if process_info.status == ProcessStatus.RUNNING:
                    try:
                        await self.terminate_process(pid, timeout=2.0)
                    except Exception:
                        pass

            # Cancel monitoring tasks
            for task in self._monitoring_tasks.values():
                task.cancel()

            self._monitoring_tasks.clear()
            self._processes.clear()

    def get_active_processes(self) -> list[ProcessInfo]:
        """
        Get all active processes.

        Returns:
            List of ProcessInfo for running processes
        """
        return [
            info for info in self._processes.values()
            if info.status == ProcessStatus.RUNNING
        ]

    def get_all_processes(self) -> list[ProcessInfo]:
        """
        Get all managed processes.

        Returns:
            List of all ProcessInfo instances
        """
        return list(self._processes.values())

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        await self.cleanup_all()

    @classmethod
    async def get_instance(cls) -> "ProcessManager":
        """Get or create the singleton instance."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
