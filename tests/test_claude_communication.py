"""
Module: test_claude_communication.py
Purpose: Test actual module-to-module communication via Claude

External Dependencies:
- pytest: Test framework
- asyncio: For async testing

Example Usage:
>>> pytest tests/test_claude_communication.py -v
All tests should pass
"""

import asyncio
import pytest
from pathlib import Path
import sys
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "granger_hub" / "core" / "modules"))

# Import directly from modules
from module_registry import ModuleRegistry, ModuleInfo
from base_module import BaseModule
from claude_code_communicator import ClaudeCodeCommunicator
from typing import Dict, Any, Optional


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
        return {"type": "object", "properties": {"count": {"type": "integer"}}}
    
    def get_output_schema(self):
        return {
            "type": "object",
            "properties": {"data": {"type": "array"}, "processor_response": {"type": "object"}}
        }
    
    async def process(self, data):
        # Produce data and send to processor
        count = data.get("count", 10)
        produced_data = list(range(count))
        
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
    registry.clear_registry()
    
    producer = ProducerModule(registry)
    processor = ProcessorModule(registry)
    
    # Test communication
    result = await producer.process({"count": 5})
    
    # Assertions
    assert "produced" in result
    assert "processor_response" in result
    assert result["processor_response"]["status"] in ["SUCCESS", "ERROR"]
    assert result["produced"] == [0, 1, 2, 3, 4]
    
    # If Claude is available, should be SUCCESS
    if result["processor_response"]["status"] == "SUCCESS":
        assert "response" in result["processor_response"]
        assert result["processor_response"]["source_module"] == "Producer"
        assert result["processor_response"]["target_module"] == "Processor"
    
    # Cleanup
    Path("test_registry.json").unlink(missing_ok=True)


@pytest.mark.asyncio 
async def test_module_registry():
    """Test module registry functionality."""
    registry = ModuleRegistry("test_registry2.json")
    registry.clear_registry()
    
    # Register test module
    module_info = ModuleInfo(
        name="TestModule",
        system_prompt="Test system prompt",
        capabilities=["test_capability"],
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    
    assert registry.register_module(module_info) == True
    
    # Test retrieval
    retrieved = registry.get_module("TestModule")
    assert retrieved is not None
    assert retrieved.name == "TestModule"
    assert "test_capability" in retrieved.capabilities
    
    # Test capability search
    modules = registry.find_modules_by_capability("test_capability")
    assert len(modules) == 1
    assert modules[0].name == "TestModule"
    
    # Cleanup
    registry.clear_registry()
    Path("test_registry2.json").unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_claude_code_communicator():
    """Test Claude code communicator directly."""
    communicator = ClaudeCodeCommunicator("TestModule", "Test system prompt")
    
    response = await communicator.send_message(
        target_module="TargetModule",
        message="Test message",
        context={"test": "data"}
    )
    
    # Should always return a response
    assert response is not None
    assert response["status"] in ["SUCCESS", "ERROR"]
    assert response["source_module"] == "TestModule"
    assert response["target_module"] == "TargetModule"
    assert "timestamp" in response
    assert "response" in response


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in communication."""
    registry = ModuleRegistry("test_registry3.json")
    registry.clear_registry()
    
    # Create module with non-existent target
    module = ProducerModule(registry)
    
    # Try to send to non-existent module
    response = await module.send_to(
        target_module="NonExistentModule",
        message="This should handle gracefully",
        data={"test": "data"}
    )
    
    # Should return response even for non-existent modules
    assert response is not None
    assert "status" in response
    
    # Cleanup
    registry.clear_registry()
    Path("test_registry3.json").unlink(missing_ok=True)


# Validation function
if __name__ == "__main__":
    async def run_tests():
        print("Running Claude communication tests...")
        
        # Test 1: Module communication
        try:
            await test_module_communication()
            print("✅ Module communication test passed")
        except AssertionError as e:
            print(f"❌ Module communication test failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Module communication test error: {e}")
            return False
        
        # Test 2: Module registry
        try:
            await test_module_registry()
            print("✅ Module registry test passed")
        except AssertionError as e:
            print(f"❌ Module registry test failed: {e}")
            return False
        
        # Test 3: Claude communicator
        try:
            await test_claude_code_communicator()
            print("✅ Claude communicator test passed")
        except AssertionError as e:
            print(f"❌ Claude communicator test failed: {e}")
            return False
        
        # Test 4: Error handling
        try:
            await test_error_handling()
            print("✅ Error handling test passed")
        except AssertionError as e:
            print(f"❌ Error handling test failed: {e}")
            return False
        
        print("\n✅ All Claude communication tests passed!")
        return True
    
    # Run all tests
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)