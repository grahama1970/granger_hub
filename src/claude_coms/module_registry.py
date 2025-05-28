"""
Module Registry for dynamic module discovery and management.

Purpose: Provides a centralized registry where modules can register themselves
and discover other modules dynamically at runtime.

Dependencies:
- json: For persistence
- pathlib: For file operations
- asyncio: For async operations
- threading: For thread-safe operations
"""

import json
import asyncio
from typing import Dict, Optional, List, Set, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import threading
from collections import defaultdict


@dataclass
class ModuleInfo:
    """Information about a registered module."""
    name: str
    system_prompt: str
    capabilities: List[str]
    input_schema: Optional[Dict] = None
    output_schema: Optional[Dict] = None
    status: str = "active"  # active, inactive, error
    last_seen: Optional[str] = None
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class ModuleRegistry:
    """Registry for dynamic module discovery and management."""
    
    def __init__(self, registry_file: str = "module_registry.json", 
                 auto_save: bool = True):
        """Initialize the module registry.
        
        Args:
            registry_file: Path to the registry persistence file
            auto_save: Whether to automatically save after modifications
        """
        self.registry_file = Path(registry_file)
        self.auto_save = auto_save
        self.modules: Dict[str, ModuleInfo] = {}
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Load existing registry
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from file if exists."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    with self._lock:
                        for name, info in data.items():
                            self.modules[name] = ModuleInfo(**info)
                print(f"📚 Loaded {len(self.modules)} modules from registry")
            except Exception as e:
                print(f"⚠️  Error loading registry: {e}")
    
    def _save_registry(self):
        """Save registry to file."""
        if not self.auto_save:
            return
            
        try:
            with self._lock:
                data = {
                    name: module.to_dict() 
                    for name, module in self.modules.items()
                }
            
            # Write atomically
            temp_file = self.registry_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.registry_file)
            
        except Exception as e:
            print(f"⚠️  Error saving registry: {e}")
    
    def register_module(self, module_info: ModuleInfo) -> bool:
        """Register a new module or update existing one.
        
        Args:
            module_info: Module information to register
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                # Update timestamp
                module_info.last_seen = datetime.now().isoformat()
                
                # Check if updating existing module
                is_update = module_info.name in self.modules
                
                # Register/update module
                self.modules[module_info.name] = module_info
                
                # Notify subscribers
                event_type = "module_updated" if is_update else "module_registered"
                self._notify_subscribers(event_type, module_info)
            
            # Save registry
            self._save_registry()
            
            action = "Updated" if is_update else "Registered"
            print(f"✅ {action} module: {module_info.name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to register module {module_info.name}: {e}")
            return False
    
    def unregister_module(self, name: str) -> bool:
        """Unregister a module.
        
        Args:
            name: Module name to unregister
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                if name not in self.modules:
                    return False
                
                module_info = self.modules.pop(name)
                self._notify_subscribers("module_unregistered", module_info)
            
            self._save_registry()
            print(f"✅ Unregistered module: {name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to unregister module {name}: {e}")
            return False
    
    def get_module(self, name: str) -> Optional[ModuleInfo]:
        """Get module information by name.
        
        Args:
            name: Module name
            
        Returns:
            ModuleInfo if found, None otherwise
        """
        with self._lock:
            return self.modules.get(name)
    
    def list_modules(self, 
                    status: Optional[str] = None,
                    capability: Optional[str] = None) -> List[ModuleInfo]:
        """List all registered modules with optional filters.
        
        Args:
            status: Filter by status (active, inactive, error)
            capability: Filter by capability
            
        Returns:
            List of matching modules
        """
        with self._lock:
            modules = list(self.modules.values())
        
        # Apply filters
        if status:
            modules = [m for m in modules if m.status == status]
        
        if capability:
            modules = [
                m for m in modules 
                if capability in m.capabilities
            ]
        
        return modules
    
    def find_modules_by_capability(self, capability: str) -> List[ModuleInfo]:
        """Find all modules with a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of modules with the capability
        """
        return self.list_modules(capability=capability)
    
    def find_compatible_modules(self, 
                               output_schema: Dict,
                               strict: bool = False) -> List[ModuleInfo]:
        """Find modules that can accept the given output schema.
        
        Args:
            output_schema: Output schema to match against module inputs
            strict: Whether to enforce strict schema matching
            
        Returns:
            List of compatible modules
        """
        compatible = []
        
        with self._lock:
            for module in self.modules.values():
                if self._schemas_compatible(output_schema, module.input_schema, strict):
                    compatible.append(module)
        
        return compatible
    
    def _schemas_compatible(self, 
                           output_schema: Optional[Dict],
                           input_schema: Optional[Dict],
                           strict: bool) -> bool:
        """Check if schemas are compatible.
        
        Args:
            output_schema: Output schema from source
            input_schema: Input schema of target
            strict: Whether to enforce strict matching
            
        Returns:
            True if compatible
        """
        # If either schema is not defined, assume compatible
        if not output_schema or not input_schema:
            return not strict
        
        # Simple compatibility check - can be enhanced
        output_props = output_schema.get("properties", {})
        input_props = input_schema.get("properties", {})
        
        if strict:
            # All input properties must exist in output
            return all(prop in output_props for prop in input_props)
        else:
            # At least one matching property
            return any(prop in output_props for prop in input_props)
    
    def update_module_status(self, name: str, status: str) -> bool:
        """Update module status.
        
        Args:
            name: Module name
            status: New status (active, inactive, error)
            
        Returns:
            True if successful
        """
        with self._lock:
            if name not in self.modules:
                return False
            
            self.modules[name].status = status
            self.modules[name].last_seen = datetime.now().isoformat()
            self._notify_subscribers("module_status_changed", self.modules[name])
        
        self._save_registry()
        return True
    
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to registry events.
        
        Args:
            event_type: Event type to subscribe to
            callback: Callback function(event_type, module_info)
        """
        with self._lock:
            self._subscribers[event_type].append(callback)
    
    def _notify_subscribers(self, event_type: str, module_info: ModuleInfo):
        """Notify subscribers of an event."""
        with self._lock:
            callbacks = self._subscribers.get(event_type, [])
        
        for callback in callbacks:
            try:
                callback(event_type, module_info)
            except Exception as e:
                print(f"⚠️  Error in subscriber callback: {e}")
    
    def get_module_graph(self) -> Dict[str, List[str]]:
        """Get module connectivity graph based on schema compatibility.
        
        Returns:
            Dict mapping module names to list of compatible target modules
        """
        graph = {}
        
        with self._lock:
            for source_name, source_module in self.modules.items():
                if source_module.output_schema:
                    compatible = self.find_compatible_modules(
                        source_module.output_schema
                    )
                    graph[source_name] = [m.name for m in compatible]
                else:
                    graph[source_name] = []
        
        return graph
    
    def clear_inactive_modules(self, inactive_hours: int = 24) -> int:
        """Remove modules that haven't been seen recently.
        
        Args:
            inactive_hours: Hours of inactivity before removal
            
        Returns:
            Number of modules removed
        """
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=inactive_hours)
        removed = 0
        
        with self._lock:
            to_remove = []
            for name, module in self.modules.items():
                if module.last_seen:
                    last_seen = datetime.fromisoformat(module.last_seen)
                    if last_seen < cutoff_time:
                        to_remove.append(name)
            
            for name in to_remove:
                self.modules.pop(name)
                removed += 1
        
        if removed > 0:
            self._save_registry()
            print(f"🧹 Removed {removed} inactive modules")
        
        return removed


# Example usage and testing
if __name__ == "__main__":
    # Create registry
    registry = ModuleRegistry("test_registry.json")
    
    # Register some modules
    registry.register_module(ModuleInfo(
        name="DataCollector",
        system_prompt="Collects data from various sources",
        capabilities=["data_collection", "web_scraping", "api_integration"],
        output_schema={
            "type": "object",
            "properties": {
                "raw_data": {"type": "array"},
                "source": {"type": "string"},
                "timestamp": {"type": "string"}
            }
        }
    ))
    
    registry.register_module(ModuleInfo(
        name="DataProcessor",
        system_prompt="Processes and transforms raw data",
        capabilities=["data_processing", "transformation", "validation"],
        input_schema={
            "type": "object",
            "properties": {
                "raw_data": {"type": "array"}
            }
        },
        output_schema={
            "type": "object",
            "properties": {
                "processed_data": {"type": "array"},
                "statistics": {"type": "object"}
            }
        }
    ))
    
    registry.register_module(ModuleInfo(
        name="DataAnalyzer",
        system_prompt="Analyzes processed data for insights",
        capabilities=["data_analysis", "pattern_recognition", "anomaly_detection"],
        input_schema={
            "type": "object",
            "properties": {
                "processed_data": {"type": "array"},
                "statistics": {"type": "object"}
            }
        },
        output_schema={
            "type": "object",
            "properties": {
                "insights": {"type": "array"},
                "recommendations": {"type": "array"}
            }
        }
    ))
    
    # Test discovery
    print("\n📋 All modules:")
    for module in registry.list_modules():
        print(f"  - {module.name}: {', '.join(module.capabilities)}")
    
    print("\n🔍 Modules with data_processing capability:")
    processors = registry.find_modules_by_capability("data_processing")
    for module in processors:
        print(f"  - {module.name}")
    
    print("\n🔗 Module compatibility graph:")
    graph = registry.get_module_graph()
    for source, targets in graph.items():
        if targets:
            print(f"  {source} → {', '.join(targets)}")
    
    # Test compatibility
    collector = registry.get_module("DataCollector")
    if collector and collector.output_schema:
        print("\n✅ Modules compatible with DataCollector output:")
        compatible = registry.find_compatible_modules(collector.output_schema)
        for module in compatible:
            print(f"  - {module.name}")
    
    # Cleanup
    Path("test_registry.json").unlink(missing_ok=True)