"""
Event System Integration for Module Communicator.

Purpose: Integrates the event system with the module communicator,
enabling event-driven communication patterns between modules.

Example Usage:
>>> communicator = EventAwareModuleCommunicator()
>>> await communicator.register_module(my_module)
>>> # Module lifecycle events are automatically emitted
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from .module_communicator import ModuleCommunicator
from .event_system import EventBus, SystemEvents, Event, EventPriority, ModuleEventMixin
from .modules.base_module import BaseModule
from .conversation.conversation_message import ConversationMessage
from pathlib import Path
import logging


class EventAwareModule(BaseModule, ModuleEventMixin):
    """Base module with integrated event support."""
    
    def __init__(self, name: str, system_prompt: str = "Event-aware module",
                 capabilities: Optional[Dict[str, Any]] = None,
                 event_bus: Optional[EventBus] = None, **kwargs):
        """Initialize with event support."""
        # Initialize BaseModule
        BaseModule.__init__(self, name, system_prompt, capabilities or {}, **kwargs)
        # Initialize event mixin
        ModuleEventMixin.__init__(self, event_bus=event_bus)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema."""
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "data": {"type": "object"}
            }
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output schema."""
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "result": {"type": "object"}
            }
        }
    
    async def execute(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Default execute implementation."""
        return {"status": "success", "result": message}
    
    async def initialize(self):
        """Initialize module and emit ready event."""
        # BaseModule doesn't have initialize, so we just emit the event
        await self.emit_event(SystemEvents.MODULE_READY, {
            "module": self.name,
            "capabilities": self.capabilities
        })
    
    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process message with event emission."""
        # Emit received event
        await self.emit_event(SystemEvents.MESSAGE_RECEIVED, {
            "module": self.name,
            "message": message
        })
        
        # Process message
        try:
            result = await self.execute(message)
            
            # Emit sent event
            await self.emit_event(SystemEvents.MESSAGE_SENT, {
                "module": self.name,
                "message": result
            })
            
            return result
            
        except Exception as e:
            # Emit error event
            await self.emit_event(SystemEvents.MODULE_ERROR, {
                "module": self.name,
                "error": str(e),
                "message": message
            }, priority=EventPriority.HIGH)
            raise
    
    async def cleanup(self):
        """Cleanup module and unsubscribe from events."""
        await self.cleanup_events()
        await super().cleanup()


class EventAwareModuleCommunicator(ModuleCommunicator):
    """
    Module communicator with integrated event system.
    
    Automatically emits events for:
    - Module registration/unregistration
    - Message routing
    - Conversation lifecycle
    - Binary transfers
    - System errors
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None, registry_path: Optional[Path] = None):
        """Initialize with event bus."""
        super().__init__(registry_path=registry_path)
        self.event_bus = event_bus or EventBus()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_internal_subscriptions()
    
    def _setup_internal_subscriptions(self):
        """Setup internal event subscriptions."""
        # Subscribe to module errors for logging
        asyncio.create_task(
            self.event_bus.subscribe(
                SystemEvents.MODULE_ERROR,
                self._handle_module_error,
                priority=EventPriority.HIGH
            )
        )
    
    async def _handle_module_error(self, event: Event):
        """Handle module error events."""
        module_name = event.data.get("module", "unknown")
        error = event.data.get("error", "unknown error")
        self.logger.error(f"Module {module_name} error: {error}")
    
    def register_module(self, name: str, module: BaseModule) -> bool:
        """Register module with event emission."""
        # Set event bus if module supports it
        if hasattr(module, 'set_event_bus'):
            module.set_event_bus(self.event_bus)
        
        # Register module
        result = super().register_module(name, module)
        
        # Emit registration event synchronously in a task
        async def emit_started():
            await self.event_bus.emit(
                SystemEvents.MODULE_STARTED,
                {
                    "module": name,
                    "type": module.__class__.__name__,
                    "capabilities": getattr(module, 'capabilities', {})
                },
                source="communicator"
            )
        
        # Create task but don't wait
        asyncio.create_task(emit_started())
        
        return result
    
    async def unregister_module(self, module_name: str):
        """Unregister module with event emission."""
        # Emit stopping event
        await self.event_bus.emit(
            SystemEvents.MODULE_STOPPED,
            {"module": module_name},
            source="communicator"
        )
        
        # Unregister module
        await super().unregister_module(module_name)
    
    async def send_message(self, target: str, message: Dict[str, Any],
                          sender: Optional[str] = None) -> Dict[str, Any]:
        """Send message with event emission."""
        # Emit sending event
        await self.event_bus.emit(
            SystemEvents.MESSAGE_SENT,
            {
                "sender": sender or "communicator",
                "target": target,
                "message": message
            },
            source="communicator"
        )
        
        try:
            # Send message
            result = await super().send_message(target, message, sender)
            
            # Emit received event
            await self.event_bus.emit(
                SystemEvents.MESSAGE_RECEIVED,
                {
                    "sender": target,
                    "target": sender or "communicator",
                    "message": result
                },
                source="communicator"
            )
            
            return result
            
        except Exception as e:
            # Emit error event
            await self.event_bus.emit(
                SystemEvents.MESSAGE_ERROR,
                {
                    "sender": sender or "communicator",
                    "target": target,
                    "error": str(e),
                    "message": message
                },
                source="communicator",
                priority=EventPriority.HIGH
            )
            raise
    
    async def start_conversation(self, initiator: str, target: str,
                               initial_message: Dict[str, Any],
                               conversation_type: str = "task") -> Dict[str, Any]:
        """Start conversation with event emission."""
        # Start conversation
        result = await super().start_conversation(
            initiator, target, initial_message, conversation_type
        )
        
        # Emit conversation started event
        await self.event_bus.emit(
            SystemEvents.CONVERSATION_STARTED,
            {
                "conversation_id": result["conversation_id"],
                "initiator": initiator,
                "target": target,
                "type": conversation_type
            },
            source="communicator"
        )
        
        return result
    
    async def _monitor_conversation(self, conversation_id: str):
        """Monitor conversation with event emission."""
        # Get conversation
        conversation = self.conversation_manager.conversations.get(conversation_id)
        if not conversation:
            return
        
        timeout = 300  # 5 minutes
        check_interval = 30  # 30 seconds
        start_time = asyncio.get_event_loop().time()
        
        while conversation_id in self.conversation_manager.conversations:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                self.logger.warning(f"Conversation {conversation_id} timed out")
                
                # Emit timeout event
                await self.event_bus.emit(
                    SystemEvents.CONVERSATION_ENDED,
                    {
                        "conversation_id": conversation_id,
                        "reason": "timeout",
                        "duration": elapsed
                    },
                    source="communicator",
                    priority=EventPriority.HIGH
                )
                
                # End conversation
                await self.conversation_manager.end_conversation(
                    conversation_id, "timeout"
                )
                break
            
            # Emit progress event
            history = await self.conversation_manager.get_conversation_history(
                conversation_id
            )
            if history:
                await self.event_bus.emit(
                    SystemEvents.CONVERSATION_MESSAGE,
                    {
                        "conversation_id": conversation_id,
                        "message_count": len(history),
                        "last_participant": history[-1].get("participant", "unknown") if isinstance(history[-1], dict) else history[-1].participant,
                        "elapsed": elapsed
                    },
                    source="communicator"
                )
            
            await asyncio.sleep(check_interval)
        
        # Emit ended event if not already emitted
        if conversation_id not in self.conversation_manager.conversations:
            history = await self.conversation_manager.get_conversation_history(
                conversation_id
            )
            await self.event_bus.emit(
                SystemEvents.CONVERSATION_ENDED,
                {
                    "conversation_id": conversation_id,
                    "reason": "completed",
                    "message_count": len(history) if history else 0,
                    "duration": asyncio.get_event_loop().time() - start_time
                },
                source="communicator"
            )
    
    async def shutdown(self):
        """Shutdown with event emission."""
        # Emit shutdown event
        await self.event_bus.emit(
            SystemEvents.SYSTEM_SHUTDOWN,
            {"timestamp": datetime.now().isoformat()},
            source="communicator",
            priority=EventPriority.CRITICAL
        )
        
        # Close any active conversations
        for conv_id in list(self.conversation_manager.conversations.keys()):
            await self.conversation_manager.end_conversation(conv_id)
        
        # Shutdown event bus
        await self.event_bus.shutdown()
        
        # Note: Skipping registry save as it's handled internally


class EventSubscriberModule(EventAwareModule):
    """
    Example module that subscribes to system events.
    
    Demonstrates how modules can react to system-wide events
    without direct coupling to other modules.
    """
    
    def __init__(self, name: str = "event_subscriber"):
        """Initialize event subscriber."""
        super().__init__(name=name)
        self.event_log = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def initialize(self):
        """Initialize and subscribe to events."""
        await super().initialize()
        
        # Subscribe to all module events
        await self.subscribe_event(
            "module.*",
            self._handle_module_event,
            use_pattern=True
        )
        
        # Subscribe to conversation events
        await self.subscribe_event(
            "conversation.*",
            self._handle_conversation_event,
            use_pattern=True
        )
    
    async def _handle_module_event(self, event: Event):
        """Handle module lifecycle events."""
        self.event_log.append({
            "type": "module",
            "event": event.type,
            "data": event.data,
            "timestamp": event.timestamp
        })
        
        # React to specific events
        if event.type == SystemEvents.MODULE_STARTED:
            module_name = event.data.get("module")
            if module_name != self.name:
                self.logger.info(f"Module {module_name} started")
    
    async def _handle_conversation_event(self, event: Event):
        """Handle conversation events."""
        self.event_log.append({
            "type": "conversation",
            "event": event.type,
            "data": event.data,
            "timestamp": event.timestamp
        })
        
        # React to conversation completion
        if event.type == SystemEvents.CONVERSATION_ENDED:
            conv_id = event.data.get("conversation_id")
            duration = event.data.get("duration", 0)
            self.logger.info(
                f"Conversation {conv_id} ended after {duration:.1f}s"
            )
    
    async def execute(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process messages."""
        command = message.get("command", "")
        
        if command == "get_event_log":
            return {
                "status": "success",
                "event_count": len(self.event_log),
                "recent_events": self.event_log[-10:]  # Last 10 events
            }
        
        return {"status": "success", "message": "Event subscriber active"}


# Create convenience functions
def create_event_aware_communicator() -> EventAwareModuleCommunicator:
    """Create a module communicator with event support."""
    return EventAwareModuleCommunicator()


def create_event_aware_module(name: str, **kwargs) -> EventAwareModule:
    """Create a module with event support."""
    return EventAwareModule(name=name, **kwargs)