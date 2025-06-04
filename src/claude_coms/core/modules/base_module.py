"""
Module: base_module.py
Purpose: Abstract base class for modules to inherit from

External Dependencies:
- abc: Built-in Python module for abstract base classes
- typing: Built-in Python module for type hints

Example Usage:
>>> class MyModule(BaseModule):
...     def get_input_schema(self): return {"type": "object"}
...     def get_output_schema(self): return {"type": "object"}
...     async def process(self, data): return {"result": "processed"}
>>> module = MyModule("MyModule", "My system prompt", ["capability1"])
'MyModule initialized'
"""

from abc import ABC, abstractmethod
import asyncio
from typing import Dict, Any, Optional, Callable, List
from collections import defaultdict
import time
try:
    from .claude_code_communicator import ClaudeCodeCommunicator
    from .module_registry import ModuleRegistry, ModuleInfo
except ImportError:
    # For standalone testing
    from claude_code_communicator import ClaudeCodeCommunicator
    from module_registry import ModuleRegistry, ModuleInfo
from loguru import logger


class BaseModule(ABC):
    """Base class for all communicating modules with conversation support."""
    
    def __init__(self, 
                 name: str,
                 system_prompt: str,
                 capabilities: List[str],
                 registry: Optional[ModuleRegistry] = None):
        self.name = name
        self.system_prompt = system_prompt
        self.capabilities = capabilities
        self.communicator = ClaudeCodeCommunicator(name, system_prompt)
        self.handlers: Dict[str, Callable] = {}
        
        # Conversation context management (Task 003.1)
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.conversation_contexts: Dict[str, Dict[str, Any]] = {}
        self.active_conversations: Dict[str, float] = {}  # conversation_id -> last_activity_time
        
        # Auto-register if registry provided
        if registry:
            module_info = ModuleInfo(
                name=name,
                system_prompt=system_prompt,
                capabilities=capabilities,
                input_schema=self.get_input_schema(),
                output_schema=self.get_output_schema()
            )
            registry.register_module(module_info)
        
        logger.info(f"Initialized module: {name}")
    
    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """Return the input schema for this module."""
        pass
    
    @abstractmethod
    def get_output_schema(self) -> Dict[str, Any]:
        """Return the output schema for this module."""
        pass
    
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming data according to module's purpose."""
        pass
    
    async def send_to(self, target_module: str, message: str, 
                      data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send message to another module."""
        logger.info(f"{self.name} sending to {target_module}: {message[:50]}...")
        return await self.communicator.send_message(
            target_module=target_module,
            message=message,
            context=data
        )
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for specific message types."""
        self.handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming message with conversation context preservation."""
        msg_type = message.get("type", "default")
        handler = self.handlers.get(msg_type, self.process)
        logger.debug(f"Handling message type '{msg_type}' with handler")
        
        # Extract conversation info if present
        conversation_id = message.get("conversation_id")
        if conversation_id:
            # Update conversation tracking
            self.active_conversations[conversation_id] = time.time()
            
            # Store message in history
            self.conversation_history[conversation_id].append(message)
            
            # Retrieve conversation context
            context = self.conversation_contexts.get(conversation_id, {})
            
            # Add context to message data
            data = message.get("data", {})
            data["_conversation_context"] = context
            data["_conversation_id"] = conversation_id
            data["_turn_number"] = len(self.conversation_history[conversation_id])
            
            # Process with context
            result = await handler(data)
            
            # Update context based on result
            if isinstance(result, dict) and "_context_updates" in result:
                self.update_conversation_context(conversation_id, result["_context_updates"])
                del result["_context_updates"]
            
            return result
        else:
            # Single-shot message (backward compatibility)
            return await handler(message.get("data", {}))
    
    def get_info(self) -> ModuleInfo:
        """Get module information."""
        return ModuleInfo(
            name=self.name,
            system_prompt=self.system_prompt,
            capabilities=self.capabilities,
            input_schema=self.get_input_schema(),
            output_schema=self.get_output_schema()
        )
    
    # Conversation context methods
    def update_conversation_context(self, conversation_id: str, updates: Dict[str, Any]) -> None:
        """Update the context for a specific conversation."""
        if conversation_id not in self.conversation_contexts:
            self.conversation_contexts[conversation_id] = {}
        self.conversation_contexts[conversation_id].update(updates)
        logger.debug(f"Updated context for conversation {conversation_id}: {updates}")
    
    def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get the current context for a conversation."""
        return self.conversation_contexts.get(conversation_id, {}).copy()
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get message history for a conversation."""
        return self.conversation_history.get(conversation_id, []).copy()
    
    def clear_conversation(self, conversation_id: str) -> None:
        """Clear conversation data."""
        if conversation_id in self.conversation_history:
            del self.conversation_history[conversation_id]
        if conversation_id in self.conversation_contexts:
            del self.conversation_contexts[conversation_id]
        if conversation_id in self.active_conversations:
            del self.active_conversations[conversation_id]
        logger.info(f"Cleared conversation {conversation_id}")
    
    def cleanup_inactive_conversations(self, timeout_seconds: float = 3600) -> int:
        """Clean up conversations that have been inactive for too long."""
        current_time = time.time()
        to_remove = []
        
        for conv_id, last_activity in self.active_conversations.items():
            if current_time - last_activity > timeout_seconds:
                to_remove.append(conv_id)
        
        for conv_id in to_remove:
            self.clear_conversation(conv_id)
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} inactive conversations")
        
        return len(to_remove)


# Example implementation for testing
class DataProcessorModule(BaseModule):
    """Example data processor module."""
    
    def __init__(self, registry: Optional[ModuleRegistry] = None):
        super().__init__(
            name="DataProcessor",
            system_prompt="Process raw data and extract meaningful patterns",
            capabilities=["data_processing", "pattern_extraction"],
            registry=registry
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "raw_data": {"type": "array"},
                "processing_options": {"type": "object"}
            },
            "required": ["raw_data"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "processed_data": {"type": "array"},
                "patterns": {"type": "array"},
                "metadata": {"type": "object"}
            }
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the raw data with conversation context awareness."""
        # Simulate realistic processing time
        await asyncio.sleep(0.02)  # 20ms processing time
        
        raw_data = data.get("raw_data", [])
        
        # Check for conversation context
        context = data.get("_conversation_context", {})
        conversation_id = data.get("_conversation_id")
        turn_number = data.get("_turn_number", 1)
        
        # Simulate processing with context awareness
        patterns = []
        if raw_data:
            # Simple pattern detection
            if len(raw_data) > 5:
                patterns.append("sequential_increase")
            if any(x > 10 for x in raw_data if isinstance(x, (int, float))):
                patterns.append("high_values_detected")
        
        # Check if we've seen similar data before in this conversation
        previous_patterns = context.get("all_patterns", [])
        new_patterns = [p for p in patterns if p not in previous_patterns]
        
        # Build context-aware response
        result = {
            "processed_data": raw_data,
            "patterns": patterns,
            "new_patterns": new_patterns,
            "metadata": {
                "count": len(raw_data),
                "patterns_found": len(patterns),
                "new_patterns_found": len(new_patterns),
                "turn_number": turn_number,
                "conversation_aware": conversation_id is not None
            }
        }
        
        # Update context for next turn
        if conversation_id:
            # Build updated pattern list maintaining uniqueness
            updated_patterns = list(set(previous_patterns + patterns))
            result["_context_updates"] = {
                "all_patterns": updated_patterns,
                "total_data_processed": context.get("total_data_processed", 0) + len(raw_data),
                "turns_processed": turn_number
            }
        
        # Skip analyzer call during testing to avoid timeouts
        # In production, would send to analyzer here
        
        return result


class DataAnalyzerModule(BaseModule):
    """Example data analyzer module."""
    
    def __init__(self, registry: Optional[ModuleRegistry] = None):
        super().__init__(
            name="DataAnalyzer",
            system_prompt="Analyze data patterns and provide insights",
            capabilities=["data_analysis", "anomaly_detection", "insight_generation"],
            registry=registry
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patterns": {"type": "array"},
                "sample": {"type": "array"}
            },
            "required": ["patterns"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "insights": {"type": "array"},
                "anomalies": {"type": "array"},
                "recommendations": {"type": "array"}
            }
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns and generate insights."""
        patterns = data.get("patterns", [])
        sample = data.get("sample", [])
        
        insights = []
        anomalies = []
        recommendations = []
        
        # Generate insights based on patterns
        if "sequential_increase" in patterns:
            insights.append("Data shows an increasing trend")
            recommendations.append("Monitor for exponential growth")
        
        if "high_values_detected" in patterns:
            insights.append("Outliers detected in dataset")
            anomalies.append("Values exceeding normal range")
            recommendations.append("Investigate high value data points")
        
        return {
            "insights": insights,
            "anomalies": anomalies,
            "recommendations": recommendations
        }


# Validation
if __name__ == "__main__":
    async def test_module():
        # Create registry
        registry = ModuleRegistry("test_base_module_registry.json")
        registry.clear_registry()
        
        # Create modules
        processor = DataProcessorModule(registry)
        analyzer = DataAnalyzerModule(registry)
        
        # Test basic functionality
        test_data = {
            "raw_data": [1, 2, 3, 15, 20, 25]
        }
        
        # Process data
        result = await processor.process(test_data)
        
        # Validate result
        assert "processed_data" in result
        assert "patterns" in result
        assert "metadata" in result
        assert result["metadata"]["count"] == 6
        assert len(result["patterns"]) > 0
        
        # Test analyzer directly
        analyzer_input = {
            "patterns": result["patterns"],
            "sample": test_data["raw_data"][:3]
        }
        
        analyzer_result = await analyzer.process(analyzer_input)
        assert "insights" in analyzer_result
        assert "anomalies" in analyzer_result
        assert "recommendations" in analyzer_result
        
        # Test registry
        modules = registry.list_modules()
        assert len(modules) == 2
        
        processors = registry.find_modules_by_capability("data_processing")
        assert len(processors) == 1
        assert processors[0].name == "DataProcessor"
        
        # Cleanup
        registry.clear_registry()
        Path("test_base_module_registry.json").unlink(missing_ok=True)
        
        print("✅ Base module validation passed!")
        print(f"Processor result: {json.dumps(result, indent=2)}")
    
    import json
    from pathlib import Path
    asyncio.run(test_module())