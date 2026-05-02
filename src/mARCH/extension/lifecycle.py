"""Extension lifecycle management."""

import asyncio
import logging
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from .contracts import ExtensionStatus as ExtensionStatusModel
from .protocol import ExtensionProtocolHandler
from .types import ExtensionStatus

logger = logging.getLogger(__name__)


class ExtensionLifecycleState(str, Enum):
    """Extension lifecycle states."""

    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"
    FAILED = "failed"


class ExtensionContext:
    """Runtime context for an extension."""

    def __init__(self, name: str, version: str, directory: Path):
        """Initialize extension context.

        Args:
            name: Extension name
            version: Extension version
            directory: Extension directory
        """
        self.name = name
        self.version = version
        self.directory = directory
        self.state = ExtensionLifecycleState.NOT_LOADED
        self.protocol_handler: Optional[ExtensionProtocolHandler] = None
        self.load_time_ms: Optional[float] = None
        self.last_error: Optional[str] = None
        self.metadata: dict[str, Any] = {}


class ExtensionLifecycleManager:
    """Manages extension loading, initialization, and unloading."""

    def __init__(self):
        """Initialize lifecycle manager."""
        self.loaded_extensions: dict[str, ExtensionContext] = {}
        self.hooks: dict[str, list[Callable]] = {}
        self.state_callbacks: dict[str, list[Callable]] = {}
        self.restart_count: dict[str, int] = {}
        self.max_restart_attempts = 3

    async def load_extension(
        self, name: str, version: str, directory: Path
    ) -> bool:
        """Load an extension.

        Args:
            name: Extension name
            version: Extension version
            directory: Extension directory

        Returns:
            True if successful, False otherwise
        """
        if name in self.loaded_extensions:
            logger.warning(f"Extension already loaded: {name}")
            return False

        # Create context
        context = ExtensionContext(name, version, directory)
        context.state = ExtensionLifecycleState.LOADING

        self.loaded_extensions[name] = context
        await self._notify_state_change(name, ExtensionLifecycleState.LOADING)

        try:
            # Record load start time
            start_time = time.time()

            # Create protocol handler
            context.protocol_handler = ExtensionProtocolHandler(name)

            # Invoke on_load hook
            await self._invoke_hook("on_load", name, context)

            # Record load time
            context.load_time_ms = (time.time() - start_time) * 1000

            # Update state
            context.state = ExtensionLifecycleState.LOADED
            await self._notify_state_change(name, ExtensionLifecycleState.LOADED)

            logger.info(f"Loaded extension {name} ({context.load_time_ms:.1f}ms)")
            self.restart_count[name] = 0

            return True

        except Exception as e:
            logger.error(f"Failed to load extension {name}: {e}")
            context.state = ExtensionLifecycleState.FAILED
            context.last_error = str(e)
            await self._notify_state_change(name, ExtensionLifecycleState.FAILED)
            return False

    async def unload_extension(self, name: str) -> bool:
        """Unload an extension.

        Args:
            name: Extension name

        Returns:
            True if successful, False otherwise
        """
        context = self.loaded_extensions.get(name)
        if not context:
            logger.warning(f"Extension not loaded: {name}")
            return False

        context.state = ExtensionLifecycleState.UNLOADING
        await self._notify_state_change(name, ExtensionLifecycleState.UNLOADING)

        try:
            # Invoke on_unload hook
            await self._invoke_hook("on_unload", name, context)

            # Clean up
            if context.protocol_handler:
                # Close any open connections/resources
                pass

            # Remove from loaded
            del self.loaded_extensions[name]
            self.restart_count.pop(name, None)

            logger.info(f"Unloaded extension {name}")
            return True

        except Exception as e:
            logger.error(f"Error unloading extension {name}: {e}")
            context.state = ExtensionLifecycleState.FAILED
            context.last_error = str(e)
            await self._notify_state_change(name, ExtensionLifecycleState.FAILED)
            return False

    async def activate_extension(self, name: str) -> bool:
        """Activate an extension (transition to active state).

        Args:
            name: Extension name

        Returns:
            True if successful, False otherwise
        """
        context = self.loaded_extensions.get(name)
        if not context:
            return False

        if context.state != ExtensionLifecycleState.LOADED:
            logger.warning(
                f"Cannot activate extension {name} in state {context.state}"
            )
            return False

        try:
            context.state = ExtensionLifecycleState.ACTIVE
            await self._notify_state_change(name, ExtensionLifecycleState.ACTIVE)
            await self._invoke_hook("on_activate", name, context)
            return True
        except Exception as e:
            logger.error(f"Failed to activate extension {name}: {e}")
            context.state = ExtensionLifecycleState.FAILED
            return False

    async def deactivate_extension(self, name: str) -> bool:
        """Deactivate an extension (transition from active to loaded).

        Args:
            name: Extension name

        Returns:
            True if successful, False otherwise
        """
        context = self.loaded_extensions.get(name)
        if not context:
            return False

        if context.state != ExtensionLifecycleState.ACTIVE:
            logger.warning(
                f"Cannot deactivate extension {name} in state {context.state}"
            )
            return False

        try:
            await self._invoke_hook("on_deactivate", name, context)
            context.state = ExtensionLifecycleState.LOADED
            await self._notify_state_change(name, ExtensionLifecycleState.LOADED)
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate extension {name}: {e}")
            context.state = ExtensionLifecycleState.FAILED
            return False

    async def restart_extension(self, name: str) -> bool:
        """Restart an extension with exponential backoff.

        Args:
            name: Extension name

        Returns:
            True if successful, False otherwise
        """
        context = self.loaded_extensions.get(name)
        if not context:
            return False

        # Check restart limit
        restart_attempts = self.restart_count.get(name, 0)
        if restart_attempts >= self.max_restart_attempts:
            logger.error(f"Extension {name} exceeded max restart attempts")
            context.state = ExtensionLifecycleState.FAILED
            return False

        # Exponential backoff: 1s, 2s, 4s
        wait_seconds = 2 ** restart_attempts
        logger.info(
            f"Restarting extension {name} (attempt {restart_attempts + 1}, "
            f"waiting {wait_seconds}s)"
        )

        await asyncio.sleep(wait_seconds)

        # Unload and reload
        success = await self.unload_extension(name)
        if success:
            directory = context.directory
            version = context.version
            success = await self.load_extension(name, version, directory)

        if success:
            self.restart_count[name] = 0
        else:
            self.restart_count[name] = restart_attempts + 1

        return success

    def register_hook(self, hook_type: str, handler: Callable) -> None:
        """Register a lifecycle hook handler.

        Hook types: on_load, on_unload, on_activate, on_deactivate, etc.

        Args:
            hook_type: Type of hook
            handler: Handler function
        """
        if hook_type not in self.hooks:
            self.hooks[hook_type] = []
        self.hooks[hook_type].append(handler)

    def register_state_callback(self, extension_name: str, callback: Callable) -> None:
        """Register a state change callback.

        Args:
            extension_name: Extension name (or "*" for all)
            callback: Callback function
        """
        key = extension_name
        if key not in self.state_callbacks:
            self.state_callbacks[key] = []
        self.state_callbacks[key].append(callback)

    async def _invoke_hook(
        self, hook_type: str, extension_name: str, context: ExtensionContext
    ) -> None:
        """Invoke hook handlers.

        Args:
            hook_type: Hook type
            extension_name: Extension name
            context: Extension context
        """
        handlers = self.hooks.get(hook_type, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(extension_name, context)
                else:
                    handler(extension_name, context)
            except Exception as e:
                logger.error(f"Error in {hook_type} hook for {extension_name}: {e}")

    async def _notify_state_change(
        self, extension_name: str, new_state: ExtensionLifecycleState
    ) -> None:
        """Notify state change callbacks.

        Args:
            extension_name: Extension name
            new_state: New state
        """
        # Call extension-specific callbacks
        for callback in self.state_callbacks.get(extension_name, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(new_state)
                else:
                    callback(new_state)
            except Exception as e:
                logger.error(
                    f"Error in state callback for {extension_name}: {e}"
                )

        # Call wildcard callbacks
        for callback in self.state_callbacks.get("*", []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(extension_name, new_state)
                else:
                    callback(extension_name, new_state)
            except Exception as e:
                logger.error(f"Error in wildcard state callback: {e}")

    def get_extension_context(self, name: str) -> Optional[ExtensionContext]:
        """Get extension context.

        Args:
            name: Extension name

        Returns:
            Extension context or None
        """
        return self.loaded_extensions.get(name)

    def get_loaded_extension(self, name: str) -> Optional[Any]:
        """Get a loaded extension instance.

        Args:
            name: Extension name

        Returns:
            Extension instance or None
        """
        context = self.get_extension_context(name)
        if context:
            return context.metadata.get("instance")
        return None

    def list_loaded(self) -> list[str]:
        """List all loaded extensions.

        Returns:
            List of extension names
        """
        return list(self.loaded_extensions.keys())

    def get_status(self, name: str) -> Optional[ExtensionStatus]:
        """Get extension status.

        Args:
            name: Extension name

        Returns:
            Status object or None
        """
        context = self.get_extension_context(name)
        if not context:
            return None

        return ExtensionStatusModel(
            name=name,
            version=context.version,
            status=context.state.value,
            last_error=context.last_error,
            load_time_ms=context.load_time_ms,
        )

