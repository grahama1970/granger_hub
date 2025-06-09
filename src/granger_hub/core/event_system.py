"""
Event System for Granger Hub.

Purpose: Provides a pub/sub event system for decoupled module communication,
enabling modules to react to system-wide events without direct dependencies.

External Dependencies: None

Example Usage:
>>> event_bus = EventBus()
>>> await event_bus.subscribe("module.started", my_handler)
>>> await event_bus.emit("module.started", {"module": "test", "time": datetime.now()})
"""

import asyncio
import weakref
from typing import Dict, Any, Callable, List, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from collections import defaultdict
import fnmatch
import uuid

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """Represents a system event."""
    type: str
    data: Dict[str, Any]
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: EventPriority = EventPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches_pattern(self, pattern: str) -> bool:
        """Check if event type matches a pattern (supports wildcards)."""
        return fnmatch.fnmatch(self.type, pattern)


@dataclass
class EventHandler:
    """Wrapper for event handler functions."""
    callback: Callable
    filter: Optional[Callable[[Event], bool]] = None
    priority: EventPriority = EventPriority.NORMAL
    max_concurrency: int = 1
    timeout: Optional[float] = None
    error_handler: Optional[Callable[[Exception, Event], None]] = None
    
    async def handle(self, event: Event) -> Any:
        """Handle an event with error handling and timeout."""
        try:
            # Apply filter if provided
            if self.filter and not self.filter(event):
                return None
            
            # Execute with timeout if specified
            if self.timeout:
                return await asyncio.wait_for(
                    self.callback(event),
                    timeout=self.timeout
                )
            else:
                return await self.callback(event)
                
        except asyncio.TimeoutError:
            logger.warning(f"Handler timeout for event {event.type}")
            if self.error_handler:
                self.error_handler(asyncio.TimeoutError("Handler timeout"), event)
            raise
        except Exception as e:
            logger.error(f"Handler error for event {event.type}: {e}")
            if self.error_handler:
                self.error_handler(e, event)
            raise


class EventBus:
    """
    Central event bus for pub/sub communication.
    
    Features:
    - Pattern-based subscriptions (wildcards)
    - Priority-based event delivery
    - Concurrent handler execution
    - Event history and replay
    - Weak references to prevent memory leaks
    """
    
    def __init__(self, history_size: int = 1000, enable_history: bool = True):
        """
        Initialize event bus.
        
        Args:
            history_size: Maximum number of events to keep in history
            enable_history: Whether to maintain event history
        """
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._pattern_handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._history: List[Event] = []
        self._history_size = history_size
        self._enable_history = enable_history
        self._active_handlers: Dict[str, int] = defaultdict(int)
        self._subscribers: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._running = True
    
    async def subscribe(self, event_type: str, handler: Callable,
                       filter: Optional[Callable[[Event], bool]] = None,
                       priority: EventPriority = EventPriority.NORMAL,
                       use_pattern: bool = False,
                       **kwargs) -> str:
        """
        Subscribe to events.
        
        Args:
            event_type: Event type or pattern (if use_pattern=True)
            handler: Async function to handle events
            filter: Optional filter function
            priority: Handler priority
            use_pattern: Whether event_type is a pattern with wildcards
            **kwargs: Additional handler options
            
        Returns:
            Subscription ID for unsubscribing
        """
        handler_wrapper = EventHandler(
            callback=handler,
            filter=filter,
            priority=priority,
            **kwargs
        )
        
        # Store handler
        if use_pattern:
            self._pattern_handlers[event_type].append(handler_wrapper)
        else:
            self._handlers[event_type].append(handler_wrapper)
        
        # Sort by priority
        if use_pattern:
            self._pattern_handlers[event_type].sort(
                key=lambda h: h.priority.value, reverse=True
            )
        else:
            self._handlers[event_type].sort(
                key=lambda h: h.priority.value, reverse=True
            )
        
        # Generate subscription ID
        sub_id = f"{event_type}:{id(handler)}"
        self._subscribers[sub_id] = handler_wrapper
        
        logger.debug(f"Subscribed to {event_type} (pattern={use_pattern})")
        return sub_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: Subscription ID from subscribe()
            
        Returns:
            True if unsubscribed successfully
        """
        if subscription_id not in self._subscribers:
            return False
        
        handler = self._subscribers[subscription_id]
        event_type = subscription_id.split(":")[0]
        
        # Remove from appropriate list
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
            if not self._handlers[event_type]:
                del self._handlers[event_type]
        elif event_type in self._pattern_handlers:
            self._pattern_handlers[event_type].remove(handler)
            if not self._pattern_handlers[event_type]:
                del self._pattern_handlers[event_type]
        
        del self._subscribers[subscription_id]
        logger.debug(f"Unsubscribed from {event_type}")
        return True
    
    async def emit(self, event_type: str, data: Dict[str, Any],
                   source: str, priority: EventPriority = EventPriority.NORMAL,
                   **metadata) -> Event:
        """
        Emit an event.
        
        Args:
            event_type: Type of event
            data: Event data
            source: Source module/component
            priority: Event priority
            **metadata: Additional metadata
            
        Returns:
            The emitted event
        """
        if not self._running:
            raise RuntimeError("Event bus is not running")
        
        # Create event
        event = Event(
            type=event_type,
            data=data,
            source=source,
            priority=priority,
            metadata=metadata
        )
        
        # Add to history
        if self._enable_history:
            self._history.append(event)
            if len(self._history) > self._history_size:
                self._history.pop(0)
        
        # Gather all matching handlers
        handlers = []
        
        # Direct subscribers
        if event_type in self._handlers:
            handlers.extend(self._handlers[event_type])
        
        # Pattern subscribers
        for pattern, pattern_handlers in self._pattern_handlers.items():
            if event.matches_pattern(pattern):
                handlers.extend(pattern_handlers)
        
        # Sort by priority
        handlers.sort(key=lambda h: h.priority.value, reverse=True)
        
        # Execute handlers
        await self._execute_handlers(handlers, event)
        
        logger.debug(f"Emitted event: {event_type} from {source}")
        return event
    
    async def _execute_handlers(self, handlers: List[EventHandler], event: Event):
        """Execute handlers with concurrency control."""
        tasks = []
        
        for handler in handlers:
            # Check concurrency limit
            handler_id = id(handler)
            if self._active_handlers[handler_id] >= handler.max_concurrency:
                logger.warning(
                    f"Handler concurrency limit reached for {event.type}"
                )
                continue
            
            # Track active handler
            self._active_handlers[handler_id] += 1
            
            # Create task
            task = asyncio.create_task(self._run_handler(handler, event))
            tasks.append(task)
        
        # Wait for all handlers
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _run_handler(self, handler: EventHandler, event: Event):
        """Run a single handler with cleanup."""
        handler_id = id(handler)
        try:
            await handler.handle(event)
        finally:
            self._active_handlers[handler_id] -= 1
    
    def get_history(self, event_type: Optional[str] = None,
                    source: Optional[str] = None,
                    since: Optional[datetime] = None) -> List[Event]:
        """
        Get event history with optional filtering.
        
        Args:
            event_type: Filter by event type/pattern
            source: Filter by source
            since: Filter by timestamp
            
        Returns:
            Filtered event history
        """
        history = self._history.copy()
        
        if event_type:
            history = [e for e in history if e.matches_pattern(event_type)]
        
        if source:
            history = [e for e in history if e.source == source]
        
        if since:
            history = [e for e in history if e.timestamp >= since]
        
        return history
    
    async def replay_events(self, events: List[Event],
                           speed_multiplier: float = 1.0):
        """
        Replay historical events.
        
        Args:
            events: Events to replay
            speed_multiplier: Speed up/slow down replay
        """
        if not events:
            return
        
        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        # Replay with timing
        start_time = sorted_events[0].timestamp
        
        for i, event in enumerate(sorted_events):
            # Calculate delay
            if i > 0:
                time_diff = (event.timestamp - sorted_events[i-1].timestamp).total_seconds()
                delay = time_diff / speed_multiplier
                if delay > 0:
                    await asyncio.sleep(delay)
            
            # Re-emit event
            await self.emit(
                event.type,
                event.data,
                f"{event.source}_replay",
                event.priority,
                **event.metadata
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        stats = {
            "total_events": len(self._history),
            "active_handlers": sum(self._active_handlers.values()),
            "subscriptions": {
                "direct": sum(len(h) for h in self._handlers.values()),
                "pattern": sum(len(h) for h in self._pattern_handlers.values())
            },
            "event_types": list(self._handlers.keys()),
            "patterns": list(self._pattern_handlers.keys())
        }
        
        # Event type frequency
        if self._history:
            from collections import Counter
            event_counts = Counter(e.type for e in self._history)
            stats["most_common_events"] = event_counts.most_common(10)
        
        return stats
    
    async def shutdown(self):
        """Shutdown event bus gracefully."""
        self._running = False
        
        # Wait for active handlers
        max_wait = 10  # seconds
        start = asyncio.get_event_loop().time()
        
        while sum(self._active_handlers.values()) > 0:
            if asyncio.get_event_loop().time() - start > max_wait:
                logger.warning("Timeout waiting for handlers to complete")
                break
            await asyncio.sleep(0.1)
        
        # Clear handlers
        self._handlers.clear()
        self._pattern_handlers.clear()
        self._subscribers.clear()


class ModuleEventMixin:
    """
    Mixin to add event capabilities to modules.
    
    Provides convenient methods for modules to emit and subscribe to events.
    """
    
    def __init__(self, *args, event_bus: Optional[EventBus] = None, **kwargs):
        """Initialize with optional event bus."""
        super().__init__(*args, **kwargs)
        self._event_bus = event_bus
        self._event_subscriptions: List[str] = []
    
    def set_event_bus(self, event_bus: EventBus):
        """Set the event bus for this module."""
        self._event_bus = event_bus
    
    async def emit_event(self, event_type: str, data: Dict[str, Any], **metadata):
        """Emit an event from this module."""
        if not self._event_bus:
            return
        
        source = getattr(self, 'name', self.__class__.__name__)
        await self._event_bus.emit(event_type, data, source, **metadata)
    
    async def subscribe_event(self, event_type: str, handler: Callable, **kwargs):
        """Subscribe to events."""
        if not self._event_bus:
            return
        
        sub_id = await self._event_bus.subscribe(event_type, handler, **kwargs)
        self._event_subscriptions.append(sub_id)
        return sub_id
    
    async def cleanup_events(self):
        """Unsubscribe from all events."""
        if not self._event_bus:
            return
        
        for sub_id in self._event_subscriptions:
            await self._event_bus.unsubscribe(sub_id)
        self._event_subscriptions.clear()


# Common event types
class SystemEvents:
    """Standard system event types."""
    # Module lifecycle
    MODULE_STARTED = "module.started"
    MODULE_STOPPED = "module.stopped"
    MODULE_ERROR = "module.error"
    MODULE_READY = "module.ready"
    
    # Communication
    MESSAGE_SENT = "message.sent"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_ERROR = "message.error"
    
    # Conversation
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_MESSAGE = "conversation.message"
    CONVERSATION_ENDED = "conversation.ended"
    
    # Binary transfer
    TRANSFER_STARTED = "transfer.started"
    TRANSFER_PROGRESS = "transfer.progress"
    TRANSFER_COMPLETED = "transfer.completed"
    TRANSFER_FAILED = "transfer.failed"
    
    # System
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    CONFIG_CHANGED = "config.changed"


# Validation
if __name__ == "__main__":
    import time
    
    async def test_event_system():
        """Test event system functionality."""
        event_bus = EventBus()
        
        # Track received events
        received_events = []
        
        # Test handler
        async def test_handler(event: Event):
            received_events.append(event)
            await asyncio.sleep(0.01)  # Simulate work
        
        # Subscribe to events
        sub1 = await event_bus.subscribe("test.event", test_handler)
        sub2 = await event_bus.subscribe("test.*", test_handler, use_pattern=True)
        
        # Emit events
        await event_bus.emit("test.event", {"value": 1}, "test_source")
        await event_bus.emit("test.other", {"value": 2}, "test_source")
        await event_bus.emit("other.event", {"value": 3}, "test_source")
        
        # Wait for handlers
        await asyncio.sleep(0.1)
        
        # Check results
        assert len(received_events) == 3  # test.event (x2) + test.other
        assert received_events[0].data["value"] == 1
        assert received_events[1].data["value"] == 1  # Duplicate from pattern
        assert received_events[2].data["value"] == 2
        
        # Test unsubscribe
        await event_bus.unsubscribe(sub1)
        received_events.clear()
        
        await event_bus.emit("test.event", {"value": 4}, "test_source")
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 1  # Only pattern handler
        
        # Test statistics
        stats = event_bus.get_statistics()
        assert stats["total_events"] == 4
        assert "test.event" in [e[0] for e in stats["most_common_events"]]
        
        print(" Event system validation passed!")
        return True
    
    # Run test
    result = asyncio.run(test_event_system())
    assert result == True