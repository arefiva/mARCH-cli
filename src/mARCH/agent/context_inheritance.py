"""Context inheritance policy for child agents."""

import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class ContextInheritancePolicy:
    """Policy for how child agents inherit context from parent."""
    inherit_file_context: bool = True
    inherit_git_context: bool = True
    inherit_conversation: bool = True
    inherit_patterns: bool = True
    inherit_environment: bool = True
    merge_strategy: Literal["override", "merge", "selective"] = "merge"


class ContextInheritanceManager:
    """Manages context inheritance between agents."""

    def __init__(self, policy: ContextInheritancePolicy = None):
        """Initialize the inheritance manager.

        Args:
            policy: Inheritance policy (default: inherit everything)
        """
        self.policy = policy or ContextInheritancePolicy()

    def apply_policy(self, parent_context, child_context) -> None:
        """Apply inheritance policy to child context.

        Args:
            parent_context: Parent AgentContext
            child_context: Child AgentContext to populate
        """
        # File context
        if self.policy.inherit_file_context:
            child_context.current_file = parent_context.current_file
            child_context.current_directory = parent_context.current_directory
            child_context.language = parent_context.language
            child_context.project_type = parent_context.project_type
            logger.debug("Inherited file context")

        # Git context
        if self.policy.inherit_git_context:
            child_context.git_branch = parent_context.git_branch
            child_context.git_repository = parent_context.git_repository
            child_context.git_status = parent_context.git_status
            logger.debug("Inherited git context")

        # Conversation context
        if self.policy.inherit_conversation:
            # Clone the conversation context
            import copy
            child_context.conversation_context = copy.deepcopy(
                parent_context.conversation_context
            )
            logger.debug("Inherited conversation context")

        # Learned patterns
        if self.policy.inherit_patterns:
            import copy
            child_context.learned_patterns = copy.deepcopy(
                parent_context.learned_patterns
            )
            logger.debug("Inherited learned patterns")

        # Environment
        if self.policy.inherit_environment:
            child_context.environment_snapshot = parent_context.environment_snapshot.copy()
            logger.debug("Inherited environment snapshot")

        # Custom context based on merge strategy
        self._apply_merge_strategy(parent_context, child_context)

    def _apply_merge_strategy(self, parent_context, child_context) -> None:
        """Apply merge strategy for custom context.

        Args:
            parent_context: Parent AgentContext
            child_context: Child AgentContext
        """
        if self.policy.merge_strategy == "override":
            # Child context completely overrides parent
            pass
        elif self.policy.merge_strategy == "merge":
            # Merge parent and child, child takes precedence
            merged = parent_context.custom_context.copy()
            merged.update(child_context.custom_context)
            child_context.custom_context = merged
            logger.debug("Applied merge strategy (parent + child)")
        elif self.policy.merge_strategy == "selective":
            # Keep child's custom context, add parent's prefixed keys
            for key, value in parent_context.custom_context.items():
                parent_key = f"parent_{key}"
                if parent_key not in child_context.custom_context:
                    child_context.custom_context[parent_key] = value
            logger.debug("Applied selective merge strategy")

    @staticmethod
    def create_isolated_child_policy() -> ContextInheritancePolicy:
        """Create a policy for isolated child agents.

        Returns:
            ContextInheritancePolicy with minimal inheritance
        """
        return ContextInheritancePolicy(
            inherit_file_context=True,  # Still need file context for work
            inherit_git_context=False,
            inherit_conversation=False,
            inherit_patterns=False,
            inherit_environment=False,
        )

    @staticmethod
    def create_cooperative_child_policy() -> ContextInheritancePolicy:
        """Create a policy for cooperative child agents.

        Returns:
            ContextInheritancePolicy with full inheritance
        """
        return ContextInheritancePolicy(
            inherit_file_context=True,
            inherit_git_context=True,
            inherit_conversation=True,
            inherit_patterns=True,
            inherit_environment=True,
            merge_strategy="merge",
        )

    @staticmethod
    def create_specialized_child_policy() -> ContextInheritancePolicy:
        """Create a policy for specialized child agents.

        Returns:
            ContextInheritancePolicy for specialized tasks
        """
        return ContextInheritancePolicy(
            inherit_file_context=True,
            inherit_git_context=True,
            inherit_conversation=True,
            inherit_patterns=True,
            inherit_environment=True,
            merge_strategy="selective",
        )
