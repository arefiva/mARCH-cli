"""Autopilot executor for executing plans with auto-approval.

Executes plan tasks based on execution mode (interactive vs autopilot).
"""

from typing import Any, Dict

from rich.console import Console
from rich.prompt import Confirm

from mARCH.core.execution_mode import ExecutionMode

console = Console()


class AutopilotExecutor:
    """Execute plan tasks with mode-based approval."""

    @staticmethod
    async def execute_plan(plan: Dict[str, Any], mode: ExecutionMode) -> Dict[str, Any]:
        """Execute plan tasks according to mode.

        Args:
            plan: Plan structure with tasks
            mode: ExecutionMode (INTERACTIVE or AUTOPILOT)

        Returns:
            Execution results
        """
        results = {"status": "complete", "mode": mode.value, "tasks": []}

        tasks = plan.get("tasks", [])
        for i, task in enumerate(tasks, 1):
            console.print(f"\n[bold]Task {i}/{len(tasks)}:[/bold] {task}")

            # In interactive mode, ask for confirmation
            if mode == ExecutionMode.INTERACTIVE:
                if not Confirm.ask("Proceed?", default=True):
                    results["status"] = "cancelled"
                    return results

            # Execute task (placeholder - in real implementation, would run actual task)
            result = AutopilotExecutor._execute_task(task)

            results["tasks"].append(
                {"task": task, "status": "completed", "result": result}
            )

            console.print("[green]✓ Task completed[/green]")

        return results

    @staticmethod
    def _execute_task(task: str) -> Dict[str, Any]:
        """Execute a single task.

        Args:
            task: Task description

        Returns:
            Task execution result
        """
        # Placeholder - in real implementation would execute actual task
        return {"status": "completed", "output": f"Executed: {task}"}

    @staticmethod
    def should_auto_approve(mode: ExecutionMode) -> bool:
        """Check if mode requires auto-approval.

        Args:
            mode: ExecutionMode to check

        Returns:
            True if auto-approval required, False otherwise
        """
        return mode in (ExecutionMode.AUTOPILOT, ExecutionMode.AUTOPILOT_FLEET)
