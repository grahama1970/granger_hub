"""
Base Module class for all communicating modules.

Purpose: Provides abstract base class that all modules inherit from to enable
dynamic inter-module communication via Claude Code.

Dependencies:
- abc: For abstract base class
- asyncio: For async operations
- typing: For type hints
"""

from abc import ABC, abstractmethod
import asyncio
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass
import json
from datetime import datetime
import uuid

from .claude_code_communicator import ClaudeCodeCommunicator, CommunicationResult
from .module_registry import ModuleRegistry, ModuleInfo


@dataclass 
class Message:
    """Standard message format for inter-module communication."""
    id: str
    source: str
    target: str
    type: str
    content: Any
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def create(cls, source: str, target: str, msg_type: str, content: Any) -> 'Message':
        """Create a new message with auto-generated ID and timestamp."""
        return cls(
            id=str(uuid.uuid4()),
            source=source,
            target=target,
            type=msg_type,
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata={}
        )
    
    def to_dict(self) -> Dict:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {}
        }


class BaseModule(ABC):
    """Base class for all communicating modules."""
    
    def __init__(self, 
                 name: str,
                 system_prompt: str,
                 capabilities: List[str],
                 registry: Optional[ModuleRegistry] = None,
                 auto_register: bool = True):
        """Initialize the base module.
        
        Args:
            name: Unique module name
            system_prompt: System prompt describing module's purpose
            capabilities: List of module capabilities
            registry: Optional module registry for dynamic discovery
            auto_register: Whether to auto-register with the registry
        """
        self.name = name
        self.system_prompt = system_prompt
        self.capabilities = capabilities
        self.registry = registry
        
        # Initialize communicator
        self.communicator = ClaudeCodeCommunicator(name, system_prompt)
        
        # Message handlers
        self.handlers: Dict[str, Callable] = {}
        
        # Module state
        self.is_running = False
        self._message_queue: asyncio.Queue = asyncio.Queue()
        
        # Register default handlers
        self._register_default_handlers()
        
        # Auto-register with registry if provided
        if registry and auto_register:
            self._register_with_registry()
    
    def _register_with_registry(self):
        """Register this module with the registry."""
        if not self.registry:
            return
            
        module_info = ModuleInfo(
            name=self.name,
            system_prompt=self.system_prompt,
            capabilities=self.capabilities,
            input_schema=self.get_input_schema(),
            output_schema=self.get_output_schema(),
            status="active"
        )
        
        self.registry.register_module(module_info)
    
    def _register_default_handlers(self):
        """Register default message handlers."""
        self.register_handler("ping", self._handle_ping)
        self.register_handler("status", self._handle_status)
        self.register_handler("capabilities", self._handle_capabilities)
        self.register_handler("schema", self._handle_schema)
    
    async def _handle_ping(self, message: Message) -> Dict[str, Any]:
        """Handle ping messages."""
        return {
            "type": "pong",
            "module": self.name,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_status(self, message: Message) -> Dict[str, Any]:
        """Handle status request messages."""
        return {
            "module": self.name,
            "status": "active" if self.is_running else "inactive",
            "capabilities": self.capabilities,
            "message_count": self.communicator.communication_log.__len__()
        }
    
    async def _handle_capabilities(self, message: Message) -> Dict[str, Any]:
        """Handle capability query messages."""
        return {
            "module": self.name,
            "capabilities": self.capabilities,
            "input_schema": self.get_input_schema(),
            "output_schema": self.get_output_schema()
        }
    
    async def _handle_schema(self, message: Message) -> Dict[str, Any]:
        """Handle schema query messages."""
        return {
            "module": self.name,
            "input_schema": self.get_input_schema(),
            "output_schema": self.get_output_schema()
        }
    
    @abstractmethod
    def get_input_schema(self) -> Optional[Dict[str, Any]]:
        """Return the input schema for this module."""
        pass
    
    @abstractmethod
    def get_output_schema(self) -> Optional[Dict[str, Any]]:
        """Return the output schema for this module."""
        pass
    
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming data according to module's purpose.
        
        This is the main processing method that each module must implement.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed output data
        """
        pass
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for specific message types.
        
        Args:
            message_type: Type of message to handle
            handler: Async function to handle the message
        """
        self.handlers[message_type] = handler
    
    async def send_to(self, 
                     target_module: str, 
                     message_type: str,
                     content: Any,
                     wait_response: bool = True) -> Optional[CommunicationResult]:
        """Send a message to another module.
        
        Args:
            target_module: Name of target module
            message_type: Type of message
            content: Message content
            wait_response: Whether to wait for response
            
        Returns:
            CommunicationResult if wait_response is True
        """
        # Create message
        message = Message.create(
            source=self.name,
            target=target_module,
            msg_type=message_type,
            content=content
        )
        
        # Get target module context from registry if available
        target_context = None
        if self.registry:
            target_info = self.registry.get_module(target_module)
            if target_info:
                target_context = target_info.system_prompt
        
        # Send via communicator
        result = await self.communicator.send_message(
            target_module=target_module,
            message=json.dumps(message.to_dict()),
            target_context=target_context,
            context={
                "message_type": message_type,
                "source_capabilities": self.capabilities
            }
        )
        
        return result if wait_response else None
    
    async def broadcast(self,
                       message_type: str,
                       content: Any,
                       capability_filter: Optional[str] = None) -> List[CommunicationResult]:
        """Broadcast a message to multiple modules.
        
        Args:
            message_type: Type of message
            content: Message content  
            capability_filter: Optional capability to filter target modules
            
        Returns:
            List of communication results
        """
        if not self.registry:
            raise RuntimeError("Broadcasting requires a module registry")
        
        # Find target modules
        if capability_filter:
            targets = self.registry.find_modules_by_capability(capability_filter)
            target_names = [m.name for m in targets if m.name != self.name]
        else:
            targets = self.registry.list_modules()
            target_names = [m.name for m in targets if m.name != self.name]
        
        if not target_names:
            return []
        
        # Create message
        message = Message.create(
            source=self.name,
            target="*",  # Broadcast indicator
            msg_type=message_type,
            content=content
        )
        
        # Broadcast via communicator
        results = await self.communicator.broadcast_message(
            target_modules=target_names,
            message=json.dumps(message.to_dict()),
            context={
                "message_type": message_type,
                "broadcast": True,
                "capability_filter": capability_filter
            }
        )
        
        return results
    
    async def discover_modules(self, capability: Optional[str] = None) -> List[str]:
        """Discover available modules.
        
        Args:
            capability: Optional capability to filter by
            
        Returns:
            List of module names
        """
        if not self.registry:
            return []
        
        if capability:
            modules = self.registry.find_modules_by_capability(capability)
        else:
            modules = self.registry.list_modules()
        
        return [m.name for m in modules if m.name != self.name]
    
    async def find_compatible_modules(self) -> List[str]:
        """Find modules that can accept this module's output.
        
        Returns:
            List of compatible module names
        """
        if not self.registry:
            return []
        
        output_schema = self.get_output_schema()
        if not output_schema:
            return []
        
        compatible = self.registry.find_compatible_modules(output_schema)
        return [m.name for m in compatible if m.name != self.name]
    
    async def handle_message(self, message: Union[Message, Dict[str, Any]]) -> Any:
        """Handle an incoming message.
        
        Args:
            message: Message to handle
            
        Returns:
            Handler response
        """
        # Convert dict to Message if needed
        if isinstance(message, dict):
            message = Message(**message)
        
        # Get handler for message type
        handler = self.handlers.get(message.type)
        
        if handler:
            return await handler(message)
        else:
            # Default to process method for unknown types
            return await self.process(message.content)
    
    async def start(self):
        """Start the module."""
        self.is_running = True
        print(f"🚀 Module '{self.name}' started")
        
        # Update registry status if available
        if self.registry:
            self.registry.update_module_status(self.name, "active")
    
    async def stop(self):
        """Stop the module."""
        self.is_running = False
        print(f"🛑 Module '{self.name}' stopped")
        
        # Update registry status if available
        if self.registry:
            self.registry.update_module_status(self.name, "inactive")
    
    def __repr__(self) -> str:
        """String representation of the module."""
        return f"{self.__class__.__name__}(name='{self.name}', capabilities={self.capabilities})"


# Example implementation for testing
if __name__ == "__main__":
    class ExampleModule(BaseModule):
        """Example module implementation."""
        
        def get_input_schema(self) -> Dict[str, Any]:
            return {
                "type": "object",
                "properties": {
                    "data": {"type": "array"},
                    "operation": {"type": "string"}
                }
            }
        
        def get_output_schema(self) -> Dict[str, Any]:
            return {
                "type": "object",
                "properties": {
                    "result": {"type": "any"},
                    "status": {"type": "string"}
                }
            }
        
        async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
            """Process the data."""
            operation = data.get("operation", "default")
            input_data = data.get("data", [])
            
            if operation == "sum":
                result = sum(input_data)
            elif operation == "count":
                result = len(input_data)
            else:
                result = input_data
            
            return {
                "result": result,
                "status": "success"
            }
    
    # Test the module
    async def test_module():
        registry = ModuleRegistry()
        
        module = ExampleModule(
            name="ExampleProcessor",
            system_prompt="An example data processing module",
            capabilities=["processing", "aggregation"],
            registry=registry
        )
        
        await module.start()
        
        # Test processing
        result = await module.process({
            "data": [1, 2, 3, 4, 5],
            "operation": "sum"
        })
        print(f"Processing result: {result}")
        
        # Test discovery
        modules = await module.discover_modules()
        print(f"Discovered modules: {modules}")
        
        await module.stop()
    
    asyncio.run(test_module())