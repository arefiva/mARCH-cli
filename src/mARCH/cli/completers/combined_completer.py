"""Combined completer for mARCH CLI.

Routes completion requests to appropriate completer based on trigger character.
"""

from typing import Iterable

from prompt_toolkit.completion import Completer, Completion, merge_completers
from prompt_toolkit.document import Document

from mARCH.cli.completers.file_completer import FileCompleter
from mARCH.cli.completers.skill_completer import SkillCompleter


class CombinedCompleter(Completer):
    """Combined completer that routes to file or skill completer."""

    def __init__(self):
        """Initialize combined completer with sub-completers."""
        self.file_completer = FileCompleter(trigger_char="@")
        self.skill_completer = SkillCompleter(trigger_char="/")

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        """Get completions from appropriate sub-completer.

        Args:
            document: Current document
            complete_event: Completion event

        Yields:
            Completion objects from active completer
        """
        # Check which completer is active
        if self.file_completer.is_active(document):
            yield from self.file_completer.get_completions(document, complete_event)
        elif self.skill_completer.is_active(document):
            yield from self.skill_completer.get_completions(document, complete_event)

    def is_active(self, document: Document) -> bool:
        """Check if any completer is active.

        Args:
            document: Current document

        Returns:
            True if any completer should show completions
        """
        return (
            self.file_completer.is_active(document)
            or self.skill_completer.is_active(document)
        )
