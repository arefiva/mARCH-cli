"""RPC call skill for inter-agent communication."""

import logging
from typing import Any, Dict

from ..registry import Skill

logger = logging.getLogger(__name__)


class RpcCallSkill(Skill):
    """Makes RPC calls to other agents."""

    name = "rpc_call"
    version = "1.0.0"
    description = "Make RPC calls to other agents"

    async def execute(
        self, params: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make an RPC call.

        Args:
            params: Parameters including 'agent_id', 'method', and 'params'
            context: Optional execution context

        Returns:
            Result with RPC response
        """
        agent_id = params.get("agent_id")
        method = params.get("method")
        rpc_params = params.get("params", {})

        if not agent_id:
            raise ValueError("Missing required parameter: agent_id")
        if not method:
            raise ValueError("Missing required parameter: method")

        try:
            # This would typically call an RPC service to reach the target agent
            # For now, return a placeholder implementation
            logger.info(
                f"RPC call to agent {agent_id}, method {method} with params {rpc_params}"
            )

            return {
                "agent_id": agent_id,
                "method": method,
                "result": None,
                "success": True,
            }

        except Exception as e:
            logger.error(f"RPC call failed: {e}")
            raise

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate parameters."""
        return "agent_id" in params and "method" in params

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema."""
        return {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Target agent ID",
                },
                "method": {
                    "type": "string",
                    "description": "Method name to call",
                },
                "params": {
                    "type": "object",
                    "description": "Method parameters",
                    "default": {},
                },
            },
            "required": ["agent_id", "method"],
        }
