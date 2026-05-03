"""Plan mode detection and parsing for mARCH CLI.

Handles [[PLAN]] prefix detection and plan content extraction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mARCH.ui.tui_widgets.input_bar import InputMode

PLAN_MODE_SYSTEM_PROMPT = """
<plan_mode>
When user messages are prefixed with [[PLAN]], you handle them in "plan mode". In this mode:
1. If this is a new request or requirements are unclear, use the ask_user tool to confirm understanding and resolve ambiguity
2. Analyze the codebase to understand the current state
3. Create a structured implementation plan (or update the existing one if present)
4. Save the plan to: plan.md in the session workspace

The plan should include:
- A brief statement of the problem and proposed approach
- A list of todos (tracking is handled via SQL, not markdown checkboxes)
- Any notes or considerations

Guidelines:
- Use the **create** or **edit** tools to write plan.md in the session workspace.
- Do NOT ask for permission to create or update plan.md in the session workspace—it's designed for this purpose.
- After writing plan.md, provide a brief summary of the plan in your response. Include the key points so the user doesn't need to open the file separately.
- Do NOT include time or date estimates of any kind when generating a plan or timeline.
- Do NOT start implementing unless the user explicitly asks (e.g., "start", "get to work", "implement it").
  When they do, read plan.md first to check for any edits the user may have made.

Before finalizing a plan, use ask_user to confirm any assumptions about:
- Feature scope and boundaries (what's in/out)
- Behavioral choices (defaults, limits, error handling)
- Implementation approach when multiple valid options exist

After saving plan.md, reflect todos into the SQL database for tracking:
- INSERT todos into the `todos` table (id, title, description)
- INSERT dependencies into `todo_deps` (todo_id, depends_on)
- Use status values: 'pending', 'in_progress', 'done', 'blocked'
- Update todo status as work progresses

plan.md is the human-readable source of truth. SQL provides queryable structure for execution.
</plan_mode>
"""

AUTOPILOT_SYSTEM_PROMPT = (
    "You are running in non-interactive mode and have no way to communicate with "
    "the user. You must work on the task until it is completed. Do not stop to ask "
    "questions or request confirmation - make reasonable assumptions and proceed "
    "autonomously. Complete the entire task before finishing.\n"
)


def build_mode_system_prompt(base_prompt: str, mode: InputMode) -> str:
    """Return base_prompt augmented with the mode-specific system prompt section.

    Args:
        base_prompt: The existing system prompt content.
        mode: An InputMode enum value determining which section to inject.

    Returns:
        The augmented system prompt string.
    """
    from mARCH.ui.tui_widgets.input_bar import InputMode  # avoid circular import

    if mode == InputMode.PLAN:
        return base_prompt + "\n\n" + PLAN_MODE_SYSTEM_PROMPT.strip()
    if mode == InputMode.AUTOPILOT:
        return AUTOPILOT_SYSTEM_PROMPT.strip() + "\n\n" + base_prompt
    return base_prompt


class PlanModeDetector:
    """Detect and parse [[PLAN]] prefix in user input."""

    PLAN_PREFIX = "[[PLAN]]"

    @staticmethod
    def is_plan_request(user_input: str) -> bool:
        """Check if input starts with [[PLAN]] prefix.

        Args:
            user_input: User input string

        Returns:
            True if input starts with [[PLAN]], False otherwise
        """
        return user_input.strip().startswith(PlanModeDetector.PLAN_PREFIX)

    @staticmethod
    def extract_content(user_input: str) -> str:
        """Extract content after [[PLAN]] prefix.

        Args:
            user_input: User input string

        Returns:
            Content after [[PLAN]] prefix, or full input if no prefix
        """
        if PlanModeDetector.is_plan_request(user_input):
            content = user_input.replace(PlanModeDetector.PLAN_PREFIX, "", 1).strip()
            return content
        return user_input
