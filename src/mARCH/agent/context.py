"""Agent context management.

Rich context capturing file, git, conversation, and learned patterns.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Represents a learned pattern."""
    pattern_id: str
    pattern_type: str  # error_fix, optimization, etc.
    condition: str
    solution: str
    success_rate: float = 0.0
    last_used: datetime = field(default_factory=datetime.utcnow)
    tag: str = ""


@dataclass
class ConversationContext:
    """Context from recent conversation."""
    recent_messages: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    entities: Dict[str, List[str]] = field(default_factory=dict)
    summary: str = ""
    turn_count: int = 0

    def add_message(self, message: str) -> None:
        """Add a message to recent history."""
        self.recent_messages.append(message)
        # Keep only last 20 messages
        if len(self.recent_messages) > 20:
            self.recent_messages = self.recent_messages[-20:]
        self.turn_count += 1


@dataclass
class AgentContext:
    """Rich context for agent execution."""
    agent_id: str = ""
    current_file: Optional[str] = None
    current_directory: str = os.getcwd()
    language: Optional[str] = None
    project_type: Optional[str] = None
    git_branch: Optional[str] = None
    git_repository: Optional[str] = None
    git_status: Optional[Dict[str, Any]] = None
    conversation_context: ConversationContext = field(default_factory=ConversationContext)
    learned_patterns: List[Pattern] = field(default_factory=list)
    custom_context: Dict[str, Any] = field(default_factory=dict)
    environment_snapshot: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def update_file_context(self, filepath: str, language: str = None) -> None:
        """Update file context."""
        self.current_file = filepath
        self.current_directory = os.path.dirname(filepath) or os.getcwd()
        if language:
            self.language = language

    def update_git_context(
        self,
        repository: str,
        branch: str,
        status: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update git context."""
        self.git_repository = repository
        self.git_branch = branch
        self.git_status = status or {}

    def add_pattern(self, pattern: Pattern) -> None:
        """Add a learned pattern."""
        self.learned_patterns.append(pattern)

    def get_patterns_by_type(self, pattern_type: str) -> List[Pattern]:
        """Get patterns by type."""
        return [p for p in self.learned_patterns if p.pattern_type == pattern_type]

    def update_custom_context(self, updates: Dict[str, Any]) -> None:
        """Update custom context."""
        self.custom_context.update(updates)

    def capture_environment_snapshot(self) -> None:
        """Capture current environment variables."""
        relevant_vars = [
            "PATH",
            "PYTHONPATH",
            "HOME",
            "USER",
            "PWD",
            "LANG",
            "SHELL",
        ]
        for var in relevant_vars:
            if var in os.environ:
                self.environment_snapshot[var] = os.environ[var]

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "agent_id": self.agent_id,
            "current_file": self.current_file,
            "current_directory": self.current_directory,
            "language": self.language,
            "project_type": self.project_type,
            "git_branch": self.git_branch,
            "git_repository": self.git_repository,
            "git_status": self.git_status,
            "conversation_context": {
                "recent_messages": self.conversation_context.recent_messages,
                "topics": self.conversation_context.topics,
                "entities": self.conversation_context.entities,
                "summary": self.conversation_context.summary,
                "turn_count": self.conversation_context.turn_count,
            },
            "learned_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "pattern_type": p.pattern_type,
                    "condition": p.condition,
                    "solution": p.solution,
                    "success_rate": p.success_rate,
                    "tag": p.tag,
                }
                for p in self.learned_patterns
            ],
            "custom_context": self.custom_context,
            "environment_snapshot": self.environment_snapshot,
            "timestamp": self.timestamp.isoformat(),
        }


class ContextManager:
    """Manages agent context lifecycle."""

    @staticmethod
    async def capture_context(agent_id: str = "") -> AgentContext:
        """Capture current context.

        Args:
            agent_id: Agent identifier

        Returns:
            Captured AgentContext
        """
        context = AgentContext(agent_id=agent_id)
        context.capture_environment_snapshot()
        logger.debug(f"Captured context for agent {agent_id}")
        return context

    @staticmethod
    async def inherit_context(
        parent_context: AgentContext,
        child_agent_id: str,
        inherit_conversation: bool = True,
        inherit_patterns: bool = True,
    ) -> AgentContext:
        """Create child context inheriting from parent.

        Args:
            parent_context: Parent agent context
            child_agent_id: ID for child agent
            inherit_conversation: Whether to inherit conversation
            inherit_patterns: Whether to inherit patterns

        Returns:
            New AgentContext for child
        """
        child_context = AgentContext(agent_id=child_agent_id)

        # Inherit file and directory context
        child_context.current_file = parent_context.current_file
        child_context.current_directory = parent_context.current_directory
        child_context.language = parent_context.language
        child_context.project_type = parent_context.project_type

        # Inherit git context
        child_context.git_branch = parent_context.git_branch
        child_context.git_repository = parent_context.git_repository
        child_context.git_status = parent_context.git_status

        # Optionally inherit conversation
        if inherit_conversation:
            child_context.conversation_context = parent_context.conversation_context

        # Optionally inherit patterns
        if inherit_patterns:
            child_context.learned_patterns = parent_context.learned_patterns.copy()

        # Inherit environment
        child_context.environment_snapshot = parent_context.environment_snapshot.copy()

        logger.debug(
            f"Created child context {child_agent_id} inheriting from {parent_context.agent_id}"
        )
        return child_context

    @staticmethod
    async def merge_contexts(*contexts: AgentContext) -> AgentContext:
        """Merge multiple contexts.

        Args:
            contexts: Contexts to merge

        Returns:
            Merged AgentContext
        """
        if not contexts:
            return AgentContext()

        merged = AgentContext()

        # Use first context as base
        merged.current_file = contexts[0].current_file
        merged.current_directory = contexts[0].current_directory
        merged.language = contexts[0].language

        # Merge all patterns
        for ctx in contexts:
            for pattern in ctx.learned_patterns:
                if pattern not in merged.learned_patterns:
                    merged.learned_patterns.append(pattern)

        # Merge custom context
        for ctx in contexts:
            merged.custom_context.update(ctx.custom_context)

        logger.debug(f"Merged {len(contexts)} contexts")
        return merged

    @staticmethod
    async def save_context_snapshot(context: AgentContext) -> Dict[str, Any]:
        """Save context snapshot.

        Args:
            context: Context to snapshot

        Returns:
            Snapshot dictionary
        """
        snapshot = context.to_dict()
        logger.debug(f"Saved context snapshot for {context.agent_id}")
        return snapshot

    @staticmethod
    async def apply_context(context: AgentContext) -> bool:
        """Apply context to current environment.

        Args:
            context: Context to apply

        Returns:
            True if successful
        """
        try:
            # Change directory
            if context.current_directory:
                os.chdir(context.current_directory)

            # Set environment variables from snapshot
            for var, value in context.environment_snapshot.items():
                os.environ[var] = value

            logger.debug(f"Applied context for {context.agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply context: {e}")
            return False
