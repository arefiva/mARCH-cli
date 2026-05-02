"""Shell execution skill.

Execute shell commands with output capture and error handling.
"""

import asyncio
import logging
from typing import Any, Dict

from ..registry import Skill

logger = logging.getLogger(__name__)


class ShellExecutionSkill(Skill):
    """Executes shell commands."""

    name = "shell_exec"
    version = "1.0.0"
    description = "Execute shell commands with output capture"

    async def execute(
        self, params: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute a shell command.

        Args:
            params: Parameters including 'command' key
            context: Optional execution context

        Returns:
            Result with stdout, stderr, and return code
        """
        command = params.get("command")
        if not command:
            raise ValueError("Missing required parameter: command")

        timeout = params.get("timeout", 30)
        cwd = params.get("cwd")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "return_code": process.returncode,
                "success": process.returncode == 0,
            }
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"Command timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Shell execution failed: {e}")
            raise

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate parameters."""
        return "command" in params

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 30,
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for command",
                },
            },
            "required": ["command"],
        }
