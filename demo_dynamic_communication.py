#!/usr/bin/env python3
"""
Demo script showing dynamic module communication.

This demonstrates how modules can:
1. Register themselves in a shared registry
2. Dynamically discover other modules
3. Communicate via Claude Code with proper context
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.claude_coms import (
    ModuleRegistry,
    DataProducerModule,
    DataProcessorModule,
    DataAnalyzerModule,
    OrchestratorModule
)


async def main():
    """Run the dynamic communication demo."""
    print("=" * 60)
    print("🚀 Claude Module Communicator - Dynamic Communication Demo")
    print("=" * 60)
    
    # Create shared registry
    registry = ModuleRegistry("demo_registry.json")
    print("\n📚 Creating module registry...")
    
    # Create modules - they auto-register with the registry
    print("\n🔧 Creating and starting modules...")
    
    producer = DataProducerModule(registry)
    await producer.start()
    print(f"  ✅ {producer.name} started")
    
    processor = DataProcessorModule(registry)
    await processor.start()
    print(f"  ✅ {processor.name} started")
    
    analyzer = DataAnalyzerModule(registry)
    await analyzer.start()
    print(f"  ✅ {analyzer.name} started")
    
    orchestrator = OrchestratorModule(registry)
    await orchestrator.start()
    print(f"  ✅ {orchestrator.name} started")
    
    # Show registered modules
    print("\n📋 Registered Modules:")
    for module in registry.list_modules():
        print(f"  • {module.name}")
        print(f"    Capabilities: {', '.join(module.capabilities)}")
        print(f"    Status: {module.status}")
    
    # Show module compatibility graph
    print("\n🔗 Module Compatibility Graph:")
    graph = registry.get_module_graph()
    for source, targets in graph.items():
        if targets:
            print(f"  {source} → {', '.join(targets)}")
    
    # Demonstrate dynamic discovery
    print("\n🔍 Dynamic Module Discovery:")
    
    # Producer discovers processors
    processors = await producer.discover_modules("data_processing")
    print(f"  Producer found processors: {processors}")
    
    # Processor discovers analyzers
    analyzers = await processor.discover_modules("data_analysis")
    print(f"  Processor found analyzers: {analyzers}")
    
    # Find compatible modules
    compatible = await producer.find_compatible_modules()
    print(f"  Modules compatible with Producer output: {compatible}")
    
    # Demonstrate communication
    print("\n💬 Module Communication Demo:")
    print("  (Note: This requires Claude CLI to be installed)")
    
    try:
        # Method 1: Direct module processing (triggers internal communication)
        print("\n  1️⃣ Direct Processing with Auto-Communication:")
        result = await producer.process({
            "data_type": "numeric",
            "count": 5,
            "parameters": {"min": 0, "max": 100}
        })
        print(f"     Producer created batch: {result['batch_id']}")
        print(f"     Data: {result['data_batch']}")
        
        # Method 2: Orchestrated workflow
        print("\n  2️⃣ Orchestrated Workflow:")
        workflow_result = await orchestrator.process({
            "workflow": "simple_pipeline",
            "parameters": {
                "data_type": "text",
                "count": 5
            }
        })
        print(f"     Workflow ID: {workflow_result['workflow_id']}")
        print(f"     Status: {workflow_result['status']}")
        
        # Method 3: Broadcast communication
        print("\n  3️⃣ Broadcast Communication:")
        broadcast_results = await producer.broadcast(
            message_type="announcement",
            content={"message": "New data batch available"},
            capability_filter="data_processing"
        )
        print(f"     Broadcast sent to {len(broadcast_results)} modules")
        
    except Exception as e:
        print(f"\n  ⚠️  Communication error: {e}")
        print("     (Make sure Claude CLI is installed and accessible)")
    
    # Show communication history
    print("\n📊 Communication History:")
    history = producer.communicator.get_communication_history()
    print(f"  Total communications: {len(history)}")
    for comm in history[-3:]:  # Show last 3
        print(f"  • {comm.source_module} → {comm.target_module}: {comm.status}")
    
    # Demonstrate module status updates
    print("\n🔄 Module Status Management:")
    
    # Simulate error state
    registry.update_module_status("DataProcessor", "error")
    print("  Set DataProcessor to error state")
    
    # Check active modules
    active_modules = registry.list_modules(status="active")
    print(f"  Active modules: {[m.name for m in active_modules]}")
    
    # Restore status
    registry.update_module_status("DataProcessor", "active")
    print("  Restored DataProcessor to active state")
    
    # Stop all modules
    print("\n🛑 Stopping all modules...")
    for module in [producer, processor, analyzer, orchestrator]:
        await module.stop()
        print(f"  ✅ {module.name} stopped")
    
    # Cleanup
    import os
    if os.path.exists("demo_registry.json"):
        os.remove("demo_registry.json")
        print("\n🧹 Cleaned up registry file")
    
    print("\n✨ Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())