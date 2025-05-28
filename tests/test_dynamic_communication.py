"""
Integration tests for dynamic module communication via Claude Code.

Purpose: Tests the complete system including module registration, discovery,
and actual communication through Claude Code instances.
"""

import asyncio
import pytest
import json
from pathlib import Path
import sys
import shutil
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.claude_coms.module_registry import ModuleRegistry, ModuleInfo
from src.claude_coms.base_module import BaseModule
from src.claude_coms.claude_code_communicator import ClaudeCodeCommunicator
from src.claude_coms.example_modules import (
    DataProducerModule, 
    DataProcessorModule,
    DataAnalyzerModule,
    OrchestratorModule
)


class TestModule(BaseModule):
    """Simple test module for unit testing."""
    
    def __init__(self, name: str, registry: ModuleRegistry):
        super().__init__(
            name=name,
            system_prompt=f"Test module {name} for integration testing",
            capabilities=["testing", "echo"],
            registry=registry
        )
        self.received_messages = []
    
    def get_input_schema(self):
        return {"type": "object", "properties": {"data": {"type": "any"}}}
    
    def get_output_schema(self):
        return {"type": "object", "properties": {"echo": {"type": "any"}}}
    
    async def process(self, data):
        self.received_messages.append(data)
        return {"echo": data, "module": self.name}


@pytest.fixture
def registry():
    """Create a test registry."""
    reg = ModuleRegistry("test_registry.json", auto_save=False)
    yield reg
    # Cleanup
    if Path("test_registry.json").exists():
        Path("test_registry.json").unlink()


@pytest.fixture
def claude_available():
    """Check if Claude CLI is available."""
    return shutil.which("claude") is not None


class TestModuleRegistry:
    """Test module registry functionality."""
    
    def test_module_registration(self, registry):
        """Test registering modules."""
        module_info = ModuleInfo(
            name="TestModule",
            system_prompt="A test module",
            capabilities=["test", "demo"],
            input_schema={"type": "object"},
            output_schema={"type": "object"}
        )
        
        assert registry.register_module(module_info)
        assert registry.get_module("TestModule") is not None
        assert len(registry.list_modules()) == 1
    
    def test_module_discovery_by_capability(self, registry):
        """Test finding modules by capability."""
        # Register multiple modules
        for i in range(3):
            module_info = ModuleInfo(
                name=f"Module{i}",
                system_prompt=f"Module {i}",
                capabilities=["common", f"unique_{i}"],
            )
            registry.register_module(module_info)
        
        # Find by common capability
        common_modules = registry.find_modules_by_capability("common")
        assert len(common_modules) == 3
        
        # Find by unique capability
        unique_modules = registry.find_modules_by_capability("unique_1")
        assert len(unique_modules) == 1
        assert unique_modules[0].name == "Module1"
    
    def test_schema_compatibility(self, registry):
        """Test schema compatibility checking."""
        # Producer module
        producer = ModuleInfo(
            name="Producer",
            system_prompt="Produces data",
            capabilities=["produce"],
            output_schema={
                "type": "object",
                "properties": {
                    "data": {"type": "array"},
                    "metadata": {"type": "object"}
                }
            }
        )
        registry.register_module(producer)
        
        # Compatible consumer
        consumer1 = ModuleInfo(
            name="Consumer1",
            system_prompt="Consumes data",
            capabilities=["consume"],
            input_schema={
                "type": "object",
                "properties": {
                    "data": {"type": "array"}
                }
            }
        )
        registry.register_module(consumer1)
        
        # Incompatible consumer
        consumer2 = ModuleInfo(
            name="Consumer2",
            system_prompt="Consumes different data",
            capabilities=["consume"],
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"}
                }
            }
        )
        registry.register_module(consumer2)
        
        # Find compatible modules
        compatible = registry.find_compatible_modules(
            producer.output_schema,
            strict=True
        )
        
        assert len(compatible) == 1
        assert compatible[0].name == "Consumer1"


class TestBaseModule:
    """Test base module functionality."""
    
    @pytest.mark.asyncio
    async def test_module_lifecycle(self, registry):
        """Test module start/stop lifecycle."""
        module = TestModule("TestModule", registry)
        
        assert not module.is_running
        
        await module.start()
        assert module.is_running
        
        # Check registry status
        module_info = registry.get_module("TestModule")
        assert module_info.status == "active"
        
        await module.stop()
        assert not module.is_running
        assert registry.get_module("TestModule").status == "inactive"
    
    @pytest.mark.asyncio
    async def test_module_discovery(self, registry):
        """Test module discovery functionality."""
        # Create multiple modules
        module1 = TestModule("Module1", registry)
        module2 = TestModule("Module2", registry)
        
        await module1.start()
        await module2.start()
        
        # Test discovery from module1
        all_modules = await module1.discover_modules()
        assert "Module2" in all_modules
        assert "Module1" not in all_modules  # Shouldn't include self
        
        # Test capability-based discovery
        test_modules = await module1.discover_modules("testing")
        assert "Module2" in test_modules
    
    @pytest.mark.asyncio
    async def test_message_handlers(self, registry):
        """Test built-in message handlers."""
        module = TestModule("TestModule", registry)
        await module.start()
        
        # Test ping handler
        ping_response = await module.handle_message({
            "type": "ping",
            "source": "test",
            "target": "TestModule",
            "content": {},
            "id": "test-1",
            "timestamp": datetime.now().isoformat()
        })
        
        assert ping_response["type"] == "pong"
        assert ping_response["module"] == "TestModule"
        
        # Test status handler
        status_response = await module.handle_message({
            "type": "status",
            "source": "test",
            "target": "TestModule",
            "content": {},
            "id": "test-2",
            "timestamp": datetime.now().isoformat()
        })
        
        assert status_response["module"] == "TestModule"
        assert status_response["status"] == "active"
        assert "testing" in status_response["capabilities"]


@pytest.mark.skipif(not shutil.which("claude"), reason="Claude CLI not available")
class TestClaudeCommunication:
    """Test actual Claude Code communication."""
    
    @pytest.mark.asyncio
    async def test_claude_communicator(self):
        """Test basic Claude Code communicator."""
        communicator = ClaudeCodeCommunicator(
            module_name="TestModule",
            system_prompt="A test module for integration testing"
        )
        
        # Test sending a simple message
        result = await communicator.send_message(
            target_module="EchoModule",
            message="Please echo this message back",
            target_context="You are an echo module that repeats messages",
            context={"test": True}
        )
        
        assert result.status == "SUCCESS"
        assert result.source_module == "TestModule"
        assert result.target_module == "EchoModule"
        assert len(result.response) > 0
    
    @pytest.mark.asyncio
    async def test_module_to_module_communication(self, registry):
        """Test communication between two modules via Claude."""
        # Create two test modules
        sender = TestModule("Sender", registry)
        receiver = TestModule("Receiver", registry)
        
        await sender.start()
        await receiver.start()
        
        # Send message from sender to receiver
        result = await sender.send_to(
            target_module="Receiver",
            message_type="test_message",
            content={"data": "Hello from Sender"},
            wait_response=True
        )
        
        assert result is not None
        assert result.status == "SUCCESS"
        assert result.source_module == "Sender"
        assert result.target_module == "Receiver"


class TestExampleModules:
    """Test the example module implementations."""
    
    @pytest.mark.asyncio
    async def test_data_pipeline(self, registry):
        """Test data producer -> processor -> analyzer pipeline."""
        # Create modules
        producer = DataProducerModule(registry)
        processor = DataProcessorModule(registry)
        analyzer = DataAnalyzerModule(registry)
        
        # Start modules
        await producer.start()
        await processor.start()
        await analyzer.start()
        
        # Verify registration
        assert len(registry.list_modules()) == 3
        
        # Test compatibility
        graph = registry.get_module_graph()
        assert "DataProcessor" in graph.get("DataProducer", [])
        assert "DataAnalyzer" in graph.get("DataProcessor", [])
        
        # Test data production
        prod_result = await producer.process({
            "data_type": "numeric",
            "count": 5
        })
        
        assert "data_batch" in prod_result
        assert len(prod_result["data_batch"]) == 5
        assert prod_result["data_type"] == "numeric"
        
        # Test data processing
        proc_result = await processor.process(prod_result)
        
        assert "processed_data" in proc_result
        assert "statistics" in proc_result
        assert "average" in proc_result["processed_data"]
        
        # Test data analysis
        analysis_result = await analyzer.process(proc_result)
        
        assert "insights" in analysis_result
        assert "recommendations" in analysis_result
        assert isinstance(analysis_result["confidence"], (int, float))
    
    @pytest.mark.asyncio
    async def test_orchestrator(self, registry):
        """Test orchestrator module."""
        orchestrator = OrchestratorModule(registry)
        await orchestrator.start()
        
        # Test workflow execution
        result = await orchestrator.process({
            "workflow": "simple_pipeline",
            "parameters": {
                "data_type": "text",
                "count": 10
            }
        })
        
        assert result["status"] == "completed"
        assert "workflow_id" in result
        assert "execution_time" in result


@pytest.mark.asyncio
async def test_dynamic_module_communication_integration(registry):
    """Full integration test of dynamic module communication."""
    print("\n🧪 Running full integration test...\n")
    
    # Create all modules
    producer = DataProducerModule(registry)
    processor = DataProcessorModule(registry)
    analyzer = DataAnalyzerModule(registry)
    orchestrator = OrchestratorModule(registry)
    
    # Start all modules
    modules = [producer, processor, analyzer, orchestrator]
    for module in modules:
        await module.start()
    
    print(f"✅ Started {len(modules)} modules")
    
    # Verify all modules are registered
    registered = registry.list_modules()
    assert len(registered) == 4
    
    print("\n📋 Module Graph:")
    graph = registry.get_module_graph()
    for source, targets in graph.items():
        if targets:
            print(f"  {source} → {', '.join(targets)}")
    
    # Test dynamic discovery
    producers = await processor.discover_modules("data_generation")
    assert "DataProducer" in producers
    
    processors = await producer.discover_modules("data_processing")
    assert "DataProcessor" in processors
    
    # Test broadcast capability
    if shutil.which("claude"):
        broadcast_results = await producer.broadcast(
            message_type="status_check",
            content={"request": "report_status"}
        )
        print(f"\n📡 Broadcast to {len(broadcast_results)} modules")
    
    # Cleanup
    for module in modules:
        await module.stop()
    
    print("\n✅ Integration test completed!")


if __name__ == "__main__":
    # Run specific test
    asyncio.run(test_dynamic_module_communication_integration(
        ModuleRegistry("test_registry.json")
    ))