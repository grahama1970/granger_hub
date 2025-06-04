"""
Module: module_registry.py
Purpose: Create registry for modules to discover each other

External Dependencies:
- json: Built-in Python module for JSON handling
- pathlib: Built-in Python module for path operations

Example Usage:
>>> registry = ModuleRegistry()
>>> registry.register_module(ModuleInfo(name="DataProcessor", system_prompt="Process data", capabilities=["processing"]))
>>> processor = registry.get_module("DataProcessor")
>>> print(processor.name)
'DataProcessor'
"""

import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
import json
from pathlib import Path
from loguru import logger


@dataclass
class ModuleInfo:
    """Information about a registered module."""
    name: str
    system_prompt: str
    capabilities: List[str]
    input_schema: Optional[Dict] = None
    output_schema: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModuleInfo':
        """Create from dictionary."""
        return cls(**data)


class ModuleRegistry:
    """Registry for module discovery and management."""
    
    def __init__(self, registry_file: str = "module_registry.json"):
        self.registry_file = Path(registry_file)
        self.modules: Dict[str, ModuleInfo] = {}
        self._load_registry()
        logger.info(f"Initialized ModuleRegistry with file: {registry_file}")
    
    def _load_registry(self):
        """Load registry from file if exists."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file) as f:
                    data = json.load(f)
                    for name, info in data.items():
                        self.modules[name] = ModuleInfo.from_dict(info)
                logger.info(f"Loaded {len(self.modules)} modules from registry")
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                self.modules = {}
    
    def _save_registry(self):
        """Save registry to file."""
        try:
            data = {
                name: module.to_dict()
                for name, module in self.modules.items()
            }
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved registry with {len(self.modules)} modules")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def register_module(self, module_info: ModuleInfo) -> bool:
        """Register a new module."""
        try:
            self.modules[module_info.name] = module_info
            self._save_registry()
            logger.success(f"Registered module: {module_info.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register module {module_info.name}: {e}")
            return False
    
    def unregister_module(self, name: str) -> bool:
        """Unregister a module."""
        if name in self.modules:
            del self.modules[name]
            self._save_registry()
            logger.info(f"Unregistered module: {name}")
            return True
        return False
    
    def get_module(self, name: str) -> Optional[ModuleInfo]:
        """Get module information by name."""
        return self.modules.get(name)
    
    def list_modules(self) -> List[ModuleInfo]:
        """List all registered modules."""
        return list(self.modules.values())
    
    def find_modules_by_capability(self, capability: str) -> List[ModuleInfo]:
        """Find modules with specific capability."""
        return [
            module for module in self.modules.values()
            if capability in module.capabilities
        ]
    
    def get_module_names(self) -> List[str]:
        """Get list of all module names."""
        return list(self.modules.keys())
    
    def clear_registry(self):
        """Clear all modules from registry."""
        self.modules = {}
        self._save_registry()
        logger.warning("Cleared module registry")


# Validation
if __name__ == "__main__":
    def test_registry():
        # Create test registry
        test_file = "test_module_registry.json"
        registry = ModuleRegistry(test_file)
        
        # Clear any existing modules
        registry.clear_registry()
        
        # Register modules
        module1 = ModuleInfo(
            name="DataProcessor",
            system_prompt="Process raw data and extract patterns",
            capabilities=["data_processing", "pattern_extraction"],
            input_schema={"type": "object", "properties": {"data": {"type": "array"}}},
            output_schema={"type": "object", "properties": {"patterns": {"type": "array"}}}
        )
        assert registry.register_module(module1) == True
        
        module2 = ModuleInfo(
            name="DataAnalyzer",
            system_prompt="Analyze processed data for insights",
            capabilities=["data_analysis", "anomaly_detection"],
            input_schema={"type": "object", "properties": {"patterns": {"type": "array"}}},
            output_schema={"type": "object", "properties": {"insights": {"type": "array"}}}
        )
        assert registry.register_module(module2) == True
        
        # Test retrieval
        processor = registry.get_module("DataProcessor")
        assert processor is not None
        assert processor.name == "DataProcessor"
        assert "data_processing" in processor.capabilities
        
        # Test listing
        modules = registry.list_modules()
        assert len(modules) == 2
        
        # Test capability search
        analyzers = registry.find_modules_by_capability("data_analysis")
        assert len(analyzers) == 1
        assert analyzers[0].name == "DataAnalyzer"
        
        processors = registry.find_modules_by_capability("data_processing")
        assert len(processors) == 1
        assert processors[0].name == "DataProcessor"
        
        # Test persistence
        registry2 = ModuleRegistry(test_file)
        assert len(registry2.list_modules()) == 2
        assert registry2.get_module("DataProcessor") is not None
        
        # Cleanup
        Path(test_file).unlink(missing_ok=True)
        
        print("✅ Module registry validation passed!")
        return True
    
    # Run test
    success = test_registry()
    assert success == True