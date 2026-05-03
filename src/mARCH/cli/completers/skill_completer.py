"""Skill and command completer for mARCH CLI.

Provides autocomplete for / skill and command references using prompt_toolkit.
"""

import time
from typing import Iterable, List, Tuple

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from mARCH.skills.registry import SkillRegistry
from mARCH.core.slash_commands import SlashCommandType


class SkillCompleter(Completer):
    """Completer for / skill and command references."""

    def __init__(self, trigger_char: str = "/"):
        """Initialize skill completer.

        Args:
            trigger_char: Character that triggers skill completion
        """
        self.trigger_char = trigger_char
        self._skill_registry = SkillRegistry.get_instance()
        self._skills_cache: List[Tuple[str, str]] = []
        self._skills_cache_timestamp: float = 0
        self._skills_cache_ttl: float = 30  # Refresh every 30 seconds

    def _get_builtin_commands(self) -> List[Tuple[str, str]]:
        """Get built-in slash commands.

        Returns:
            List of (command_name, description) tuples
        """
        commands = [
            ("login", "Authenticate with GitHub"),
            ("logout", "Log out from GitHub"),
            ("model", "View or change the AI model"),
            ("lsp", "View Language Server Protocol configuration"),
            ("feedback", "Send feedback to GitHub"),
            ("experimental", "Toggle experimental mode"),
            ("status", "Show current status and settings"),
            ("setup", "Configure API keys and settings"),
            ("help", "Show help message"),
            ("skills", "List available skills"),
        ]
        return commands

    def _get_registered_skills(self) -> List[Tuple[str, str]]:
        """Get registered skills from registry (with caching).

        Returns:
            List of (skill_name, description) tuples
        """
        now = time.time()
        # Return cached skills if TTL not expired
        if self._skills_cache and (now - self._skills_cache_timestamp) < self._skills_cache_ttl:
            return self._skills_cache

        skills = []
        try:
            for skill in self._skill_registry.list_skills():
                skills.append((skill.name, skill.description or "No description"))
        except Exception:
            pass

        # Update cache
        self._skills_cache = skills
        self._skills_cache_timestamp = now
        return skills

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        """Get skill/command completions.

        Args:
            document: Current document
            complete_event: Completion event

        Yields:
            Completion objects for matching skills/commands
        """
        text = document.text_before_cursor

        # Check if / is at start or after whitespace
        trigger_pos = -1
        for i in range(len(text) - 1, -1, -1):
            if text[i] == self.trigger_char:
                # Valid trigger at start or after whitespace
                if i == 0 or text[i - 1].isspace():
                    trigger_pos = i
                    break

        if trigger_pos == -1:
            return

        # Extract query after /
        query = text[trigger_pos + 1 :].lower()

        # Don't complete if there's a space after query
        if " " in query:
            return

        # Collect all commands and skills
        all_items: List[Tuple[str, str, str]] = []  # (name, description, type)

        # Add built-in commands
        for name, desc in self._get_builtin_commands():
            if query in name.lower():
                all_items.append((name, desc, "command"))

        # Add registered skills
        for name, desc in self._get_registered_skills():
            if query in name.lower():
                all_items.append((name, desc, "skill"))

        # Sort by match quality
        def sort_key(item: Tuple[str, str, str]) -> Tuple[int, str]:
            name = item[0].lower()
            if name.startswith(query):
                return (0, name)  # Prefix match first
            return (1, name)  # Then alphabetical

        all_items.sort(key=sort_key)

        # Generate completions
        start_position = -(len(query) + 1)  # +1 for /

        for name, description, item_type in all_items:
            # Icon based on type
            icon = "⚡" if item_type == "skill" else "🔧"

            yield Completion(
                text=f"{name} ",  # Space after for args
                start_position=start_position,
                display=f"{icon} /{name}",
                display_meta=description[:50] + ("..." if len(description) > 50 else ""),
            )

    def is_active(self, document: Document) -> bool:
        """Check if skill completion should be active.

        Args:
            document: Current document

        Returns:
            True if / was typed at valid position
        """
        text = document.text_before_cursor

        # Find last /
        for i in range(len(text) - 1, -1, -1):
            if text[i] == self.trigger_char:
                # Valid if at start or after whitespace
                if i == 0 or text[i - 1].isspace():
                    # Check no space in query
                    query = text[i + 1 :]
                    return " " not in query
                break

        return False
