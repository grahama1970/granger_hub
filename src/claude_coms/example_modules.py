"""
Example modules demonstrating dynamic inter-module communication.

Purpose: Provides concrete implementations of BaseModule to demonstrate
how modules can dynamically discover and communicate with each other.
"""

import asyncio
import random
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_module import BaseModule
from .module_registry import ModuleRegistry


class DataProducerModule(BaseModule):
    """Module that produces data and sends it to processors."""
    
    def __init__(self, registry: ModuleRegistry):
        super().__init__(
            name="DataProducer",
            system_prompt=(
                "You are a data production module that generates various types of data "
                "and sends it to appropriate processing modules. You can produce numeric data, "
                "text data, or structured records based on requests."
            ),
            capabilities=["data_generation", "data_streaming", "batch_production"],
            registry=registry
        )
        self.production_count = 0
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data_type": {
                    "type": "string",
                    "enum": ["numeric", "text", "records"]
                },
                "count": {"type": "integer", "minimum": 1},
                "parameters": {"type": "object"}
            },
            "required": ["data_type", "count"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data_batch": {"type": "array"},
                "batch_id": {"type": "string"},
                "timestamp": {"type": "string"},
                "data_type": {"type": "string"}
            }
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data based on request."""
        data_type = data.get("data_type", "numeric")
        count = data.get("count", 10)
        params = data.get("parameters", {})
        
        # Generate data based on type
        if data_type == "numeric":
            data_batch = [random.uniform(0, 100) for _ in range(count)]
        elif data_type == "text":
            words = ["alpha", "beta", "gamma", "delta", "epsilon"]
            data_batch = [random.choice(words) for _ in range(count)]
        else:  # records
            data_batch = [
                {
                    "id": i,
                    "value": random.uniform(0, 100),
                    "category": random.choice(["A", "B", "C"])
                }
                for i in range(count)
            ]
        
        self.production_count += count
        batch_id = f"batch_{self.production_count:04d}"
        
        result = {
            "data_batch": data_batch,
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "data_type": data_type
        }
        
        # Find processors and send data
        processors = await self.discover_modules("data_processing")
        if processors:
            print(f"📤 Sending batch {batch_id} to {len(processors)} processors")
            for processor in processors:
                await self.send_to(
                    processor,
                    "process_data",
                    result
                )
        
        return result


class DataProcessorModule(BaseModule):
    """Module that processes incoming data."""
    
    def __init__(self, registry: ModuleRegistry):
        super().__init__(
            name="DataProcessor",
            system_prompt=(
                "You are a data processing module that transforms and analyzes data. "
                "You can aggregate numeric data, analyze text patterns, and process structured records. "
                "You apply various transformations and extract meaningful statistics."
            ),
            capabilities=["data_processing", "aggregation", "transformation"],
            registry=registry
        )
        self.processed_batches = 0
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data_batch": {"type": "array"},
                "batch_id": {"type": "string"},
                "data_type": {"type": "string"}
            },
            "required": ["data_batch"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "processed_data": {"type": "object"},
                "statistics": {"type": "object"},
                "batch_id": {"type": "string"},
                "processing_time": {"type": "number"}
            }
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming data batch."""
        start_time = datetime.now()
        
        data_batch = data.get("data_batch", [])
        batch_id = data.get("batch_id", "unknown")
        data_type = data.get("data_type", "unknown")
        
        # Process based on data type
        if data_type == "numeric":
            processed = {
                "sum": sum(data_batch),
                "average": sum(data_batch) / len(data_batch) if data_batch else 0,
                "min": min(data_batch) if data_batch else None,
                "max": max(data_batch) if data_batch else None
            }
            statistics = {
                "count": len(data_batch),
                "std_dev": self._calculate_std_dev(data_batch)
            }
        elif data_type == "text":
            word_counts = {}
            for word in data_batch:
                word_counts[word] = word_counts.get(word, 0) + 1
            processed = {"word_counts": word_counts}
            statistics = {
                "unique_words": len(word_counts),
                "total_words": len(data_batch)
            }
        else:  # records
            processed = {
                "by_category": self._group_by_category(data_batch),
                "value_sum": sum(r.get("value", 0) for r in data_batch)
            }
            statistics = {
                "record_count": len(data_batch),
                "categories": len(processed["by_category"])
            }
        
        self.processed_batches += 1
        processing_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            "processed_data": processed,
            "statistics": statistics,
            "batch_id": batch_id,
            "processing_time": processing_time
        }
        
        # Find analyzers and send results
        analyzers = await self.discover_modules("data_analysis")
        if analyzers:
            print(f"📤 Sending processed batch {batch_id} to analyzers")
            for analyzer in analyzers:
                await self.send_to(
                    analyzer,
                    "analyze_data",
                    result
                )
        
        return result
    
    def _calculate_std_dev(self, data: List[float]) -> float:
        """Calculate standard deviation."""
        if not data:
            return 0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return variance ** 0.5
    
    def _group_by_category(self, records: List[Dict]) -> Dict:
        """Group records by category."""
        groups = {}
        for record in records:
            category = record.get("category", "unknown")
            if category not in groups:
                groups[category] = []
            groups[category].append(record)
        return groups


class DataAnalyzerModule(BaseModule):
    """Module that analyzes processed data for insights."""
    
    def __init__(self, registry: ModuleRegistry):
        super().__init__(
            name="DataAnalyzer",
            system_prompt=(
                "You are a data analysis module that finds patterns and generates insights. "
                "You can detect anomalies, identify trends, and provide recommendations "
                "based on processed data and statistics."
            ),
            capabilities=["data_analysis", "pattern_recognition", "anomaly_detection"],
            registry=registry
        )
        self.analysis_count = 0
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "processed_data": {"type": "object"},
                "statistics": {"type": "object"},
                "batch_id": {"type": "string"}
            },
            "required": ["processed_data", "statistics"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "insights": {"type": "array"},
                "anomalies": {"type": "array"},
                "recommendations": {"type": "array"},
                "confidence": {"type": "number"}
            }
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze processed data for insights."""
        processed_data = data.get("processed_data", {})
        statistics = data.get("statistics", {})
        batch_id = data.get("batch_id", "unknown")
        
        insights = []
        anomalies = []
        recommendations = []
        
        # Analyze based on data structure
        if "average" in processed_data:  # Numeric data
            avg = processed_data["average"]
            if avg > 75:
                insights.append("High average value detected")
                recommendations.append("Consider investigating high value sources")
            elif avg < 25:
                insights.append("Low average value detected")
                recommendations.append("Review data collection parameters")
            
            if statistics.get("std_dev", 0) > 30:
                anomalies.append("High variance in data")
        
        elif "word_counts" in processed_data:  # Text data
            word_counts = processed_data["word_counts"]
            total = statistics.get("total_words", 0)
            unique = statistics.get("unique_words", 0)
            
            if unique < total * 0.3:
                insights.append("Low vocabulary diversity")
                recommendations.append("Consider expanding data sources")
            
            # Find most common word
            if word_counts:
                most_common = max(word_counts.items(), key=lambda x: x[1])
                insights.append(f"Most frequent: {most_common[0]} ({most_common[1]} times)")
        
        elif "by_category" in processed_data:  # Record data
            categories = processed_data["by_category"]
            if len(categories) == 1:
                anomalies.append("All records in single category")
                recommendations.append("Verify categorization logic")
        
        self.analysis_count += 1
        confidence = 0.8 if insights else 0.5
        
        result = {
            "insights": insights,
            "anomalies": anomalies,
            "recommendations": recommendations,
            "confidence": confidence,
            "analysis_id": f"analysis_{self.analysis_count:04d}",
            "batch_id": batch_id
        }
        
        print(f"📊 Analysis complete for batch {batch_id}")
        return result


class OrchestratorModule(BaseModule):
    """Module that orchestrates workflows between other modules."""
    
    def __init__(self, registry: ModuleRegistry):
        super().__init__(
            name="Orchestrator",
            system_prompt=(
                "You are an orchestration module that coordinates workflows between other modules. "
                "You can create data pipelines, manage module interactions, and monitor overall system flow."
            ),
            capabilities=["orchestration", "workflow_management", "monitoring"],
            registry=registry
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "workflow": {
                    "type": "string",
                    "enum": ["simple_pipeline", "parallel_processing", "conditional_flow"]
                },
                "parameters": {"type": "object"}
            },
            "required": ["workflow"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string"},
                "status": {"type": "string"},
                "results": {"type": "array"},
                "execution_time": {"type": "number"}
            }
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow."""
        workflow = data.get("workflow", "simple_pipeline")
        params = data.get("parameters", {})
        
        start_time = datetime.now()
        workflow_id = f"workflow_{int(start_time.timestamp())}"
        results = []
        
        if workflow == "simple_pipeline":
            # Producer -> Processor -> Analyzer pipeline
            print(f"🎯 Starting simple pipeline workflow")
            
            # Check if modules exist
            producer = await self.discover_modules("data_generation")
            if producer:
                # Send production request
                prod_result = await self.send_to(
                    producer[0],
                    "process",
                    {
                        "data_type": params.get("data_type", "numeric"),
                        "count": params.get("count", 20)
                    }
                )
                results.append({
                    "stage": "production",
                    "status": prod_result.status if prod_result else "failed"
                })
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "results": results,
            "execution_time": execution_time
        }


# Demo script
async def demo_dynamic_communication():
    """Demonstrate dynamic module communication."""
    print("🚀 Starting Dynamic Module Communication Demo\n")
    
    # Create shared registry
    registry = ModuleRegistry("demo_registry.json")
    
    # Create and start modules
    producer = DataProducerModule(registry)
    processor = DataProcessorModule(registry)
    analyzer = DataAnalyzerModule(registry)
    orchestrator = OrchestratorModule(registry)
    
    # Start all modules
    await producer.start()
    await processor.start()
    await analyzer.start()
    await orchestrator.start()
    
    print("\n📋 Registered Modules:")
    for module in registry.list_modules():
        print(f"  - {module.name}: {', '.join(module.capabilities)}")
    
    print("\n🔗 Module Compatibility Graph:")
    graph = registry.get_module_graph()
    for source, targets in graph.items():
        if targets:
            print(f"  {source} → {', '.join(targets)}")
    
    print("\n🎬 Starting workflow...\n")
    
    # Execute a workflow through orchestrator
    result = await orchestrator.send_to(
        "Orchestrator",  # Self-call for demo
        "process",
        {
            "workflow": "simple_pipeline",
            "parameters": {
                "data_type": "numeric",
                "count": 10
            }
        }
    )
    
    if result:
        print(f"\n✅ Workflow completed!")
        print(f"Status: {result.status}")
    
    # Stop all modules
    await producer.stop()
    await processor.stop()
    await analyzer.stop()
    await orchestrator.stop()
    
    # Cleanup
    import os
    if os.path.exists("demo_registry.json"):
        os.remove("demo_registry.json")


if __name__ == "__main__":
    asyncio.run(demo_dynamic_communication())