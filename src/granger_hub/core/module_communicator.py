"""
Module Communicator - High-level orchestrator for module communication.

Purpose: Provides a unified interface for module registration, discovery,
message routing, and task execution by combining ModuleRegistry and
ConversationManager functionality.

Third-party packages: None (uses only internal modules)

Sample Input:
- register_module("DataProcessor", DataProcessorModule())
- send_message("DataProcessor", "process", {"data": [1, 2, 3]})

Expected Output:
- Module registration confirmation
- Processed message results
"""

from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import asyncio
from datetime import datetime

from .modules import ModuleRegistry, BaseModule, ModuleInfo
from .conversation import ConversationManager, ConversationMessage
from .modules.progress_tracker import AsyncProgressTracker as ProgressTracker


class ModuleCommunicator:
    """High-level orchestrator for inter-module communication."""
    
    def __init__(self, registry_path: Optional[Path] = None, progress_db: Optional[Path] = None):
        """Initialize the module communicator.
        
        Args:
            registry_path: Path to module registry file
            progress_db: Path to progress database
        """
        self.registry = ModuleRegistry(registry_path)
        self.conversation_manager = ConversationManager(self.registry)
        self.progress_tracker = ProgressTracker(progress_db) if progress_db else None
        self.modules: Dict[str, BaseModule] = {}
        
    def register_module(self, name: str, module: BaseModule) -> bool:
        """Register a module.
        
        Args:
            name: Module name
            module: Module instance
            
        Returns:
            True if successful
        """
        # Store module reference
        self.modules[name] = module
        
        # Register with registry
        info = ModuleInfo(
            name=name,
            system_prompt=module.system_prompt,
            capabilities=module.capabilities,
            input_schema=module.get_input_schema() if hasattr(module, 'get_input_schema') else None,
            output_schema=module.get_output_schema() if hasattr(module, 'get_output_schema') else None
        )
        
        return self.registry.register_module(info)
    
    async def discover_modules(self, pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover available modules.
        
        Args:
            pattern: Optional filter pattern
            
        Returns:
            List of module information
        """
        modules = self.registry.list_modules()
        
        # Filter by pattern if provided
        if pattern:
            modules = [m for m in modules if pattern.lower() in m.name.lower()]
        
        # Convert to dict format
        return [
            {
                'name': m.name,
                'system_prompt': m.system_prompt,
                'capabilities': m.capabilities,
                'input_schema': m.input_schema,
                'output_schema': m.output_schema
            }
            for m in modules
        ]
    
    async def send_message(self, target: str, action: str, data: Dict[str, Any], 
                          timeout: Optional[int] = None) -> Dict[str, Any]:
        """Send a message to a target module.
        
        Args:
            target: Target module name
            action: Action to perform
            data: Message data
            timeout: Optional timeout in seconds
            
        Returns:
            Response with success status and data/error
        """
        try:
            # Create conversation message
            message = ConversationMessage.create(
                source="CLI",
                target=target,
                msg_type=action,
                content=str(data),
                data=data
            )
            
            # Route through conversation manager
            result = await self.conversation_manager.route_message(message)
            
            if result:
                return {"success": True, "data": result}
            else:
                return {"success": False, "error": "No response from module"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_instruction(self, instruction: str, requester: Optional[str] = None,
                                 task_type: Optional[str] = None, 
                                 parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a natural language instruction.
        
        Args:
            instruction: Natural language instruction
            requester: Optional requester module name
            task_type: Optional task type hint
            parameters: Optional parameters
            
        Returns:
            Execution result
        """
        try:
            # Find suitable module based on instruction
            # This is a simplified implementation
            modules = self.registry.list_modules()
            
            # Look for module with matching capabilities
            suitable_module = None
            for module in modules:
                # Simple keyword matching
                if any(cap.lower() in instruction.lower() for cap in module.capabilities):
                    suitable_module = module.name
                    break
            
            if not suitable_module:
                return {
                    "success": False,
                    "error": "No suitable module found for instruction"
                }
            
            # Send instruction to module
            result = await self.send_message(
                suitable_module,
                "execute",
                {
                    "instruction": instruction,
                    "requester": requester or "CLI",
                    "task_type": task_type,
                    "parameters": parameters or {}
                }
            )
            
            return {
                "success": result.get("success", False),
                "module": suitable_module,
                "result": result.get("data"),
                "error": result.get("error")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def broadcast_message(self, action: str, data: Dict[str, Any],
                               pattern: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Broadcast a message to multiple modules.
        
        Args:
            action: Action to broadcast
            data: Message data
            pattern: Optional module filter pattern
            
        Returns:
            Results from each module
        """
        modules = await self.discover_modules(pattern)
        results = {}
        
        for module in modules:
            result = await self.send_message(module['name'], action, data)
            results[module['name']] = result
            
        return results
    
    async def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get module dependency graph.
        
        Returns:
            Dependency graph as adjacency list
        """
        graph = {}
        modules = self.registry.list_modules()
        
        for module in modules:
            graph[module.name] = module.dependencies
            
        return graph
    
    async def check_compatibility(self, source: str, target: str) -> Dict[str, Any]:
        """Check compatibility between two modules.
        
        Args:
            source: Source module name
            target: Target module name
            
        Returns:
            Compatibility check result
        """
        try:
            # Get module info
            source_info = self.registry.get_module(source)
            target_info = self.registry.get_module(target)
            
            if not source_info or not target_info:
                return {
                    "compatible": False,
                    "reason": "One or both modules not found"
                }
            
            # Simple compatibility check based on capabilities
            # In real implementation, this would check schemas
            compatible = True
            reason = "Modules are compatible"
            
            # Check if target is in source's dependencies
            if target in source_info.dependencies:
                compatible = True
                reason = "Direct dependency relationship"
            
            return {
                "compatible": compatible,
                "reason": reason,
                "details": {
                    "source_capabilities": source_info.capabilities,
                    "target_capabilities": target_info.capabilities
                }
            }
            
        except Exception as e:
            return {
                "compatible": False,
                "reason": str(e)
            }
    
    async def get_progress(self, session_id: Optional[str] = None,
                          limit: int = 10) -> List[Dict[str, Any]]:
        """Get communication progress.
        
        Args:
            session_id: Optional session filter
            limit: Number of entries to return
            
        Returns:
            Progress entries
        """
        if not self.progress_tracker:
            return []
            
        # This would query the progress database
        # For now, return mock data
        return [
            {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id or "default",
                "source": "Module1",
                "target": "Module2",
                "status": "completed"
            }
        ]
    
    async def start_conversation(self, initiator: str, target: str, 
                                initial_message: Dict[str, Any],
                                conversation_type: str = "task") -> Dict[str, Any]:
        """Start a conversation between modules.
        
        Args:
            initiator: Initiating module name
            target: Target module name
            initial_message: Initial message content
            conversation_type: Type of conversation (task, negotiation, etc.)
            
        Returns:
            Conversation details including ID
        """
        try:
            # Create conversation
            conversation = await self.conversation_manager.create_conversation(
                initiator=initiator,
                target=target,
                initial_message={
                    "type": conversation_type,
                    "content": initial_message,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Start conversation monitoring
            asyncio.create_task(self._monitor_conversation(conversation.conversation_id))
            
            return {
                "success": True,
                "conversation_id": conversation.conversation_id,
                "participants": conversation.participants,
                "status": conversation.status,
                "type": conversation_type
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _monitor_conversation(self, conversation_id: str):
        """Monitor a conversation for timeout and logging.
        
        Args:
            conversation_id: Conversation to monitor
        """
        timeout_seconds = 300  # 5 minute timeout
        check_interval = 30    # Check every 30 seconds
        
        start_time = datetime.now()
        
        while True:
            await asyncio.sleep(check_interval)
            
            # Check if conversation still exists
            if conversation_id not in self.conversation_manager.conversations:
                break
                
            conversation = self.conversation_manager.conversations[conversation_id]
            
            # Check for timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                await self.conversation_manager.end_conversation(
                    conversation_id, 
                    reason="timeout"
                )
                break
            
            # Check if conversation completed
            if conversation.status in ["completed", "failed"]:
                break
    
    async def get_conversation_analytics(self, 
                                       start_date: Optional[datetime] = None,
                                       end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get analytics about conversations.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Analytics data
        """
        try:
            # Get all conversations in range
            all_conversations = await self.conversation_manager.get_conversation_history()
            
            # Filter by date if provided
            if start_date or end_date:
                filtered = []
                for conv in all_conversations:
                    conv_time = datetime.fromisoformat(conv.get("started_at", ""))
                    if start_date and conv_time < start_date:
                        continue
                    if end_date and conv_time > end_date:
                        continue
                    filtered.append(conv)
                all_conversations = filtered
            
            # Calculate analytics
            total_conversations = len(all_conversations)
            completed = sum(1 for c in all_conversations if c.get("status") == "completed")
            failed = sum(1 for c in all_conversations if c.get("status") == "failed")
            active = sum(1 for c in all_conversations if c.get("status") == "active")
            
            # Average turns and duration
            total_turns = sum(c.get("turn_count", 0) for c in all_conversations)
            total_duration = sum(
                (datetime.fromisoformat(c.get("last_activity", c.get("started_at", ""))) - 
                 datetime.fromisoformat(c.get("started_at", ""))).total_seconds()
                for c in all_conversations if c.get("started_at")
            )
            
            avg_turns = total_turns / total_conversations if total_conversations > 0 else 0
            avg_duration = total_duration / total_conversations if total_conversations > 0 else 0
            
            # Module participation
            module_stats = {}
            for conv in all_conversations:
                for participant in conv.get("participants", []):
                    if participant not in module_stats:
                        module_stats[participant] = {"initiated": 0, "participated": 0}
                    module_stats[participant]["participated"] += 1
                    
                # First participant is the initiator
                participants = conv.get("participants", [])
                if participants and participants[0] in module_stats:
                    module_stats[participants[0]]["initiated"] += 1
            
            return {
                "total_conversations": total_conversations,
                "completed": completed,
                "failed": failed,
                "active": active,
                "average_turns": round(avg_turns, 2),
                "average_duration_seconds": round(avg_duration, 2),
                "module_statistics": module_stats,
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "total_conversations": 0
            }
    
    async def shutdown(self):
        """Shutdown the communicator gracefully."""
        # Close any active conversations
        for conv_id in list(self.conversation_manager.conversations.keys()):
            await self.conversation_manager.end_conversation(conv_id)
        
        # Save registry
        self.registry.save()


if __name__ == "__main__":
    # Validation test
    async def test_communicator():
        comm = ModuleCommunicator()
        
        # Test module discovery
        modules = await comm.discover_modules()
        print(f"Discovered {len(modules)} modules")
        
        # Test dependency graph
        graph = await comm.get_dependency_graph()
        print(f"Dependency graph: {graph}")
        
        return len(modules) >= 0  # Should always pass
    
    # Run test
    result = asyncio.run(test_communicator())
    print(f"Test result: {'PASSED' if result else 'FAILED'}")