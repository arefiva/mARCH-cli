"""Inter-extension communication and service discovery."""

import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Registry for services and capabilities provided by extensions."""

    def __init__(self):
        """Initialize service registry."""
        self.services: dict[str, dict[str, Any]] = {}
        self.event_bus: dict[str, list[Callable]] = {}
        self.service_lock = asyncio.Lock()

    async def register_service(
        self,
        extension_name: str,
        service_name: str,
        methods: list[str],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Register a service provided by an extension.

        Args:
            extension_name: Name of extension providing service
            service_name: Name of service
            methods: List of method names provided
            metadata: Additional metadata
        """
        async with self.service_lock:
            service_key = f"{extension_name}:{service_name}"
            self.services[service_key] = {
                "extension": extension_name,
                "name": service_name,
                "methods": methods,
                "metadata": metadata or {},
            }
            logger.info(f"Registered service {service_key} with {len(methods)} methods")

    async def unregister_service(
        self, extension_name: str, service_name: str
    ) -> bool:
        """Unregister a service.

        Args:
            extension_name: Name of extension
            service_name: Name of service

        Returns:
            True if service was registered, False otherwise
        """
        async with self.service_lock:
            service_key = f"{extension_name}:{service_name}"
            if service_key in self.services:
                del self.services[service_key]
                logger.info(f"Unregistered service {service_key}")
                return True
        return False

    def get_service(self, extension_name: str, service_name: str) -> Optional[dict[str, Any]]:
        """Get service information.

        Args:
            extension_name: Name of extension
            service_name: Name of service

        Returns:
            Service information or None
        """
        service_key = f"{extension_name}:{service_name}"
        return self.services.get(service_key)

    def find_services(self, service_name: str) -> list[dict[str, Any]]:
        """Find all services with a given name.

        Args:
            service_name: Service name

        Returns:
            List of matching services
        """
        results = []
        for service_key, service in self.services.items():
            if service["name"] == service_name:
                results.append(service)
        return results

    def find_services_by_extension(self, extension_name: str) -> list[dict[str, Any]]:
        """Find all services provided by an extension.

        Args:
            extension_name: Extension name

        Returns:
            List of services
        """
        results = []
        for service_key, service in self.services.items():
            if service["extension"] == extension_name:
                results.append(service)
        return results

    def list_all_services(self) -> list[dict[str, Any]]:
        """List all registered services.

        Returns:
            List of all services
        """
        return list(self.services.values())

    async def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to events.

        Args:
            event_type: Type of event
            handler: Handler function
        """
        if event_type not in self.event_bus:
            self.event_bus[event_type] = []
        self.event_bus[event_type].append(handler)
        logger.debug(f"Subscribed to event {event_type}")

    async def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from events.

        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if event_type in self.event_bus:
            try:
                self.event_bus[event_type].remove(handler)
                logger.debug(f"Unsubscribed from event {event_type}")
            except ValueError:
                pass

    async def publish_event(self, event_type: str, data: Any) -> None:
        """Publish an event to subscribers.

        Args:
            event_type: Type of event
            data: Event data
        """
        handlers = self.event_bus.get(event_type, [])

        logger.debug(f"Publishing event {event_type} to {len(handlers)} subscribers")

        tasks = []
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(handler(data))
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_event_subscriber_count(self, event_type: str) -> int:
        """Get number of subscribers for an event type.

        Args:
            event_type: Type of event

        Returns:
            Number of subscribers
        """
        return len(self.event_bus.get(event_type, []))

    async def clear_extension_data(self, extension_name: str) -> None:
        """Clear all data for an extension.

        Args:
            extension_name: Extension name
        """
        async with self.service_lock:
            # Remove all services for this extension
            keys_to_remove = [
                k for k, v in self.services.items()
                if v["extension"] == extension_name
            ]
            for key in keys_to_remove:
                del self.services[key]

        logger.info(f"Cleared data for extension {extension_name}")
