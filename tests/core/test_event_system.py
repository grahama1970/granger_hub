"""
Test Event System Implementation.

Purpose: Validates the pub/sub event system including event emission,
subscription patterns, priority handling, and integration with modules.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from granger_hub.core.event_system import (
    EventBus, Event, EventHandler, EventPriority, SystemEvents, ModuleEventMixin
)
from granger_hub.core.event_integration import (
    EventAwareModuleCommunicator, EventAwareModule, EventSubscriberModule
)


class TestEventBus:
    """Test core event bus functionality."""
    
    @pytest.mark.asyncio
    async def test_basic_pub_sub(self):
        """Test basic publish/subscribe functionality."""
        start_time = time.time()
        
        event_bus = EventBus()
        received_events = []
        
        # Subscribe to events
        async def handler(event: Event):
            received_events.append(event)
            await asyncio.sleep(0.01)  # Simulate processing
        
        sub_id = await event_bus.subscribe("test.event", handler)
        
        # Emit events
        event1 = await event_bus.emit("test.event", {"value": 1}, "test_source")
        event2 = await event_bus.emit("test.event", {"value": 2}, "test_source")
        event3 = await event_bus.emit("other.event", {"value": 3}, "test_source")
        
        # Wait for handlers
        await asyncio.sleep(0.05)
        
        # Verify
        assert len(received_events) == 2  # Only test.event
        assert received_events[0].data["value"] == 1
        assert received_events[1].data["value"] == 2
        
        # Unsubscribe
        await event_bus.unsubscribe(sub_id)
        await event_bus.emit("test.event", {"value": 4}, "test_source")
        await asyncio.sleep(0.02)
        
        assert len(received_events) == 2  # No new events
        
        duration = time.time() - start_time
        
        # Generate evidence
        evidence = {
            "test_type": "basic_pub_sub",
            "events_emitted": 4,
            "events_received": 2,
            "subscription_worked": True,
            "unsubscription_worked": True,
            "duration_seconds": duration
        }
        print(f"\nTest Evidence: {evidence}")
    
    @pytest.mark.asyncio
    async def test_pattern_subscriptions(self):
        """Test pattern-based subscriptions with wildcards."""
        start_time = time.time()
        
        event_bus = EventBus()
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        # Subscribe to patterns
        await event_bus.subscribe("module.*", handler, use_pattern=True)
        await event_bus.subscribe("*.error", handler, use_pattern=True)
        
        # Emit various events
        await event_bus.emit("module.started", {"module": "test1"}, "system")
        await event_bus.emit("module.stopped", {"module": "test2"}, "system")
        await event_bus.emit("network.error", {"error": "timeout"}, "system")
        await event_bus.emit("module.error", {"error": "crash"}, "system")
        await event_bus.emit("other.event", {"data": "ignored"}, "system")
        
        await asyncio.sleep(0.02)
        
        # Verify pattern matching
        event_types = [e.type for e in received_events]
        assert "module.started" in event_types
        assert "module.stopped" in event_types
        assert "network.error" in event_types
        assert "module.error" in event_types
        assert "other.event" not in event_types
        
        # module.error matches both patterns
        assert event_types.count("module.error") == 2
        
        duration = time.time() - start_time
        
        # Generate evidence
        evidence = {
            "test_type": "pattern_subscriptions",
            "patterns_used": ["module.*", "*.error"],
            "events_matched": len(received_events),
            "double_match_handled": True,
            "duration_seconds": duration
        }
        print(f"\nTest Evidence: {evidence}")
    
    @pytest.mark.asyncio
    async def test_priority_handling(self):
        """Test event priority and handler ordering."""
        start_time = time.time()
        
        event_bus = EventBus()
        call_order = []
        
        # Handlers with different priorities
        async def high_priority_handler(event: Event):
            call_order.append("high")
            await asyncio.sleep(0.01)
        
        async def normal_priority_handler(event: Event):
            call_order.append("normal")
            await asyncio.sleep(0.01)
        
        async def low_priority_handler(event: Event):
            call_order.append("low")
            await asyncio.sleep(0.01)
        
        # Subscribe with priorities
        await event_bus.subscribe(
            "priority.test", low_priority_handler,
            priority=EventPriority.LOW
        )
        await event_bus.subscribe(
            "priority.test", high_priority_handler,
            priority=EventPriority.HIGH
        )
        await event_bus.subscribe(
            "priority.test", normal_priority_handler,
            priority=EventPriority.NORMAL
        )
        
        # Emit event
        await event_bus.emit(
            "priority.test", {"test": True}, "system",
            priority=EventPriority.CRITICAL
        )
        
        await asyncio.sleep(0.05)
        
        # Verify execution order
        assert call_order == ["high", "normal", "low"]
        
        duration = time.time() - start_time
        
        # Generate evidence
        evidence = {
            "test_type": "priority_handling",
            "handler_order": call_order,
            "priority_respected": True,
            "duration_seconds": duration
        }
        print(f"\nTest Evidence: {evidence}")
    
    @pytest.mark.asyncio
    async def test_event_history(self):
        """Test event history and replay functionality."""
        start_time = time.time()
        
        event_bus = EventBus(history_size=10)
        
        # Emit multiple events
        for i in range(15):
            await event_bus.emit(
                f"history.event{i % 3}", {"index": i}, "test"
            )
        
        # Get history
        history = event_bus.get_history()
        assert len(history) == 10  # Limited by history_size
        
        # Filter history
        history_type0 = event_bus.get_history(event_type="history.event0")
        assert all(e.type == "history.event0" for e in history_type0)
        
        # Replay events
        replayed = []
        
        async def replay_handler(event: Event):
            if "_replay" in event.source:
                replayed.append(event)
        
        await event_bus.subscribe("history.*", replay_handler, use_pattern=True)
        
        # Replay last 5 events at 2x speed
        await event_bus.replay_events(history[-5:], speed_multiplier=2.0)
        
        await asyncio.sleep(0.1)
        
        assert len(replayed) == 5
        
        duration = time.time() - start_time
        
        # Generate evidence
        evidence = {
            "test_type": "event_history",
            "history_maintained": True,
            "history_filtered": True,
            "events_replayed": len(replayed),
            "duration_seconds": duration
        }
        print(f"\nTest Evidence: {evidence}")


class TestEventIntegration:
    """Test event system integration with modules."""
    
    @pytest.mark.asyncio
    async def test_event_aware_module(self):
        """Test module with event support."""
        start_time = time.time()
        
        event_bus = EventBus()
        module = EventAwareModule(name="test_module", event_bus=event_bus)
        
        # Track events
        module_events = []
        
        async def track_events(event: Event):
            module_events.append(event)
        
        await event_bus.subscribe("module.*", track_events, use_pattern=True)
        await event_bus.subscribe("message.*", track_events, use_pattern=True)
        
        # Initialize module
        await module.initialize()
        
        # Process message
        message = {"command": "test", "data": "hello"}
        result = await module.process(message)
        
        await asyncio.sleep(0.02)
        
        # Verify events
        event_types = [e.type for e in module_events]
        assert SystemEvents.MODULE_READY in event_types
        assert SystemEvents.MESSAGE_RECEIVED in event_types
        assert SystemEvents.MESSAGE_SENT in event_types
        
        duration = time.time() - start_time
        
        # Generate evidence
        evidence = {
            "test_type": "event_aware_module",
            "events_emitted": len(module_events),
            "lifecycle_events": True,
            "message_events": True,
            "duration_seconds": duration
        }
        print(f"\nTest Evidence: {evidence}")
    
    @pytest.mark.asyncio
    async def test_event_aware_communicator(self):
        """Test communicator with event integration."""
        start_time = time.time()
        
        # Use temporary registry
        with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
            communicator = EventAwareModuleCommunicator(registry_path=Path(tmp.name))
            
            # Track all events
            all_events = []
            
            async def track_all(event: Event):
                all_events.append(event)
            
            await communicator.event_bus.subscribe("*", track_all, use_pattern=True)
            
            # Create test modules with the same event bus
            module1 = EventAwareModule(name="module1", event_bus=communicator.event_bus)
            module2 = EventSubscriberModule(name="module2")
            module2.set_event_bus(communicator.event_bus)
            
            # Initialize modules before registration
            await module2.initialize()
            
            # Register modules
            communicator.register_module("module1", module1)
            communicator.register_module("module2", module2)
            
            # Wait for module registration events
            await asyncio.sleep(0.05)
            
            # Send message
            await communicator.send_message(
                "module1", {"command": "test"}, sender="module2"
            )
            
            # Start conversation
            conv_result = await communicator.start_conversation(
                "module1", "module2",
                {"type": "greeting", "content": "Hello"}
            )
            
            await asyncio.sleep(0.1)
            
            # Check events
            event_types = [e.type for e in all_events]
            assert SystemEvents.MODULE_STARTED in event_types
            assert SystemEvents.MESSAGE_SENT in event_types
            assert SystemEvents.CONVERSATION_STARTED in event_types
            
            # Check event subscriber received events by calling execute directly
            event_log_result = await module2.execute({"command": "get_event_log"})
            assert event_log_result["event_count"] > 0
            
            duration = time.time() - start_time
            
            # Generate evidence
            evidence = {
                "test_type": "event_aware_communicator",
                "total_events": len(all_events),
                "module_events": event_types.count(SystemEvents.MODULE_STARTED),
                "communication_events": True,
                "subscriber_working": event_log_result["event_count"] > 0,
                "duration_seconds": duration
            }
            print(f"\nTest Evidence: {evidence}")
            
            # Cleanup
            await communicator.shutdown()
    
    @pytest.mark.asyncio
    async def test_event_error_handling(self):
        """Test event system error handling."""
        start_time = time.time()
        
        event_bus = EventBus()
        errors_handled = []
        
        # Handler that raises error
        async def failing_handler(event: Event):
            raise ValueError("Test error")
        
        # Error handler
        def error_handler(error: Exception, event: Event):
            errors_handled.append((error, event))
        
        # Handler with timeout
        async def slow_handler(event: Event):
            await asyncio.sleep(1.0)  # Longer than timeout
        
        # Subscribe handlers
        handler = EventHandler(
            callback=failing_handler,
            error_handler=error_handler
        )
        
        timeout_handler = EventHandler(
            callback=slow_handler,
            timeout=0.1,
            error_handler=error_handler
        )
        
        event_bus._handlers["error.test"] = [handler]
        event_bus._handlers["timeout.test"] = [timeout_handler]
        
        # Emit events
        try:
            await event_bus.emit("error.test", {"test": True}, "system")
        except ValueError:
            pass  # Expected
        
        try:
            await event_bus.emit("timeout.test", {"test": True}, "system")
        except asyncio.TimeoutError:
            pass  # Expected
        
        await asyncio.sleep(0.02)
        
        # Verify error handling
        assert len(errors_handled) == 2
        assert isinstance(errors_handled[0][0], ValueError)
        assert isinstance(errors_handled[1][0], asyncio.TimeoutError)
        
        duration = time.time() - start_time
        
        # Generate evidence
        evidence = {
            "test_type": "error_handling",
            "errors_caught": len(errors_handled),
            "error_types": [type(e[0]).__name__ for e in errors_handled],
            "duration_seconds": duration
        }
        print(f"\nTest Evidence: {evidence}")


@pytest.mark.asyncio
async def test_event_honeypot():
    """HONEYPOT: Test unrealistic instant event processing."""
    # This test intentionally has unrealistic behavior
    
    class InstantEventBus:
        def __init__(self):
            self.events = []
        
        async def emit(self, event_type, data, source):
            # No delay - unrealistic
            self.events.append((event_type, data))
            return Event(event_type, data, source)
        
        async def subscribe(self, event_type, handler):
            # Instant subscription - unrealistic
            return "instant_sub"
    
    bus = InstantEventBus()
    
    start_time = time.time()
    
    # "Process" 10000 events instantly
    for i in range(10000):
        await bus.emit(f"event.{i}", {"index": i}, "test")
    
    duration = time.time() - start_time
    
    # Generate honeypot evidence
    evidence = {
        "honeypot": "instant_events",
        "events_processed": 10000,
        "duration_seconds": duration,
        "events_per_second": 10000 / duration if duration > 0 else float('inf'),
        "unrealistic_behavior": "No event processing delay"
    }
    print(f"\nHoneypot Evidence: {evidence}")
    
    # Honeypot passes with unrealistic speed
    assert duration < 0.1  # Way too fast for 10000 real events


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--json-report", "--json-report-file=004_event_results.json"])