"""
AI agent module - public API for agent management and conversations.

Re-exports key components from agent_state for convenience.
"""

# Import and re-export agent components
from mARCH.core.agent_state import (
    Agent,
    AgentContext,
    AgentManager,
    AgentState,
    ConversationHistory,
    ConversationMessage,
    ConversationMode,
    get_agent_manager,
)

__all__ = [
    "Agent",
    "AgentContext",
    "AgentManager",
    "AgentState",
    "ConversationHistory",
    "ConversationMessage",
    "ConversationMode",
    "get_agent_manager",
]
