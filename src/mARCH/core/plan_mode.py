"""Plan mode detection and parsing for mARCH CLI.

Handles [[PLAN]] prefix detection and plan content extraction.
"""


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
