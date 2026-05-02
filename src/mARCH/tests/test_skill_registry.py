"""Unit tests for skill registry."""

import pytest
from src.mARCH.skills import Skill, SkillRegistry


class DummySkill(Skill):
    """Test skill."""
    name = "dummy_skill"
    version = "1.0.0"
    description = "A dummy test skill"
    
    async def execute(self, params, context=None):
        """Execute the skill."""
        return {"result": "success"}


@pytest.fixture
def registry():
    """Create a skill registry for testing."""
    return SkillRegistry()


def test_registry_initialization(registry):
    """Test registry initialization."""
    assert isinstance(registry, SkillRegistry)


def test_skill_registration(registry):
    """Test registering a skill."""
    skill = DummySkill()
    registry.register_skill(skill)
    
    assert registry.get_skill("dummy_skill") is not None


def test_skill_retrieval(registry):
    """Test retrieving a skill."""
    skill = DummySkill()
    registry.register_skill(skill)
    
    retrieved = registry.get_skill("dummy_skill")
    assert retrieved is not None
    assert retrieved.name == "dummy_skill"


def test_skill_list(registry):
    """Test listing skills."""
    skill1 = DummySkill()
    skill2 = DummySkill()
    skill2.name = "dummy_skill_2"
    
    registry.register_skill(skill1)
    registry.register_skill(skill2)
    
    skills = registry.list_skills()
    assert len(skills) >= 2


def test_skill_unregistration(registry):
    """Test unregistering a skill."""
    skill = DummySkill()
    registry.register_skill(skill)
    
    success = registry.unregister_skill("dummy_skill")
    assert success is True
    assert registry.get_skill("dummy_skill") is None


def test_skill_validation(registry):
    """Test skill configuration validation."""
    skill = DummySkill()
    registry.register_skill(skill)
    
    config = {"name": "dummy_skill", "params": {}}
    assert registry.validate_skill_config(config) is True


def test_invalid_skill_validation(registry):
    """Test invalid skill validation."""
    config = {"name": "nonexistent_skill"}
    assert registry.validate_skill_config(config) is False


def test_skill_metadata(registry):
    """Test skill metadata."""
    skill = DummySkill()
    registry.register_skill(skill)
    
    metadata_list = registry.get_skills_metadata()
    assert len(metadata_list) >= 1
    assert metadata_list[0]["name"] == "dummy_skill"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
