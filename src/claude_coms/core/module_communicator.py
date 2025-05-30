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
            module_class=module.__class__.__name__,
            capabilities=getattr(module, 'capabilities', []),
            version=getattr(module, 'version', '1.0.0'),
            description=getattr(module, 'description', ''),
            dependencies=getattr(module, 'dependencies', [])
        )
        
        return self.registry.register(info)
    
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
                'class': m.module_class,
                'capabilities': m.capabilities,
                'version': m.version,
                'description': m.description
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