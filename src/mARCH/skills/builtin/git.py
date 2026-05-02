"""Git operation skill."""

import asyncio
import logging
from typing import Any, Dict

from ..registry import Skill

logger = logging.getLogger(__name__)


class GitOperationSkill(Skill):
    """Executes git commands."""

    name = "git_operation"
    version = "1.0.0"
    description = "Execute git operations and commands"

    async def execute(
        self, params: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute a git command.

        Args:
            params: Parameters including 'operation' or 'command'
            context: Optional execution context

        Returns:
            Result with command output
        """
        command = params.get("command") or params.get("operation")
        if not command:
            raise ValueError("Missing required parameter: command or operation")

        repo_path = params.get("repo_path", ".")
        timeout = params.get("timeout", 30)

        # Build git command
        if not command.startswith("git "):
            command = f"git {command}"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_path,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return {
                "command": command,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "return_code": process.returncode,
                "success": process.returncode == 0,
                "repo_path": repo_path,
            }
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"Git command timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Git operation failed: {e}")
            raise

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate parameters."""
        return "command" in params or "operation" in params

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Git command to execute (with or without 'git' prefix)",
                },
                "operation": {
                    "type": "string",
                    "description": "Alternative name for command",
                },
                "repo_path": {
                    "type": "string",
                    "description": "Repository path",
                    "default": ".",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 30,
                },
            },
            "anyOf": [
                {"required": ["command"]},
                {"required": ["operation"]},
            ],
        }
