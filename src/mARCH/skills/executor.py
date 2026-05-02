"""Skill execution context and executor.

Provides context to skills during execution and manages skill execution.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .registry import Skill, SkillRegistry

logger = logging.getLogger(__name__)


@dataclass
class SkillContext:
    """Context for skill execution."""
    agent_context: Dict[str, Any] = field(default_factory=dict)
    session: Optional[Any] = None
    available_skills: Optional[SkillRegistry] = None
    timeout_ms: int = 30000
    execution_id: str = ""
    logger: Optional[Any] = None
    config: Dict[str, Any] = field(default_factory=dict)
    user_data: Dict[str, Any] = field(default_factory=dict)

    def get_agent_context(self) -> Dict[str, Any]:
        """Get agent context."""
        return self.agent_context.copy()

    def get_session(self) -> Optional[Any]:
        """Get session."""
        return self.session

    def get_available_skills(self) -> Optional[SkillRegistry]:
        """Get available skills."""
        return self.available_skills

    def set_user_data(self, key: str, value: Any) -> None:
        """Store user data in context.

        Args:
            key: Data key
            value: Data value
        """
        self.user_data[key] = value

    def get_user_data(self, key: str, default: Any = None) -> Any:
        """Retrieve user data from context.

        Args:
            key: Data key
            default: Default value if not found

        Returns:
            User data value
        """
        return self.user_data.get(key, default)


class SkillExecutor:
    """Executes skills with context and error handling."""

    def __init__(self, skill_registry: Optional[SkillRegistry] = None):
        """Initialize the skill executor.

        Args:
            skill_registry: Skill registry instance
        """
        self.skill_registry = skill_registry or SkillRegistry()

    async def execute_skill(
        self,
        skill_name: str,
        params: Dict[str, Any],
        context: Optional[SkillContext] = None,
    ) -> Dict[str, Any]:
        """Execute a single skill.

        Args:
            skill_name: Name of skill to execute
            params: Parameters for the skill
            context: Optional execution context

        Returns:
            Result dictionary with status and output
        """
        context = context or SkillContext()

        # Get skill
        skill = self.skill_registry.get_skill(skill_name)
        if not skill:
            return {
                "status": "error",
                "error": f"Skill not found: {skill_name}",
            }

        # Validate parameters
        if not skill.validate_params(params):
            return {
                "status": "error",
                "error": f"Invalid parameters for skill {skill_name}",
            }

        try:
            # Execute with timeout
            timeout_sec = context.timeout_ms / 1000.0
            start_time = time.time()

            result = await asyncio.wait_for(
                skill.execute(params, context.agent_context),
                timeout=timeout_sec,
            )

            duration_ms = (time.time() - start_time) * 1000

            return {
                "status": "success",
                "result": result,
                "duration_ms": duration_ms,
                "skill": skill_name,
            }

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(f"Skill {skill_name} timed out after {context.timeout_ms}ms")
            return {
                "status": "timeout",
                "error": f"Skill execution timed out after {context.timeout_ms}ms",
                "skill": skill_name,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Skill {skill_name} execution failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "skill": skill_name,
                "duration_ms": duration_ms,
            }

    async def execute_skill_chain(
        self,
        skills: List[Dict[str, Any]],
        context: Optional[SkillContext] = None,
    ) -> Dict[str, Any]:
        """Execute multiple skills sequentially.

        Args:
            skills: List of skill definitions with names and params
            context: Optional execution context

        Returns:
            Result with all skill outputs
        """
        context = context or SkillContext()
        results = []
        success = True

        for skill_def in skills:
            if not isinstance(skill_def, dict) or "name" not in skill_def:
                results.append({
                    "status": "error",
                    "error": "Invalid skill definition",
                })
                success = False
                break

            skill_name = skill_def["name"]
            params = skill_def.get("params", {})

            result = await self.execute_skill(skill_name, params, context)
            results.append(result)

            # Stop if skill failed (unless continue_on_error is True)
            if result["status"] in ("error", "timeout"):
                if not skill_def.get("continue_on_error", False):
                    success = False
                    break

        return {
            "status": "success" if success else "partial",
            "results": results,
            "total_skills": len(skills),
            "successful_skills": sum(
                1 for r in results if r["status"] == "success"
            ),
        }

    async def execute_skills_parallel(
        self,
        skills: List[Dict[str, Any]],
        context: Optional[SkillContext] = None,
    ) -> Dict[str, Any]:
        """Execute multiple skills in parallel.

        Args:
            skills: List of skill definitions with names and params
            context: Optional execution context

        Returns:
            Result with all skill outputs
        """
        context = context or SkillContext()

        # Create tasks
        tasks = []
        skill_names = []

        for skill_def in skills:
            if not isinstance(skill_def, dict) or "name" not in skill_def:
                continue

            skill_name = skill_def["name"]
            params = skill_def.get("params", {})
            skill_names.append(skill_name)

            task = self.execute_skill(skill_name, params, context)
            tasks.append(task)

        # Execute in parallel
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Parallel skill execution failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

        # Process results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")

        return {
            "status": "success" if successful == len(results) else "partial",
            "results": results,
            "skill_names": skill_names,
            "total_skills": len(results),
            "successful_skills": successful,
        }

    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a skill.

        Args:
            skill_name: Name of skill

        Returns:
            Skill metadata if found, None otherwise
        """
        skill = self.skill_registry.get_skill(skill_name)
        if not skill:
            return None

        metadata = skill.get_metadata()
        schema = skill.get_schema()

        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "tags": metadata.tags,
            "schema": schema,
        }

    def list_available_skills(self) -> List[Dict[str, Any]]:
        """List all available skills.

        Returns:
            List of skill metadata
        """
        return self.skill_registry.get_skills_metadata()
