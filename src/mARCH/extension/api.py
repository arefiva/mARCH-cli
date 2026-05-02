"""Extension API - stable interface for extensions."""

from typing import Any, Callable, Optional

from .contracts import ExtensionManifest, ExtensionStatus


class ExtensionAPI:
    """Provides the stable API surface for extensions.

    This is the interface extensions use to interact with mARCH.
    """

    def __init__(self, extension_name: str, manifest: ExtensionManifest):
        """Initialize extension API.

        Args:
            extension_name: Name of the extension
            manifest: Extension manifest
        """
        self.name = extension_name
        self.manifest = manifest
        self._event_handlers: dict[str, list[Callable]] = {}

    def log(self, message: str, level: str = "info") -> None:
        """Log a message from the extension.

        Args:
            message: Message to log
            level: Log level (debug, info, warning, error)
        """
        # TODO: Implement logging integration
        pass

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register an event handler.

        Args:
            event_type: Type of event to handle
            handler: Callable to handle the event
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def emit_event(self, event_type: str, data: Any) -> None:
        """Emit an event that other extensions can listen to.

        Args:
            event_type: Type of event
            data: Event data
        """
        # TODO: Implement event bus integration
        pass

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get extension configuration value.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value
        """
        # TODO: Implement config retrieval
        return default

    def get_status(self) -> ExtensionStatus:
        """Get current status of this extension.

        Returns:
            Extension status
        """
        # TODO: Implement status retrieval
        return ExtensionStatus(
            name=self.name,
            version=self.manifest.version,
            status="active",
        )
