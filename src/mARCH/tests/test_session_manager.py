"""Unit tests for session manager."""

import pytest
import asyncio
from src.mARCH.session import SessionManager, Session, SessionConfig


@pytest.fixture
async def manager():
    """Create a session manager for testing."""
    return await SessionManager.get_instance()


@pytest.mark.asyncio
async def test_session_creation(manager):
    """Test creating a new session."""
    session = await manager.create_session("test-agent")
    
    assert session is not None
    assert session.agent_id == "test-agent"
    assert session.status == "active"
    assert session.is_active() is True


@pytest.mark.asyncio
async def test_session_retrieval(manager):
    """Test retrieving a session."""
    created_session = await manager.create_session("agent1")
    retrieved = await manager.get_session(created_session.session_id)
    
    assert retrieved is not None
    assert retrieved.session_id == created_session.session_id


@pytest.mark.asyncio
async def test_session_list(manager):
    """Test listing sessions."""
    await manager.create_session("agent1")
    await manager.create_session("agent2")
    
    sessions = await manager.list_sessions()
    assert len(sessions) >= 2


@pytest.mark.asyncio
async def test_session_list_with_filter(manager):
    """Test listing with filter."""
    await manager.create_session("agent1")
    await manager.create_session("agent2")
    
    sessions = await manager.list_sessions({"agent_id": "agent1"})
    assert all(s.agent_id == "agent1" for s in sessions)


@pytest.mark.asyncio
async def test_session_cleanup(manager):
    """Test session cleanup."""
    session = await manager.create_session("test-agent")
    success = await manager.cleanup_session(session.session_id)
    
    assert success is True
    assert session.status == "completed"


@pytest.mark.asyncio
async def test_session_context_update(manager):
    """Test updating session context."""
    session = await manager.create_session("test-agent")
    session.update_context({"key": "value"})
    
    assert session.context["key"] == "value"


@pytest.mark.asyncio
async def test_session_history(manager):
    """Test adding to execution history."""
    session = await manager.create_session("test-agent")
    session.add_to_history("test-cmd", {"result": "ok"}, 100.0)
    
    assert len(session.execution_history) == 1
    assert session.execution_history[0].command == "test-cmd"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
