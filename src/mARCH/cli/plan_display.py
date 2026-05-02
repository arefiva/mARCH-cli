"""Plan display and approval UI for mARCH CLI.

Displays structured plans and collects user action selection.
"""

from typing import Any, Dict, Literal

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

ActionChoice = Literal["exit_only", "interactive", "autopilot", "autopilot_fleet"]


class PlanApprovalUI:
    """Display plan and get user approval action."""

    @staticmethod
    def display_plan(plan: Dict[str, Any]) -> None:
        """Display structured plan using Rich formatting.

        Args:
            plan: Plan structure with summary, approach, tasks, etc.
        """
        # Display summary in a panel
        console.print()
        console.print(
            Panel.fit(
                plan.get("summary", "Plan"),
                title="📋 Plan Summary",
                border_style="cyan",
            )
        )

        # Display approach
        console.print("\n[bold cyan]Approach:[/bold cyan]")
        console.print(plan.get("approach", ""))

        # Display tasks
        tasks = plan.get("tasks", [])
        if tasks:
            console.print("\n[bold cyan]Tasks:[/bold cyan]")
            for i, task in enumerate(tasks, 1):
                console.print(f"  {i}. {task}")

        # Display estimated effort
        console.print("\n[bold cyan]Estimated Effort:[/bold cyan]")
        console.print(f"  {plan.get('estimated_effort', 'Unknown')}")

        # Display success criteria
        criteria = plan.get("success_criteria", [])
        if criteria:
            console.print("\n[bold cyan]Success Criteria:[/bold cyan]")
            for criterion in criteria:
                console.print(f"  ✓ {criterion}")

    @staticmethod
    def get_approval() -> ActionChoice:
        """Display action choices and get user selection.

        Returns:
            Selected action: "exit_only", "interactive", "autopilot", or "autopilot_fleet"
        """
        console.print()
        console.print("[bold cyan]Approve & Execute:[/bold cyan]")
        console.print("  [cyan]e[/cyan]  [dim]exit_only[/dim] - Exit without implementing")
        console.print("  [cyan]i[/cyan]  [dim]interactive[/dim] - Confirm each step")
        console.print("  [cyan]a[/cyan]  [dim]autopilot[/dim] - Auto-execute without prompts")
        console.print(
            "  [cyan]f[/cyan]  [dim]autopilot_fleet[/dim] - Parallel execution"
        )
        console.print()

        choices = {
            "e": "exit_only",
            "i": "interactive",
            "a": "autopilot",
            "f": "autopilot_fleet",
        }

        choice = Prompt.ask(
            "Select action", choices=list(choices.keys()), default="i"
        )
        action = choices.get(choice, "exit_only")

        return action
