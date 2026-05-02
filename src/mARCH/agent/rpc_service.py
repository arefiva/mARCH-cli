"""Agent RPC service for inter-agent communication."""

import logging
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RpcMessage:
    """Represents an RPC message."""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Dict[str, Any] = None
    id: str = ""
    from_agent: str = ""
    to_agent: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params or {},
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
        }


class AgentRpcService:
    """Service for RPC communication between agents."""

    def __init__(self):
        """Initialize RPC service."""
        self._registered_agents: Dict[str, Any] = {}
        self._rpc_handlers: Dict[str, Callable] = {}

    def register_agent(self, agent_id: str, agent: Any) -> None:
        """Register an agent for RPC calls.

        Args:
            agent_id: Agent identifier
            agent: Agent instance
        """
        self._registered_agents[agent_id] = agent
        logger.info(f"Registered agent for RPC: {agent_id}")

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if unregistered, False if not found
        """
        if agent_id not in self._registered_agents:
            return False
        self._registered_agents.pop(agent_id)
        logger.info(f"Unregistered agent from RPC: {agent_id}")
        return True

    def register_agent_methods(self, agent_id: str, agent: Any) -> None:
        """Register RPC-exposed methods for an agent.

        Args:
            agent_id: Agent identifier
            agent: Agent instance
        """
        # Common methods exposed by agents
        methods = {
            "agent.get_context": lambda: getattr(agent, "get_context", lambda: {})(),
            "agent.set_context": lambda ctx: setattr(agent, "context", ctx),
            "agent.get_status": lambda: getattr(agent, "get_status", lambda: "unknown")(),
            "agent.execute_command": lambda cmd, ctx: self._call_agent_method(
                agent, "execute_command", cmd, ctx
            ),
        }

        for method_name, handler in methods.items():
            self._rpc_handlers[f"{agent_id}.{method_name}"] = handler

        logger.debug(f"Registered RPC methods for agent: {agent_id}")

    async def call_agent_method(
        self, agent_id: str, method_name: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call a remote agent method.

        Args:
            agent_id: Target agent ID
            method_name: Method name to call
            params: Method parameters

        Returns:
            Result dictionary
        """
        params = params or {}

        # Check if agent is registered
        agent = self._registered_agents.get(agent_id)
        if not agent:
            logger.error(f"Agent not registered: {agent_id}")
            return {
                "error": f"Agent not registered: {agent_id}",
                "code": -32603,
            }

        try:
            # Call the method
            method = getattr(agent, method_name, None)
            if not method or not callable(method):
                logger.error(f"Method not found: {agent_id}.{method_name}")
                return {
                    "error": f"Method not found: {method_name}",
                    "code": -32601,
                }

            # Support both sync and async methods
            import inspect
            if inspect.iscoroutinefunction(method):
                result = await method(**params)
            else:
                result = method(**params)

            return {"result": result}

        except Exception as e:
            logger.error(f"RPC call failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "code": -32603,
            }

    async def broadcast_to_agents(
        self, message: Dict[str, Any], filter_criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Broadcast a message to multiple agents.

        Args:
            message: Message to broadcast
            filter_criteria: Optional filter for target agents

        Returns:
            Dictionary of agent_id -> response
        """
        results = {}

        for agent_id in self._registered_agents:
            # Apply filter if provided
            if filter_criteria:
                # Simple filter matching
                if "exclude_agents" in filter_criteria:
                    if agent_id in filter_criteria["exclude_agents"]:
                        continue

            # Send message to agent
            logger.debug(f"Broadcasting message to agent: {agent_id}")
            results[agent_id] = {"status": "broadcasted"}

        return results

    def _call_agent_method(self, agent: Any, method_name: str, *args, **kwargs) -> Any:
        """Helper to call a method on an agent."""
        method = getattr(agent, method_name, None)
        if method and callable(method):
            return method(*args, **kwargs)
        return None

    def get_registered_agents(self) -> Dict[str, Any]:
        """Get all registered agents.

        Returns:
            Dictionary of agent_id -> agent
        """
        return self._registered_agents.copy()
