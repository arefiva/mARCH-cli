"""
Task executor framework for mARCH plan execution.

Provides abstract TaskExecutor base class and TaskExecutorRegistry for routing
tasks to appropriate executors based on task type.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Type
from mARCH.core.task_types import TaskBase, TaskResult, TaskType


class TaskExecutor(ABC):
    """Abstract base class for task executors."""

    @abstractmethod
    async def execute(self, task: TaskBase) -> TaskResult:
        """Execute a task.

        Args:
            task: Task to execute

        Returns:
            TaskResult with execution outcome
        """
        pass

    def get_supported_types(self) -> list[TaskType]:
        """Get task types supported by this executor.

        Returns:
            List of supported TaskType values
        """
        return []


class TaskExecutorRegistry:
    """Registry for task executors with routing support."""

    def __init__(self):
        """Initialize executor registry."""
        self._executors: Dict[TaskType, TaskExecutor] = {}

    def register(self, task_type: TaskType, executor: TaskExecutor) -> None:
        """Register an executor for a task type.

        Args:
            task_type: Task type to handle
            executor: Executor instance
        """
        self._executors[task_type] = executor

    def get_executor(self, task_type: TaskType) -> Optional[TaskExecutor]:
        """Get executor for task type.

        Args:
            task_type: Task type to look up

        Returns:
            Executor instance or None if not registered
        """
        return self._executors.get(task_type)

    def is_registered(self, task_type: TaskType) -> bool:
        """Check if executor is registered for task type.

        Args:
            task_type: Task type to check

        Returns:
            True if registered, False otherwise
        """
        return task_type in self._executors

    def get_all_supported_types(self) -> list[TaskType]:
        """Get all supported task types.

        Returns:
            List of all registered task types
        """
        return list(self._executors.keys())


def get_default_registry() -> TaskExecutorRegistry:
    """Get default executor registry with all executors registered.

    Returns:
        Registry with all default executors registered
    """
    from mARCH.tasks.bash_executor import BashTaskExecutor
    from mARCH.tasks.file_executor import FileTaskExecutor
    from mARCH.tasks.analysis_executor import AnalysisTaskExecutor

    registry = TaskExecutorRegistry()
    registry.register(TaskType.BASH, BashTaskExecutor())
    registry.register(TaskType.FILE_READ, FileTaskExecutor())
    registry.register(TaskType.FILE_CREATE, FileTaskExecutor())
    registry.register(TaskType.FILE_EDIT, FileTaskExecutor())
    registry.register(TaskType.ANALYSIS, AnalysisTaskExecutor())

    return registry
