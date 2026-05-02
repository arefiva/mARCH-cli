"""Skill registry and base classes.

Registry-based skill registration and discovery.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
import json

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Metadata for a skill."""
    name: str
    version: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    requires_auth: bool = False
    timeout_seconds: int = 30
    resource_limits: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "requires_auth": self.requires_auth,
            "timeout_seconds": self.timeout_seconds,
            "resource_limits": self.resource_limits,
        }


class Skill(ABC):
    """Abstract base class for skills."""

    name: str = "base_skill"
    version: str = "1.0.0"
    description: str = ""

    @abstractmethod
    async def execute(
        self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the skill.

        Args:
            params: Parameters for the skill
            context: Optional execution context

        Returns:
            Result dictionary
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate input parameters.

        Args:
            params: Parameters to validate

        Returns:
            True if valid, False otherwise
        """
        # Override in subclasses for custom validation
        return True

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for parameters.

        Returns:
            JSON schema dictionary
        """
        # Override in subclasses for schema definition
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def get_metadata(self) -> SkillMetadata:
        """Get skill metadata.

        Returns:
            SkillMetadata instance
        """
        return SkillMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name={self.name}, version={self.version})"


class SkillRegistry:
    """Registry for skill management.

    Singleton pattern for application-wide skill registry.
    """

    _instance: Optional["SkillRegistry"] = None

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the registry."""
        if not hasattr(self, "_initialized"):
            self._skills: Dict[str, Skill] = {}
            self._tags_index: Dict[str, Set[str]] = {}
            self._initialized = True

    def register_skill(self, skill: Skill) -> None:
        """Register a skill.

        Args:
            skill: Skill instance to register
        """
        if not isinstance(skill, Skill):
            raise TypeError(f"Skill must be an instance of Skill class, got {type(skill)}")

        self._skills[skill.name] = skill
        logger.info(f"Registered skill: {skill.name} (v{skill.version})")

        # Update tags index
        metadata = skill.get_metadata()
        for tag in metadata.tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = set()
            self._tags_index[tag].add(skill.name)

    def unregister_skill(self, skill_name: str) -> bool:
        """Unregister a skill.

        Args:
            skill_name: Name of skill to unregister

        Returns:
            True if unregistered, False if not found
        """
        if skill_name not in self._skills:
            logger.warning(f"Skill not found for unregistration: {skill_name}")
            return False

        skill = self._skills.pop(skill_name)

        # Update tags index
        metadata = skill.get_metadata()
        for tag in metadata.tags:
            self._tags_index[tag].discard(skill_name)
            if not self._tags_index[tag]:
                del self._tags_index[tag]

        logger.info(f"Unregistered skill: {skill_name}")
        return True

    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """Retrieve a skill.

        Args:
            skill_name: Name of skill to retrieve

        Returns:
            Skill instance if found, None otherwise
        """
        return self._skills.get(skill_name)

    def list_skills(
        self, filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Skill]:
        """List all registered skills with optional filtering.

        Args:
            filter_criteria: Optional filter criteria

        Returns:
            List of matching skills
        """
        skills = list(self._skills.values())

        if not filter_criteria:
            return skills

        # Apply filters
        if "tag" in filter_criteria:
            tag = filter_criteria["tag"]
            skills = [s for s in skills if tag in s.get_metadata().tags]

        if "version" in filter_criteria:
            version = filter_criteria["version"]
            skills = [s for s in skills if s.version == version]

        return skills

    def get_skills_by_tag(self, tag: str) -> List[Skill]:
        """Get skills by tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of skills with the tag
        """
        skill_names = self._tags_index.get(tag, set())
        return [self._skills[name] for name in skill_names if name in self._skills]

    def validate_skill_config(self, config: Dict[str, Any]) -> bool:
        """Validate skill configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        if "name" not in config:
            logger.warning("Skill config missing 'name' field")
            return False

        skill = self.get_skill(config["name"])
        if not skill:
            logger.warning(f"Skill not found: {config['name']}")
            return False

        # Validate parameters if provided
        if "params" in config:
            if not skill.validate_params(config["params"]):
                logger.warning(f"Invalid parameters for skill {config['name']}")
                return False

        return True

    def get_all_skills(self) -> Dict[str, Skill]:
        """Get all registered skills.

        Returns:
            Dictionary of skill_name -> Skill
        """
        return self._skills.copy()

    def get_skills_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all registered skills.

        Returns:
            List of skill metadata dictionaries
        """
        return [skill.get_metadata().to_dict() for skill in self._skills.values()]

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        """Get singleton instance.

        Returns:
            SkillRegistry instance
        """
        return cls()
