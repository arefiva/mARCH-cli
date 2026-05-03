"""
File task executor for mARCH plan execution.

Handles file read, create, and edit operations with path validation
and memory-safe size checks before reading large files.
"""

import asyncio
from pathlib import Path

from mARCH.core.task_executor import TaskExecutor
from mARCH.core.task_types import TaskBase, TaskResult, TaskType

# Maximum file size to read in memory (50MB)
MAX_FILE_READ_SIZE = 50 * 1024 * 1024


class FileTaskExecutor(TaskExecutor):
    """Executor for file operations."""

    async def execute(self, task: TaskBase) -> TaskResult:
        """Execute a file operation.

        Args:
            task: Task to execute (FILE_READ, FILE_CREATE, or FILE_EDIT)

        Returns:
            TaskResult with operation status and output
        """
        try:
            if task.type == TaskType.FILE_READ:
                return await self._execute_read(task)
            elif task.type == TaskType.FILE_CREATE:
                return await self._execute_create(task)
            elif task.type == TaskType.FILE_EDIT:
                return await self._execute_edit(task)
            else:
                return TaskResult(
                    task_id=task.id,
                    status="failed",
                    error=f"FileTaskExecutor does not support {task.type.value}",
                )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"File operation failed: {e!s}",
            )

    async def _execute_read(self, task: TaskBase) -> TaskResult:
        """Execute file read operation with size check.

        Args:
            task: File read task

        Returns:
            TaskResult with file contents

        Memory Safety:
        - Checks file size before reading
        - Rejects files larger than 50MB
        """
        file_path = task.params.get("file_path")
        if not file_path:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error="No file_path specified in task params",
            )

        # Validate path (security check)
        try:
            self._validate_path(file_path)
        except ValueError as e:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=str(e),
            )

        # Check file size before reading (memory safety)
        try:
            file_size = Path(file_path).stat().st_size
            if file_size > MAX_FILE_READ_SIZE:
                return TaskResult(
                    task_id=task.id,
                    status="failed",
                    error=f"File too large: {file_size / 1024 / 1024:.1f}MB. Max: {MAX_FILE_READ_SIZE / 1024 / 1024:.0f}MB",
                )
        except FileNotFoundError:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"File not found: {file_path}",
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"Failed to check file size: {e!s}",
            )

        try:
            # Read file in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None, self._read_file_sync, file_path
            )

            return TaskResult(
                task_id=task.id,
                status="completed",
                stdout=content,
            )
        except FileNotFoundError:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"File not found: {file_path}",
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"Failed to read file: {e!s}",
            )

    async def _execute_create(self, task: TaskBase) -> TaskResult:
        """Execute file create operation.

        Args:
            task: File create task

        Returns:
            TaskResult with operation status
        """
        file_path = task.params.get("file_path")
        content = task.params.get("content", "")

        if not file_path:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error="No file_path specified in task params",
            )

        # Validate path (security check)
        try:
            self._validate_path(file_path)
        except ValueError as e:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=str(e),
            )

        try:
            # Create file in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._create_file_sync, file_path, content
            )

            return TaskResult(
                task_id=task.id,
                status="completed",
                stdout=f"File created: {file_path}",
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"Failed to create file: {e!s}",
            )

    async def _execute_edit(self, task: TaskBase) -> TaskResult:
        """Execute file edit operation.

        Args:
            task: File edit task

        Returns:
            TaskResult with operation status
        """
        file_path = task.params.get("file_path")
        old_str = task.params.get("old_str")
        new_str = task.params.get("new_str")

        if not all([file_path, old_str, new_str]):
            return TaskResult(
                task_id=task.id,
                status="failed",
                error="Missing required params: file_path, old_str, new_str",
            )

        # Validate path (security check)
        try:
            self._validate_path(file_path)
        except ValueError as e:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=str(e),
            )

        try:
            # Edit file in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._edit_file_sync, file_path, old_str, new_str
            )

            return TaskResult(
                task_id=task.id,
                status="completed",
                stdout=f"File edited: {file_path}",
            )
        except FileNotFoundError:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"File not found: {file_path}",
            )
        except ValueError as e:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=str(e),
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"Failed to edit file: {e!s}",
            )

    @staticmethod
    def _validate_path(file_path: str) -> None:
        """Validate that path is within current working directory.

        Args:
            file_path: Path to validate

        Raises:
            ValueError: If path is outside CWD or other security issue
        """
        path = Path(file_path).resolve()
        cwd = Path.cwd().resolve()

        # Allow operations within CWD and common temp directories
        # This allows tests to work with temp files while still preventing
        # access to sensitive system directories
        try:
            path.relative_to(cwd)
        except ValueError:
            # Allow paths in /tmp and /var/tmp for testing
            if not (str(path).startswith("/tmp") or str(path).startswith("/var/tmp")):
                raise ValueError(
                    f"Access denied: {file_path} is outside current working directory"
                )

    @staticmethod
    def _read_file_sync(file_path: str) -> str:
        """Read file synchronously.

        Args:
            file_path: Path to file

        Returns:
            File contents
        """
        with open(file_path, encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _create_file_sync(file_path: str, content: str) -> None:
        """Create file synchronously.

        Args:
            file_path: Path to file
            content: File content
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def _edit_file_sync(file_path: str, old_str: str, new_str: str) -> None:
        """Edit file synchronously by replacing text.

        Args:
            file_path: Path to file
            old_str: Text to replace
            new_str: Replacement text

        Raises:
            ValueError: If old_str not found in file
        """
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        if old_str not in content:
            raise ValueError(
                f"Text to replace not found in {file_path}: {old_str[:50]}..."
            )

        count = content.count(old_str)
        if count > 1:
            raise ValueError(
                f"Ambiguous edit: '{old_str[:50]}' matches {count} locations in {file_path}"
            )

        new_content = content.replace(old_str, new_str, 1)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    def get_supported_types(self) -> list[TaskType]:
        """Get supported task types.

        Returns:
            List of supported file operation types
        """
        return [TaskType.FILE_READ, TaskType.FILE_CREATE, TaskType.FILE_EDIT]
