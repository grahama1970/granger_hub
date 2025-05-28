#!/usr/bin/env python3
"""
Demo showing the module system without requiring Claude CLI.

This demonstrates:
1. Module registration and discovery
2. Schema compatibility checking
3. Module lifecycle management
4. Dynamic capability-based discovery
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.claude_coms import ModuleRegistry, BaseModule


class SensorModule(BaseModule):
    """Simulates a sensor that produces readings."""
    
    def __init__(self, registry):
        super().__init__(
            name="TemperatureSensor",
            system_prompt="I am a temperature sensor that produces readings",
            capabilities=["sensor", "temperature", "data_source"],
            registry=registry
        )
    
    def get_input_schema(self):
        return None  # Sensors don't have input
    
    def get_output_schema(self):
        return {
            "type": "object",
            "properties": {
                "temperature": {"type": "number"},
                "unit": {"type": "string"},
                "timestamp": {"type": "string"}
            }
        }
    
    async def process(self, data):
        import random
        from datetime import datetime
        return {
            "temperature": round(random.uniform(20, 30), 1),
            "unit": "celsius",
            "timestamp": datetime.now().isoformat()
        }


class ConverterModule(BaseModule):
    """Converts temperature units."""
    
    def __init__(self, registry):
        super().__init__(
            name="TemperatureConverter",
            system_prompt="I convert temperature between units",
            capabilities=["converter", "temperature", "data_processor"],
            registry=registry
        )
    
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "temperature": {"type": "number"},
                "unit": {"type": "string"}
            }
        }
    
    def get_output_schema(self):
        return {
            "type": "object",
            "properties": {
                "celsius": {"type": "number"},
                "fahrenheit": {"type": "number"},
                "kelvin": {"type": "number"}
            }
        }
    
    async def process(self, data):
        temp = data.get("temperature", 0)
        unit = data.get("unit", "celsius").lower()
        
        # Convert to celsius first
        if unit == "fahrenheit":
            celsius = (temp - 32) * 5/9
        elif unit == "kelvin":
            celsius = temp - 273.15
        else:
            celsius = temp
        
        return {
            "celsius": round(celsius, 1),
            "fahrenheit": round(celsius * 9/5 + 32, 1),
            "kelvin": round(celsius + 273.15, 1)
        }


class AlertModule(BaseModule):
    """Monitors temperature and generates alerts."""
    
    def __init__(self, registry):
        super().__init__(
            name="TemperatureAlert",
            system_prompt="I monitor temperature and generate alerts",
            capabilities=["monitor", "alert", "temperature"],
            registry=registry
        )
        self.threshold_celsius = 25
    
    def get_input_schema(self):
        return {
            "type": "object",
            "properties": {
                "celsius": {"type": "number"}
            }
        }
    
    def get_output_schema(self):
        return {
            "type": "object",
            "properties": {
                "alert": {"type": "boolean"},
                "message": {"type": "string"},
                "severity": {"type": "string"}
            }
        }
    
    async def process(self, data):
        celsius = data.get("celsius", 0)
        
        if celsius > self.threshold_celsius:
            return {
                "alert": True,
                "message": f"High temperature: {celsius}°C (threshold: {self.threshold_celsius}°C)",
                "severity": "warning"
            }
        else:
            return {
                "alert": False,
                "message": f"Temperature normal: {celsius}°C",
                "severity": "info"
            }


async def main():
    print("🌡️  Temperature Monitoring System Demo")
    print("=" * 50)
    
    # Create registry
    registry = ModuleRegistry()
    
    # Create and register modules
    sensor = SensorModule(registry)
    converter = ConverterModule(registry)
    alert = AlertModule(registry)
    
    # Start modules
    for module in [sensor, converter, alert]:
        await module.start()
    
    # Show system overview
    print("\n📊 System Overview:")
    print(f"Total modules: {len(registry.list_modules())}")
    
    print("\n📋 Module Details:")
    for module_info in registry.list_modules():
        print(f"\n• {module_info.name}")
        print(f"  Capabilities: {', '.join(module_info.capabilities)}")
        if module_info.input_schema:
            props = module_info.input_schema.get("properties", {})
            print(f"  Inputs: {', '.join(props.keys())}")
        if module_info.output_schema:
            props = module_info.output_schema.get("properties", {})
            print(f"  Outputs: {', '.join(props.keys())}")
    
    # Show compatibility graph
    print("\n🔗 Data Flow Compatibility:")
    graph = registry.get_module_graph()
    for source, targets in graph.items():
        if targets:
            print(f"  {source} → {', '.join(targets)}")
    
    # Demonstrate dynamic discovery
    print("\n🔍 Dynamic Discovery Examples:")
    
    # Find all sensors
    sensors = registry.find_modules_by_capability("sensor")
    print(f"  Sensors: {[m.name for m in sensors]}")
    
    # Find temperature-related modules
    temp_modules = registry.find_modules_by_capability("temperature")
    print(f"  Temperature modules: {[m.name for m in temp_modules]}")
    
    # Find data processors
    processors = registry.find_modules_by_capability("data_processor")
    print(f"  Data processors: {[m.name for m in processors]}")
    
    # Simulate data flow
    print("\n🔄 Simulating Data Flow:")
    
    # 1. Get sensor reading
    sensor_data = await sensor.process({})
    print(f"\n1. Sensor reading: {sensor_data['temperature']}°{sensor_data['unit']}")
    
    # 2. Convert temperature
    converted_data = await converter.process(sensor_data)
    print(f"2. Converted: {converted_data['celsius']}°C / {converted_data['fahrenheit']}°F")
    
    # 3. Check for alerts
    alert_data = await alert.process(converted_data)
    print(f"3. Alert status: {alert_data['message']}")
    
    # Demonstrate finding compatible modules
    print("\n🔍 Finding Compatible Modules:")
    
    # What can process sensor output?
    sensor_compatible = registry.find_compatible_modules(
        sensor.get_output_schema()
    )
    print(f"  Modules that can process sensor output: {[m.name for m in sensor_compatible]}")
    
    # What can process converter output?
    converter_compatible = registry.find_compatible_modules(
        converter.get_output_schema()
    )
    print(f"  Modules that can process converter output: {[m.name for m in converter_compatible]}")
    
    # Stop all modules
    print("\n🛑 Stopping modules...")
    for module in [sensor, converter, alert]:
        await module.stop()
    
    print("\n✅ Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())