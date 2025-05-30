#!/usr/bin/env python3
"""
Real data validation test for ModuleCommunicator per CLAUDE.md standards.

This test uses ONLY real data and NO mocking.
"""

import asyncio
import json
from pathlib import Path
import tempfile
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_coms.core.modules import ModuleRegistry, ModuleInfo
from claude_coms.core.modules.example_modules import DataProducerModule, DataProcessorModule


async def validate_module_registry():
    """Validate ModuleRegistry with real data."""
    print("\n1️⃣ Testing ModuleRegistry with Real Data...")
    
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        registry = ModuleRegistry(tf.name)
        
        # Test 1: Register real module info
        module_info = ModuleInfo(
            name="RealDataModule",
            system_prompt="A module for processing real sensor data",
            capabilities=["sensor", "data_processing", "validation"],
            input_schema={
                "type": "object",
                "properties": {
                    "sensor_data": {"type": "array"},
                    "timestamp": {"type": "string"}
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "processed": {"type": "boolean"},
                    "results": {"type": "object"}
                }
            },
            metadata={"version": "1.0.0", "author": "test"}
        )
        
        # Register and verify
        assert registry.register_module(module_info)
        retrieved = registry.get_module("RealDataModule")
        assert retrieved is not None
        assert retrieved.name == "RealDataModule"
        assert len(retrieved.capabilities) == 3
        print("✅ Module registration successful")
        
        # Test 2: Capability search with real modules
        # Register more modules
        for i in range(3):
            info = ModuleInfo(
                name=f"Sensor{i}",
                system_prompt=f"Sensor module {i}",
                capabilities=["sensor", f"type_{i}"]
            )
            registry.register_module(info)
        
        sensors = registry.find_modules_by_capability("sensor")
        assert len(sensors) == 4  # RealDataModule + 3 sensors
        print(f"✅ Found {len(sensors)} sensor modules")
        
        # Test 3: Schema compatibility
        producer_schema = {
            "type": "object",
            "properties": {
                "data": {"type": "array"},
                "metadata": {"type": "object"}
            }
        }
        
        compatible = registry.find_compatible_modules(producer_schema, strict=False)
        print(f"✅ Found {len(compatible)} compatible modules")
        
        # Cleanup
        Path(tf.name).unlink()
        
    return True


async def validate_data_pipeline():
    """Validate real data pipeline."""
    print("\n2️⃣ Testing Data Pipeline with Real Data...")
    
    registry = ModuleRegistry()
    
    # Create real modules
    producer = DataProducerModule(registry)
    processor = DataProcessorModule(registry)
    
    # Start modules
    await producer.start()
    await processor.start()
    
    # Test real data generation
    print("\n📊 Generating real data...")
    prod_result = await producer.process({
        "data_type": "numeric",
        "count": 50,
        "seed": 42  # For reproducibility
    })
    
    # Validate produced data
    assert "data_batch" in prod_result
    assert len(prod_result["data_batch"]) == 50
    assert all(isinstance(x, (int, float)) for x in prod_result["data_batch"])
    assert "batch_id" in prod_result
    assert "timestamp" in prod_result
    print(f"✅ Generated {len(prod_result['data_batch'])} real numeric values")
    
    # Test real data processing
    print("\n⚙️ Processing real data...")
    proc_result = await processor.process(prod_result)
    
    # Validate processed results
    assert "processed_data" in proc_result
    assert "statistics" in proc_result
    assert proc_result["statistics"]["count"] == 50
    assert "min" in proc_result["statistics"]
    assert "max" in proc_result["statistics"]
    assert "average" in proc_result["processed_data"]
    assert "sorted" in proc_result["processed_data"]
    assert len(proc_result["processed_data"]["sorted"]) == 50
    
    # Verify sorting is correct
    sorted_data = proc_result["processed_data"]["sorted"]
    assert all(sorted_data[i] <= sorted_data[i+1] for i in range(len(sorted_data)-1))
    
    print(f"✅ Processed data successfully")
    print(f"   - Average: {proc_result['processed_data']['average']:.2f}")
    print(f"   - Min: {proc_result['statistics']['min']:.2f}")
    print(f"   - Max: {proc_result['statistics']['max']:.2f}")
    
    # Stop modules
    await producer.stop()
    await processor.stop()
    
    return True


async def validate_module_discovery():
    """Validate module discovery with real modules."""
    print("\n3️⃣ Testing Module Discovery with Real Data...")
    
    registry = ModuleRegistry()
    
    # Create and register multiple real modules
    modules = []
    module_types = [
        ("DataProducer", DataProducerModule),
        ("DataProcessor", DataProcessorModule)
    ]
    
    for name, ModuleClass in module_types:
        module = ModuleClass(registry)
        await module.start()
        modules.append(module)
    
    # Test discovery from first module
    discovered = await modules[0].discover_modules()
    print(f"✅ Discovered {len(discovered)} modules")
    
    # Verify discovered modules
    assert "DataProcessor" in discovered
    
    # Test capability-based discovery
    data_gen_modules = await modules[1].discover_modules("data_generation")
    assert "DataProducer" in data_gen_modules
    print(f"✅ Found {len(data_gen_modules)} data generation modules")
    
    # Stop all modules
    for module in modules:
        await module.stop()
    
    return True


async def validate_text_data():
    """Validate with text data type."""
    print("\n4️⃣ Testing Text Data Processing...")
    
    registry = ModuleRegistry()
    producer = DataProducerModule(registry)
    
    await producer.start()
    
    # Generate text data
    text_result = await producer.process({
        "data_type": "text",
        "count": 10
    })
    
    assert "data_batch" in text_result
    assert len(text_result["data_batch"]) == 10
    assert all(isinstance(x, str) for x in text_result["data_batch"])
    assert text_result["data_type"] == "text"
    
    print(f"✅ Generated {len(text_result['data_batch'])} text samples")
    print(f"   Sample: '{text_result['data_batch'][0][:50]}...'")
    
    await producer.stop()
    
    return True


async def main():
    """Run all validation tests."""
    print("🚀 Starting Real Data Validation (NO MOCKING)\n")
    print("=" * 60)
    
    try:
        # Run all validations
        results = []
        results.append(await validate_module_registry())
        results.append(await validate_data_pipeline())
        results.append(await validate_module_discovery())
        results.append(await validate_text_data())
        
        # Summary
        print("\n" + "=" * 60)
        if all(results):
            print("\n✨ ALL VALIDATION TESTS PASSED WITH REAL DATA!")
            print("   - No mocking used")
            print("   - All data was real")
            print("   - All assertions validated actual functionality")
            return True
        else:
            print("\n❌ Some tests failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Validation error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)