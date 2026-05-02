"""Skills/Tools system.

Provides skill registry, plugin loading, and built-in skills.
"""

from .registry import Skill, SkillRegistry, SkillMetadata
from .executor import SkillExecutor, SkillContext
from .plugin_loader import PluginLoader
from .builtin.shell import ShellExecutionSkill
from .builtin.file import FileReadSkill, FileWriteSkill
from .builtin.git import GitOperationSkill
from .builtin.api import APICallSkill
from .builtin.rpc import RpcCallSkill

__all__ = [
    "Skill",
    "SkillRegistry",
    "SkillMetadata",
    "SkillExecutor",
    "SkillContext",
    "PluginLoader",
    "ShellExecutionSkill",
    "FileReadSkill",
    "FileWriteSkill",
    "GitOperationSkill",
    "APICallSkill",
    "RpcCallSkill",
]
