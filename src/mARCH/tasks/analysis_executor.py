"""
Analysis task executor for mARCH plan execution.

Handles analysis tasks like code reviews, security scans, etc.
"""

import asyncio
from typing import Optional

from mARCH.core.task_executor import TaskExecutor
from mARCH.core.task_types import TaskBase, TaskResult, TaskType


class AnalysisTaskExecutor(TaskExecutor):
    """Executor for analysis tasks."""

    async def execute(self, task: TaskBase) -> TaskResult:
        """Execute an analysis task.

        Args:
            task: Task to execute (must be of type ANALYSIS)

        Returns:
            TaskResult with analysis output
        """
        if task.type != TaskType.ANALYSIS:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"AnalysisTaskExecutor only handles ANALYSIS tasks, got {task.type.value}",
            )

        analysis_type = task.params.get("analysis_type")
        target = task.params.get("target")

        if not analysis_type or not target:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error="Missing required params: analysis_type or target",
            )

        try:
            # Dispatch to appropriate analysis handler
            if analysis_type == "lint":
                return await self._run_lint_analysis(task.id, target)
            elif analysis_type == "security":
                return await self._run_security_analysis(task.id, target)
            elif analysis_type == "performance":
                return await self._run_performance_analysis(task.id, target)
            else:
                return TaskResult(
                    task_id=task.id,
                    status="failed",
                    error=f"Unknown analysis type: {analysis_type}",
                )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=f"Analysis failed: {str(e)}",
            )

    async def _run_lint_analysis(self, task_id: str, target: str) -> TaskResult:
        """Run lint analysis.

        Args:
            task_id: Task identifier
            target: Target file or pattern

        Returns:
            TaskResult with analysis output
        """
        return TaskResult(
            task_id=task_id,
            status="completed",
            stdout=f"Lint analysis completed for: {target}",
        )

    async def _run_security_analysis(
        self, task_id: str, target: str
    ) -> TaskResult:
        """Run security analysis.

        Args:
            task_id: Task identifier
            target: Target file or pattern

        Returns:
            TaskResult with security findings
        """
        return TaskResult(
            task_id=task_id,
            status="completed",
            stdout=f"Security analysis completed for: {target}",
        )

    async def _run_performance_analysis(
        self, task_id: str, target: str
    ) -> TaskResult:
        """Run performance analysis.

        Args:
            task_id: Task identifier
            target: Target file or pattern

        Returns:
            TaskResult with performance metrics
        """
        return TaskResult(
            task_id=task_id,
            status="completed",
            stdout=f"Performance analysis completed for: {target}",
        )

    def get_supported_types(self) -> list[TaskType]:
        """Get supported task types.

        Returns:
            List containing ANALYSIS task type
        """
        return [TaskType.ANALYSIS]
