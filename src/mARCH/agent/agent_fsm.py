"""Agent state machine.

Finite state machine for agent state transitions with validation.
"""

from enum import Enum
from typing import Any, Callable, Dict, Optional, Set
from dataclasses import dataclass


class AgentState(str, Enum):
    """Agent states."""
    IDLE = "idle"
    INITIALIZED = "initialized"
    EXECUTING = "executing"
    WAITING_OUTPUT = "waiting_output"
    PROCESSING_RESULT = "processing_result"
    RESPONDING = "responding"
    ERROR = "error"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


@dataclass
class StateTransition:
    """Represents a state transition."""
    from_state: AgentState
    to_state: AgentState
    context: Optional[Dict[str, Any]] = None


class AgentStateMachine:
    """Finite state machine for agent state transitions."""

    # Define valid transitions
    VALID_TRANSITIONS: Dict[AgentState, Set[AgentState]] = {
        AgentState.IDLE: {AgentState.INITIALIZED, AgentState.SHUTDOWN},
        AgentState.INITIALIZED: {AgentState.EXECUTING, AgentState.SHUTDOWN},
        AgentState.EXECUTING: {
            AgentState.WAITING_OUTPUT,
            AgentState.ERROR,
            AgentState.SHUTDOWN,
        },
        AgentState.WAITING_OUTPUT: {
            AgentState.PROCESSING_RESULT,
            AgentState.ERROR,
            AgentState.SHUTDOWN,
        },
        AgentState.PROCESSING_RESULT: {
            AgentState.RESPONDING,
            AgentState.ERROR,
            AgentState.SHUTDOWN,
        },
        AgentState.RESPONDING: {
            AgentState.IDLE,
            AgentState.ERROR,
            AgentState.FAILED,
            AgentState.SHUTDOWN,
        },
        AgentState.ERROR: {
            AgentState.EXECUTING,
            AgentState.FAILED,
            AgentState.SHUTDOWN,
        },
        AgentState.FAILED: {AgentState.SHUTDOWN},
        AgentState.SHUTDOWN: set(),
    }

    def __init__(self, agent_id: str, initial_state: AgentState = AgentState.IDLE):
        """Initialize the state machine.

        Args:
            agent_id: Unique identifier for the agent
            initial_state: Initial state (default: IDLE)
        """
        self.agent_id = agent_id
        self._current_state = initial_state
        self._state_history: list[tuple[AgentState, Dict[str, Any]]] = [
            (initial_state, {})
        ]
        self._state_handlers: Dict[
            AgentState, Dict[str, Callable]
        ] = self._init_state_handlers()
        self._transition_validators: Dict[
            tuple[AgentState, AgentState], Callable
        ] = {}

    def _init_state_handlers(
        self,
    ) -> Dict[AgentState, Dict[str, Callable]]:
        """Initialize state entry/exit handlers."""
        return {state: {"on_enter": None, "on_exit": None} for state in AgentState}

    @property
    def current_state(self) -> AgentState:
        """Get the current state."""
        return self._current_state

    @property
    def state_history(self) -> list[tuple[AgentState, Dict[str, Any]]]:
        """Get the state transition history."""
        return self._state_history.copy()

    def get_valid_transitions(self, current_state: Optional[AgentState] = None) -> Set[AgentState]:
        """Get valid transitions from a state.

        Args:
            current_state: State to query (uses current state if not provided)

        Returns:
            Set of valid target states
        """
        state = current_state or self._current_state
        return self.VALID_TRANSITIONS.get(state, set()).copy()

    def can_transition(self, new_state: AgentState) -> bool:
        """Check if a transition is valid.

        Args:
            new_state: Target state

        Returns:
            True if transition is valid, False otherwise
        """
        return new_state in self.get_valid_transitions()

    def register_transition_validator(
        self,
        from_state: AgentState,
        to_state: AgentState,
        validator: Callable[[Dict[str, Any]], bool],
    ) -> None:
        """Register a custom transition validator.

        Args:
            from_state: Source state
            to_state: Target state
            validator: Function that returns True if transition is valid
        """
        self._transition_validators[(from_state, to_state)] = validator

    def register_state_handler(
        self,
        state: AgentState,
        handler_type: str,
        handler: Callable,
    ) -> None:
        """Register a state entry/exit handler.

        Args:
            state: State to register handler for
            handler_type: "on_enter" or "on_exit"
            handler: Callable to execute
        """
        if handler_type not in {"on_enter", "on_exit"}:
            raise ValueError(f"Invalid handler type: {handler_type}")
        if state not in self._state_handlers:
            self._state_handlers[state] = {"on_enter": None, "on_exit": None}
        self._state_handlers[state][handler_type] = handler

    async def transition(
        self, new_state: AgentState, context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Transition to a new state.

        Args:
            new_state: Target state
            context: Optional transition context

        Returns:
            True if transition succeeded, False otherwise
        """
        context = context or {}

        # Validate transition
        if not self.can_transition(new_state):
            raise ValueError(
                f"Invalid transition from {self._current_state} to {new_state}"
            )

        # Run custom validator if registered
        validator_key = (self._current_state, new_state)
        if validator_key in self._transition_validators:
            validator = self._transition_validators[validator_key]
            if not validator(context):
                return False

        # Run exit handler for current state
        old_state = self._current_state
        exit_handler = self._state_handlers[old_state].get("on_exit")
        if exit_handler:
            if callable(exit_handler):
                # Support both sync and async handlers
                import inspect
                if inspect.iscoroutinefunction(exit_handler):
                    await exit_handler(context)
                else:
                    exit_handler(context)

        # Update state
        self._current_state = new_state
        self._state_history.append((new_state, context))

        # Run enter handler for new state
        enter_handler = self._state_handlers[new_state].get("on_enter")
        if enter_handler:
            if callable(enter_handler):
                import inspect
                if inspect.iscoroutinefunction(enter_handler):
                    await enter_handler(context)
                else:
                    enter_handler(context)

        return True

    def reset(self) -> None:
        """Reset to initial state."""
        self._current_state = AgentState.IDLE
        self._state_history = [(AgentState.IDLE, {})]

    def __repr__(self) -> str:
        """String representation."""
        return f"AgentStateMachine(agent_id={self.agent_id}, state={self._current_state})"
