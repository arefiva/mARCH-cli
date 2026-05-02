"""Unit tests for agent state machine."""

import pytest
from src.mARCH.agent.agent_fsm import AgentStateMachine, AgentState


@pytest.fixture
def fsm():
    """Create a state machine for testing."""
    return AgentStateMachine("test-agent")


def test_fsm_initialization(fsm):
    """Test FSM initialization."""
    assert fsm.agent_id == "test-agent"
    assert fsm.current_state == AgentState.IDLE


def test_fsm_valid_transitions(fsm):
    """Test valid state transitions."""
    valid_next = fsm.get_valid_transitions(AgentState.IDLE)
    assert AgentState.INITIALIZED in valid_next
    assert AgentState.SHUTDOWN in valid_next


def test_fsm_invalid_transitions(fsm):
    """Test invalid transitions."""
    assert not fsm.can_transition(AgentState.ERROR)
    assert not fsm.can_transition(AgentState.FAILED)


@pytest.mark.asyncio
async def test_fsm_transition(fsm):
    """Test state transition."""
    success = await fsm.transition(AgentState.INITIALIZED)
    assert success is True
    assert fsm.current_state == AgentState.INITIALIZED


@pytest.mark.asyncio
async def test_fsm_invalid_transition_raises(fsm):
    """Test invalid transition raises error."""
    with pytest.raises(ValueError):
        await fsm.transition(AgentState.FAILED)


def test_fsm_state_history(fsm):
    """Test state history tracking."""
    history = fsm.state_history
    assert len(history) >= 1
    assert history[0][0] == AgentState.IDLE


@pytest.mark.asyncio
async def test_fsm_with_handler(fsm):
    """Test state handlers."""
    handler_called = False
    
    def on_enter_handler(context):
        nonlocal handler_called
        handler_called = True
    
    fsm.register_state_handler(AgentState.INITIALIZED, "on_enter", on_enter_handler)
    await fsm.transition(AgentState.INITIALIZED)
    
    # Handler should have been called
    assert handler_called is True


def test_fsm_reset(fsm):
    """Test FSM reset."""
    fsm.reset()
    assert fsm.current_state == AgentState.IDLE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
