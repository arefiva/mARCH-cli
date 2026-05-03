"""
Task types and structures for mARCH plan execution.

Defines Task and TaskResult dataclasses, task type constants, and factory methods
for creating different types of tasks (bash, file operations, analysis).
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime


class TaskType(Enum):
    """Enumeration of supported task types."""

    BASH = "bash"
    FILE_READ = "file_read"
    FILE_CREATE = "file_create"
    FILE_EDIT = "file_edit"
    ANALYSIS = "analysis"
    RESEARCH = "research"


@dataclass
class TaskBase:
    """Base task data structure."""

    id: str
    description: str
    type: TaskType
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "type": self.type.value,
            "params": self.params,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TaskBase":
        """Create task from dictionary."""
        task_type = TaskType(data.get("type", TaskType.BASH.value))
        return TaskBase(
            id=data.get("id", ""),
            description=data.get("description", ""),
            type=task_type,
            params=data.get("params", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TaskResult:
    """Result of task execution with memory metrics."""

    task_id: str
    status: str  # "completed", "failed", "skipped", "memory_exceeded"
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    # Memory metrics for tracking resource usage
    memory_used_mb: float = 0.0
    peak_memory_mb: float = 0.0
    output_file: Optional[str] = None  # Pointer to full output if truncated

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TaskResult":
        """Create result from dictionary."""
        return TaskResult(**data)


# Task factory methods
def create_bash_task(
    task_id: str,
    description: str,
    command: str,
    timeout: Optional[float] = None,
    working_directory: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> TaskBase:
    """Create a bash task.

    Args:
        task_id: Unique task identifier
        description: Human-readable task description
        command: Bash command to execute
        timeout: Command timeout in seconds (default 30)
        working_directory: Working directory for command
        metadata: Additional metadata

    Returns:
        TaskBase instance for bash execution
    """
    return TaskBase(
        id=task_id,
        description=description,
        type=TaskType.BASH,
        params={
            "command": command,
            "timeout": timeout or 30,
            "working_directory": working_directory,
        },
        metadata=metadata or {},
    )


def create_file_read_task(
    task_id: str,
    description: str,
    file_path: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> TaskBase:
    """Create a file read task.

    Args:
        task_id: Unique task identifier
        description: Human-readable task description
        file_path: Path to file to read
        metadata: Additional metadata

    Returns:
        TaskBase instance for file read
    """
    return TaskBase(
        id=task_id,
        description=description,
        type=TaskType.FILE_READ,
        params={"file_path": file_path},
        metadata=metadata or {},
    )


def create_file_create_task(
    task_id: str,
    description: str,
    file_path: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> TaskBase:
    """Create a file create task.

    Args:
        task_id: Unique task identifier
        description: Human-readable task description
        file_path: Path where to create file
        content: File content to write
        metadata: Additional metadata

    Returns:
        TaskBase instance for file creation
    """
    return TaskBase(
        id=task_id,
        description=description,
        type=TaskType.FILE_CREATE,
        params={"file_path": file_path, "content": content},
        metadata=metadata or {},
    )


def create_file_edit_task(
    task_id: str,
    description: str,
    file_path: str,
    old_str: str,
    new_str: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> TaskBase:
    """Create a file edit task.

    Args:
        task_id: Unique task identifier
        description: Human-readable task description
        file_path: Path to file to edit
        old_str: Old text to replace
        new_str: New text to insert
        metadata: Additional metadata

    Returns:
        TaskBase instance for file editing
    """
    return TaskBase(
        id=task_id,
        description=description,
        type=TaskType.FILE_EDIT,
        params={"file_path": file_path, "old_str": old_str, "new_str": new_str},
        metadata=metadata or {},
    )


def create_analysis_task(
    task_id: str,
    description: str,
    analysis_type: str,
    target: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> TaskBase:
    """Create an analysis task.

    Args:
        task_id: Unique task identifier
        description: Human-readable task description
        analysis_type: Type of analysis to run
        target: Target file or pattern for analysis
        metadata: Additional metadata

    Returns:
        TaskBase instance for analysis
    """
    return TaskBase(
        id=task_id,
        description=description,
        type=TaskType.ANALYSIS,
        params={"analysis_type": analysis_type, "target": target},
        metadata=metadata or {},
    )
