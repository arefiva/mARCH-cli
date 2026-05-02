"""Tests for inter-extension communication."""

import asyncio

import pytest

from mARCH.extension.discovery import ServiceRegistry


class TestServiceRegistry:
    """Test service registry."""

    @pytest.fixture
    def registry(self):
        """Create a service registry."""
        return ServiceRegistry()

    @pytest.mark.asyncio
    async def test_registry_creation(self, registry):
        """Test creating registry."""
        assert len(registry.services) == 0
        assert len(registry.event_bus) == 0

    @pytest.mark.asyncio
    async def test_register_service(self, registry):
        """Test registering service."""
        await registry.register_service(
            "ext1", "calculator", ["add", "subtract"], metadata={"version": 1}
        )

        assert "ext1:calculator" in registry.services
        service = registry.services["ext1:calculator"]
        assert service["name"] == "calculator"
        assert len(service["methods"]) == 2

    @pytest.mark.asyncio
    async def test_register_multiple_services(self, registry):
        """Test registering multiple services."""
        await registry.register_service("ext1", "service1", ["method1"])
        await registry.register_service("ext1", "service2", ["method2"])
        await registry.register_service("ext2", "service1", ["method3"])

        assert len(registry.services) == 3

    @pytest.mark.asyncio
    async def test_unregister_service(self, registry):
        """Test unregistering service."""
        await registry.register_service("ext1", "test", ["method1"])

        success = await registry.unregister_service("ext1", "test")
        assert success
        assert "ext1:test" not in registry.services

    @pytest.mark.asyncio
    async def test_unregister_nonexistent(self, registry):
        """Test unregistering nonexistent service."""
        success = await registry.unregister_service("ext1", "nonexistent")
        assert not success

    @pytest.mark.asyncio
    async def test_get_service(self, registry):
        """Test getting service."""
        await registry.register_service("ext1", "test", ["method1"])

        service = registry.get_service("ext1", "test")
        assert service is not None
        assert service["name"] == "test"

    @pytest.mark.asyncio
    async def test_get_service_not_found(self, registry):
        """Test getting nonexistent service."""
        service = registry.get_service("ext1", "nonexistent")
        assert service is None

    @pytest.mark.asyncio
    async def test_find_services(self, registry):
        """Test finding services by name."""
        await registry.register_service("ext1", "logger", ["log"])
        await registry.register_service("ext2", "logger", ["log"])
        await registry.register_service("ext1", "other", ["func"])

        results = registry.find_services("logger")
        assert len(results) == 2
        assert all(s["name"] == "logger" for s in results)

    @pytest.mark.asyncio
    async def test_find_services_by_extension(self, registry):
        """Test finding services by extension."""
        await registry.register_service("ext1", "service1", ["method1"])
        await registry.register_service("ext1", "service2", ["method2"])
        await registry.register_service("ext2", "service3", ["method3"])

        results = registry.find_services_by_extension("ext1")
        assert len(results) == 2
        assert all(s["extension"] == "ext1" for s in results)

    @pytest.mark.asyncio
    async def test_list_all_services(self, registry):
        """Test listing all services."""
        await registry.register_service("ext1", "s1", ["m1"])
        await registry.register_service("ext2", "s2", ["m2"])

        all_services = registry.list_all_services()
        assert len(all_services) == 2

    @pytest.mark.asyncio
    async def test_subscribe_event(self, registry):
        """Test subscribing to events."""
        called = []

        async def handler(data):
            called.append(data)

        await registry.subscribe("event1", handler)
        assert "event1" in registry.event_bus

    @pytest.mark.asyncio
    async def test_unsubscribe_event(self, registry):
        """Test unsubscribing from events."""
        async def handler(data):
            pass

        await registry.subscribe("event1", handler)
        await registry.unsubscribe("event1", handler)

        assert len(registry.event_bus.get("event1", [])) == 0

    @pytest.mark.asyncio
    async def test_publish_event_sync(self, registry):
        """Test publishing event with sync handler."""
        called = []

        def handler(data):
            called.append(data)

        await registry.subscribe("event1", handler)
        await registry.publish_event("event1", {"value": 42})

        assert len(called) == 1
        assert called[0]["value"] == 42

    @pytest.mark.asyncio
    async def test_publish_event_async(self, registry):
        """Test publishing event with async handler."""
        called = []

        async def handler(data):
            called.append(data)
            await asyncio.sleep(0.01)

        await registry.subscribe("event1", handler)
        await registry.publish_event("event1", {"value": 42})

        assert len(called) == 1
        assert called[0]["value"] == 42

    @pytest.mark.asyncio
    async def test_publish_event_multiple_handlers(self, registry):
        """Test publishing to multiple handlers."""
        called = []

        def handler1(data):
            called.append(("h1", data))

        def handler2(data):
            called.append(("h2", data))

        await registry.subscribe("event1", handler1)
        await registry.subscribe("event1", handler2)
        await registry.publish_event("event1", {"value": 1})

        assert len(called) == 2

    @pytest.mark.asyncio
    async def test_get_subscriber_count(self, registry):
        """Test getting subscriber count."""
        async def h1(data):
            pass

        async def h2(data):
            pass

        await registry.subscribe("event1", h1)
        await registry.subscribe("event1", h2)

        count = registry.get_event_subscriber_count("event1")
        assert count == 2

    @pytest.mark.asyncio
    async def test_clear_extension_data(self, registry):
        """Test clearing extension data."""
        await registry.register_service("ext1", "s1", ["m1"])
        await registry.register_service("ext1", "s2", ["m2"])
        await registry.register_service("ext2", "s3", ["m3"])

        await registry.clear_extension_data("ext1")

        assert len(registry.find_services_by_extension("ext1")) == 0
        assert len(registry.find_services_by_extension("ext2")) == 1
