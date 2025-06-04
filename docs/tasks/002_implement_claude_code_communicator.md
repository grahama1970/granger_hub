# Task 002: Implement Claude Code-Based Module Communication

**Project**: granger_hub
**Goal**: Implement actual module communication using Claude Code instances

## Task Breakdown

### Task 1: Create ClaudeCodeCommunicator Class

**Module**: `src/claude_coms/claude_code_communicator.py`
**Goal**: Implement core class that spawns Claude Code instances for module communication

## Working Code Example

```python
# COPY THIS WORKING PATTERN:
import subprocess
import json
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
from datetime import datetime

class ClaudeCodeCommunicator:
    """Communicates between modules using Claude Code instances."""
    
    def __init__(self, module_name: str, system_prompt: str):
        self.module_name = module_name
        self.system_prompt = system_prompt
        self.claude_code_path = "claude"  # Assumes claude is in PATH
        
    async def send_message(self, target_module: str, message: str, 
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a message to another module via Claude Code."""
        
        # Prepare the full prompt with context
        full_prompt = f"""
You are acting as module '{self.module_name}' communicating with module '{target_module}'.

Module Context:
{self.system_prompt}

Target Module: {target_module}
Message: {message}

Additional Context:
{json.dumps(context or {}, indent=2)}

Please process this inter-module communication and provide a structured response.
"""
        
        # Create temporary file for the prompt
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(full_prompt)
            prompt_file = f.name
        
        try:
            # Run Claude Code with dangerous permissions flag
            cmd = [
                self.claude_code_path,
                "--dangerously-skip-permissions",
                prompt_file
            ]
            
            # Execute Claude Code
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Claude Code failed: {stderr.decode()}")
            
            # Parse response
            response = {
                "source_module": self.module_name,
                "target_module": target_module,
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "response": stdout.decode().strip(),
                "status": "SUCCESS"
            }
            
            return response
            
        finally:
            # Cleanup
            Path(prompt_file).unlink()
    
    async def receive_handler(self, callback):
        """Register a handler for receiving messages."""
        # Implementation depends on architecture choice
        pass

# Usage example:
async def test_communication():
    # Module A setup
    module_a = ClaudeCodeCommunicator(
        module_name="DataProcessor",
        system_prompt="You process raw data and extract meaningful patterns."
    )
    
    # Send message to Module B
    response = await module_a.send_message(
        target_module="DataAnalyzer",
        message="I have processed 1000 records. Please analyze for anomalies.",
        context={"record_count": 1000, "processing_time": 5.2}
    )
    
    print(f"Response: {response}")

# Run test
if __name__ == "__main__":
    asyncio.run(test_communication())
```

## Validation Requirements

```python
# This implementation works when:
assert response["status"] == "SUCCESS"
assert "response" in response
assert response["source_module"] == "DataProcessor"
assert response["target_module"] == "DataAnalyzer"
```

## Common Issues & Solutions

### Issue 1: Claude command not found
```python
# Solution: Specify full path or check installation
self.claude_code_path = "/usr/local/bin/claude"
# Or use shutil.which
import shutil
claude_path = shutil.which("claude")
if not claude_path:
    raise RuntimeError("Claude Code CLI not found in PATH")
```

### Issue 2: Permission denied without --dangerously-skip-permissions
```python
# Solution: Always include the flag for automated execution
cmd = [
    self.claude_code_path,
    "--dangerously-skip-permissions",  # Required for automation
    prompt_file
]
```

---

### Task 2: Implement Module Registry

**Module**: `src/claude_coms/module_registry.py`
**Goal**: Create registry for modules to discover each other

## Working Code Example

```python
# COPY THIS WORKING PATTERN:
import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass
class ModuleInfo:
    """Information about a registered module."""
    name: str
    system_prompt: str
    capabilities: List[str]
    input_schema: Optional[Dict] = None
    output_schema: Optional[Dict] = None
    
class ModuleRegistry:
    """Registry for module discovery and management."""
    
    def __init__(self, registry_file: str = "module_registry.json"):
        self.registry_file = Path(registry_file)
        self.modules: Dict[str, ModuleInfo] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from file if exists."""
        if self.registry_file.exists():
            with open(self.registry_file) as f:
                data = json.load(f)
                for name, info in data.items():
                    self.modules[name] = ModuleInfo(**info)
    
    def _save_registry(self):
        """Save registry to file."""
        data = {
            name: {
                "name": module.name,
                "system_prompt": module.system_prompt,
                "capabilities": module.capabilities,
                "input_schema": module.input_schema,
                "output_schema": module.output_schema
            }
            for name, module in self.modules.items()
        }
        with open(self.registry_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def register_module(self, module_info: ModuleInfo):
        """Register a new module."""
        self.modules[module_info.name] = module_info
        self._save_registry()
        print(f"✅ Registered module: {module_info.name}")
    
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

# Usage example:
def test_registry():
    registry = ModuleRegistry()
    
    # Register modules
    registry.register_module(ModuleInfo(
        name="DataProcessor",
        system_prompt="Process raw data and extract patterns",
        capabilities=["data_processing", "pattern_extraction"],
        input_schema={"type": "object", "properties": {"data": {"type": "array"}}},
        output_schema={"type": "object", "properties": {"patterns": {"type": "array"}}}
    ))
    
    registry.register_module(ModuleInfo(
        name="DataAnalyzer",
        system_prompt="Analyze processed data for insights",
        capabilities=["data_analysis", "anomaly_detection"],
        input_schema={"type": "object", "properties": {"patterns": {"type": "array"}}},
        output_schema={"type": "object", "properties": {"insights": {"type": "array"}}}
    ))
    
    # Find modules
    analyzers = registry.find_modules_by_capability("data_analysis")
    print(f"Found {len(analyzers)} modules with data_analysis capability")

if __name__ == "__main__":
    test_registry()
```

---

### Task 3: Create Module Base Class

**Module**: `src/claude_coms/base_module.py`
**Goal**: Abstract base class for modules to inherit from

## Working Code Example

```python
# COPY THIS WORKING PATTERN:
from abc import ABC, abstractmethod
import asyncio
from typing import Dict, Any, Optional, Callable
from .claude_code_communicator import ClaudeCodeCommunicator
from .module_registry import ModuleRegistry, ModuleInfo

class BaseModule(ABC):
    """Base class for all communicating modules."""
    
    def __init__(self, 
                 name: str,
                 system_prompt: str,
                 capabilities: list,
                 registry: Optional[ModuleRegistry] = None):
        self.name = name
        self.system_prompt = system_prompt
        self.capabilities = capabilities
        self.communicator = ClaudeCodeCommunicator(name, system_prompt)
        self.handlers: Dict[str, Callable] = {}
        
        # Auto-register if registry provided
        if registry:
            registry.register_module(ModuleInfo(
                name=name,
                system_prompt=system_prompt,
                capabilities=capabilities,
                input_schema=self.get_input_schema(),
                output_schema=self.get_output_schema()
            ))
    
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
        return await self.communicator.send_message(
            target_module=target_module,
            message=message,
            context=data
        )
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for specific message types."""
        self.handlers[message_type] = handler
    
    async def handle_message(self, message: Dict[str, Any]):
        """Handle incoming message."""
        msg_type = message.get("type", "default")
        handler = self.handlers.get(msg_type, self.process)
        return await handler(message.get("data", {}))

# Example implementation:
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
        """Process the raw data."""
        raw_data = data.get("raw_data", [])
        
        # Send to Claude for processing
        response = await self.send_to(
            target_module="DataAnalyzer",
            message=f"Process {len(raw_data)} data points",
            data={"sample": raw_data[:5]}  # Send sample
        )
        
        return {
            "processed_data": raw_data,
            "patterns": ["pattern1", "pattern2"],  # Simplified
            "metadata": {
                "count": len(raw_data),
                "claude_response": response
            }
        }

# Test it:
async def test_module():
    registry = ModuleRegistry()
    processor = DataProcessorModule(registry)
    
    result = await processor.process({
        "raw_data": [1, 2, 3, 4, 5]
    })
    
    print(f"Processing result: {result}")

if __name__ == "__main__":
    asyncio.run(test_module())
```

---

### Task 4: Integration Test

**Module**: `tests/test_claude_communication.py`
**Goal**: Test actual module-to-module communication via Claude

## Working Code Example

```python
# COPY THIS WORKING PATTERN:
import asyncio
import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.claude_coms.module_registry import ModuleRegistry
from src.claude_coms.base_module import BaseModule

class ProducerModule(BaseModule):
    """Produces data for processing."""
    
    def __init__(self, registry):
        super().__init__(
            name="Producer",
            system_prompt="You produce data and send it to processors",
            capabilities=["data_production"],
            registry=registry
        )
    
    def get_input_schema(self):
        return {"type": "object"}
    
    def get_output_schema(self):
        return {
            "type": "object",
            "properties": {"data": {"type": "array"}}
        }
    
    async def process(self, data):
        # Produce data and send to processor
        produced_data = list(range(10))
        
        response = await self.send_to(
            target_module="Processor",
            message="Please process this data batch",
            data={"batch": produced_data}
        )
        
        return {
            "produced": produced_data,
            "processor_response": response
        }

class ProcessorModule(BaseModule):
    """Processes data from producer."""
    
    def __init__(self, registry):
        super().__init__(
            name="Processor",
            system_prompt="You process data and return results",
            capabilities=["data_processing"],
            registry=registry
        )
    
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {"batch": {"type": "array"}}
        }
    
    def get_output_schema(self):
        return {
            "type": "object",
            "properties": {"result": {"type": "object"}}
        }
    
    async def process(self, data):
        batch = data.get("batch", [])
        return {
            "result": {
                "count": len(batch),
                "sum": sum(batch),
                "average": sum(batch) / len(batch) if batch else 0
            }
        }

@pytest.mark.asyncio
async def test_module_communication():
    """Test actual communication between modules via Claude."""
    # Setup
    registry = ModuleRegistry("test_registry.json")
    producer = ProducerModule(registry)
    processor = ProcessorModule(registry)
    
    # Test communication
    result = await producer.process({})
    
    # Assertions
    assert "produced" in result
    assert "processor_response" in result
    assert result["processor_response"]["status"] == "SUCCESS"
    
    # Cleanup
    Path("test_registry.json").unlink(missing_ok=True)

# Run directly
if __name__ == "__main__":
    asyncio.run(test_module_communication())
    print("✅ Module communication test passed!")
```

## Run Command

```bash
cd /home/graham/workspace/experiments/granger_hub
source .venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Run individual test
python tests/test_claude_communication.py

# Or with pytest
pytest tests/test_claude_communication.py -v
```

## Expected Output Structure

```json
{
    "produced": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    "processor_response": {
        "source_module": "Producer",
        "target_module": "Processor",
        "timestamp": "2025-05-27T18:45:00",
        "message": "Please process this data batch",
        "response": "Processed 10 items. Sum: 45, Average: 4.5",
        "status": "SUCCESS"
    }
}
```

## Common Issues & Solutions

### Issue 1: Claude Code not installed
```bash
# Solution: Install Claude CLI
# Check installation docs at https://claude.ai/cli
```

### Issue 2: Module not found errors
```python
# Solution: Ensure proper imports and PYTHONPATH
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Issue 3: Permission errors
```python
# Solution: Always use --dangerously-skip-permissions flag
# This is handled in ClaudeCodeCommunicator class
```

## Success Criteria

- [ ] ClaudeCodeCommunicator successfully spawns Claude instances
- [ ] Modules can register and discover each other
- [ ] Messages are routed through Claude with proper context
- [ ] System prompts provide module context to Claude
- [ ] Integration test shows end-to-end communication
- [ ] No mocking - uses real Claude Code CLI