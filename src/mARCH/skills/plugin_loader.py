"""Plugin loader for dynamic skill discovery.

Discovers and loads skills from the plugin directory.
"""

import asyncio
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, List, Optional, Type

from .registry import Skill, SkillRegistry

logger = logging.getLogger(__name__)


class PluginLoader:
    """Loads and manages plugins (skills)."""

    def __init__(self, skill_registry: Optional[SkillRegistry] = None):
        """Initialize the plugin loader.

        Args:
            skill_registry: Skill registry instance
        """
        self.skill_registry = skill_registry or SkillRegistry()
        self._loaded_plugins: dict[str, Any] = {}

    async def discover_plugins(self, directory: Path) -> List[Path]:
        """Discover Python plugin files in a directory.

        Args:
            directory: Directory to search for plugins

        Returns:
            List of discovered plugin file paths
        """
        directory = Path(directory)
        if not directory.exists():
            logger.warning(f"Plugin directory does not exist: {directory}")
            return []

        plugins = []

        # Find all .py files in directory and subdirectories
        for py_file in directory.rglob("*.py"):
            # Skip __pycache__ and __init__.py
            if "__pycache__" in py_file.parts or py_file.name == "__init__.py":
                continue

            plugins.append(py_file)

        logger.info(f"Discovered {len(plugins)} plugin files in {directory}")
        return plugins

    async def load_plugin(self, plugin_path: Path) -> Optional[Skill]:
        """Load a plugin from a Python file.

        Args:
            plugin_path: Path to the plugin file

        Returns:
            Loaded Skill instance if successful, None otherwise
        """
        try:
            plugin_path = Path(plugin_path)

            # Load the module
            spec = importlib.util.spec_from_file_location(
                plugin_path.stem, plugin_path
            )
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create module spec for {plugin_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_path.stem] = module
            spec.loader.exec_module(module)

            # Get skill class
            skill_class = getattr(module, "__skill_class__", None)
            if skill_class is None:
                logger.debug(f"Plugin {plugin_path} does not export __skill_class__")
                return None

            # Validate it's a Skill subclass
            if not issubclass(skill_class, Skill):
                logger.error(
                    f"Plugin class {skill_class} is not a Skill subclass"
                )
                return None

            # Instantiate skill
            skill = skill_class()
            self._loaded_plugins[skill.name] = skill
            logger.info(f"Loaded plugin: {skill.name} from {plugin_path}")
            return skill

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_path}: {e}", exc_info=True)
            return None

    def validate_plugin(self, plugin: Any) -> bool:
        """Validate that a plugin is a valid Skill.

        Args:
            plugin: Plugin instance to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(plugin, Skill):
            logger.error(f"Plugin must be a Skill instance, got {type(plugin)}")
            return False

        # Check required attributes
        if not hasattr(plugin, "name") or not plugin.name:
            logger.error("Plugin must have a non-empty 'name' attribute")
            return False

        if not hasattr(plugin, "version") or not plugin.version:
            logger.error("Plugin must have a non-empty 'version' attribute")
            return False

        # Check required methods
        if not hasattr(plugin, "execute") or not callable(plugin.execute):
            logger.error("Plugin must implement 'execute' method")
            return False

        logger.debug(f"Validated plugin: {plugin.name}")
        return True

    async def load_all_plugins(
        self, plugin_dirs: List[Path]
    ) -> tuple[int, int]:
        """Load all plugins from a list of directories.

        Args:
            plugin_dirs: List of directories to search for plugins

        Returns:
            Tuple of (loaded_count, failed_count)
        """
        loaded_count = 0
        failed_count = 0

        for plugin_dir in plugin_dirs:
            plugins = await self.discover_plugins(plugin_dir)

            for plugin_path in plugins:
                skill = await self.load_plugin(plugin_path)
                if skill:
                    if self.validate_plugin(skill):
                        self.skill_registry.register_skill(skill)
                        loaded_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1

        logger.info(
            f"Loaded plugins: {loaded_count} successful, {failed_count} failed"
        )
        return (loaded_count, failed_count)

    def get_plugin_info(self, plugin_name: str) -> Optional[dict[str, Any]]:
        """Get information about a loaded plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin metadata if found, None otherwise
        """
        if plugin_name not in self._loaded_plugins:
            return None

        plugin = self._loaded_plugins[plugin_name]
        metadata = plugin.get_metadata()

        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "tags": metadata.tags,
            "module": type(plugin).__module__,
        }

    def get_loaded_plugins(self) -> dict[str, Any]:
        """Get all loaded plugins.

        Returns:
            Dictionary of plugin_name -> Skill instance
        """
        return self._loaded_plugins.copy()

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin.

        Args:
            plugin_name: Name of plugin to unload

        Returns:
            True if unloaded, False if not found
        """
        if plugin_name not in self._loaded_plugins:
            logger.warning(f"Plugin not found for unload: {plugin_name}")
            return False

        self._loaded_plugins.pop(plugin_name)
        self.skill_registry.unregister_skill(plugin_name)
        logger.info(f"Unloaded plugin: {plugin_name}")
        return True

    def reload_plugin(self, plugin_path: Path) -> Optional[Skill]:
        """Reload a plugin (unload and reload).

        Args:
            plugin_path: Path to the plugin file

        Returns:
            Reloaded Skill instance if successful, None otherwise
        """
        # This is a blocking operation, but called from async context
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.load_plugin(plugin_path))
        finally:
            loop.close()
