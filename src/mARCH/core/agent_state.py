"""
AI Agent state management and conversation logic.

Provides agent state machine, conversation history tracking, and multi-turn
conversation management for the mARCH CLI.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentState(str, Enum):
    """Agent operational states."""

    IDLE = "idle"
    THINKING = "thinking"
    PROCESSING = "processing"
    RESPONDING = "responding"
    ERROR = "error"
    WAITING_INPUT = "waiting_input"


class ConversationMode(str, Enum):
    """Conversation modes."""

    INTERACTIVE = "interactive"
    AUTOPILOT = "autopilot"
    COMMAND = "command"


@dataclass
class ConversationMessage:
    """Single message in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert message to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class AgentContext:
    """Context for agent decision-making."""

    current_file: str | None = None
    current_directory: str = "."
    language: str | None = None
    project_type: str | None = None
    git_branch: str | None = None
    custom_context: dict[str, Any] = field(default_factory=dict)

    def update_from_github_context(self, github_context: dict) -> None:
        """Update context from GitHub integration."""
        if github_context:
            self.current_directory = github_context.get("repo_root", ".")
            self.git_branch = github_context.get("branch")


class ConversationHistory:
    """Manages conversation message history."""

    def __init__(self, max_messages: int = 100):
        """
        Initialize conversation history.

        Args:
            max_messages: Maximum messages to keep in memory
        """
        self.messages: list[ConversationMessage] = []
        self.max_messages = max_messages

    def add_message(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add message to history.

        Args:
            role: Message role ("user" or "assistant")
            content: Message content
            metadata: Optional metadata
        """
        msg = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(msg)

        # Trim old messages if exceeding max
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def get_messages(
        self,
        limit: int | None = None,
        role_filter: str | None = None,
    ) -> list[ConversationMessage]:
        """
        Get messages from history.

        Args:
            limit: Limit to last N messages
            role_filter: Filter by role ("user" or "assistant")

        Returns:
            List of messages
        """
        messages = self.messages

        if role_filter:
            messages = [m for m in messages if m.role == role_filter]

        if limit:
            messages = messages[-limit:]

        return messages

    def get_summary(self, token_limit: int = 1000) -> str:
        """
        Get conversation summary for API context.

        Args:
            token_limit: Approximate token limit

        Returns:
            Summary string
        """
        summary_parts: list[str] = []
        total_chars = 0

        for msg in reversed(self.messages):
            char_count = len(msg.content)
            if total_chars + char_count > token_limit * 4:  # Rough estimate
                break
            summary_parts.insert(
                0, f"{msg.role}: {msg.content[:200]}..."
            )
            total_chars += char_count

        return "\n".join(summary_parts)

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages.clear()

    def export(self) -> list[dict]:
        """Export conversation history as dictionaries."""
        return [msg.to_dict() for msg in self.messages]


class Agent:
    """AI Agent for conversation handling."""

    def __init__(
        self,
        name: str = "mARCH",
        mode: ConversationMode = ConversationMode.INTERACTIVE,
    ):
        """
        Initialize agent.

        Args:
            name: Agent name
            mode: Conversation mode
        """
        self.name = name
        self.mode = mode
        self.state = AgentState.IDLE
        self.history = ConversationHistory()
        self.context = AgentContext()
        self.is_thinking = False

    def set_state(self, state: AgentState) -> None:
        """Set agent state."""
        self.state = state

    def set_mode(self, mode: ConversationMode) -> None:
        """Set conversation mode."""
        self.mode = mode

    def add_user_message(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add user message to history."""
        self.history.add_message("user", content, metadata)

    def add_assistant_message(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add assistant message to history."""
        self.history.add_message("assistant", content, metadata)

    def should_autopilot(self) -> bool:
        """Check if autopilot mode is enabled."""
        return self.mode == ConversationMode.AUTOPILOT

    def get_conversation_context(
        self, include_system_prompt: bool = True
    ) -> list[dict]:
        """
        Get conversation messages for API call.

        Args:
            include_system_prompt: Include system prompt

        Returns:
            List of message dicts suitable for API
        """
        messages = []

        if include_system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": self._get_system_prompt(),
                }
            )

        for msg in self.history.messages:
            messages.append({"role": msg.role, "content": msg.content})

        return messages

    def _get_system_prompt(self) -> str:
        """Generate system prompt for agent."""
        return f"""You are {self.name}, an AI-powered coding assistant.
You help developers with code analysis, debugging, and implementation.

Current context:
- Directory: {self.context.current_directory}
- Language: {self.context.language or "Not specified"}
- Branch: {self.context.git_branch or "Not specified"}

Be concise, helpful, and provide code examples when appropriate."""

    def get_history(self, limit: int | None = None) -> list[ConversationMessage]:
        """Get conversation history."""
        return self.history.get_messages(limit=limit)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.history.clear()

    def is_ready_to_respond(self) -> bool:
        """Check if agent is ready to respond."""
        return self.state not in (
            AgentState.ERROR,
            AgentState.THINKING,
            AgentState.PROCESSING,
        )


class AgentManager:
    """Manages agent lifecycle and operations."""

    def __init__(self):
        """Initialize agent manager."""
        self.agents: dict[str, Agent] = {}
        self.default_agent_name = "march"
        self._create_default_agent()

    def _create_default_agent(self) -> None:
        """Create default agent."""
        agent = Agent(
            name="mARCH",
            mode=ConversationMode.INTERACTIVE,
        )
        self.agents[self.default_agent_name] = agent

    def get_agent(self, name: str | None = None) -> Agent:
        """Get agent by name (creates if not exists)."""
        if name is None:
            name = self.default_agent_name

        if name not in self.agents:
            self.agents[name] = Agent(name=name.capitalize())

        return self.agents[name]

    def create_agent(
        self,
        name: str,
        mode: ConversationMode = ConversationMode.INTERACTIVE,
    ) -> Agent:
        """Create new agent."""
        agent = Agent(name=name, mode=mode)
        self.agents[name] = agent
        return agent

    def list_agents(self) -> list[str]:
        """Get list of agent names."""
        return list(self.agents.keys())

    def set_default_agent(self, name: str) -> bool:
        """Set default agent."""
        if name in self.agents:
            self.default_agent_name = name
            return True
        return False

    def delete_agent(self, name: str) -> bool:
        """Delete agent (cannot delete default agent)."""
        if name != self.default_agent_name and name in self.agents:
            del self.agents[name]
            return True
        return False


_agent_manager_instance: AgentManager | None = None


def get_agent_manager() -> AgentManager:
    """Get or create singleton AgentManager."""
    global _agent_manager_instance
    if _agent_manager_instance is None:
        _agent_manager_instance = AgentManager()
    return _agent_manager_instance
