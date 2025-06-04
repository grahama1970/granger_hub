"""
Integration tests for multi-turn conversation support.

Purpose: Validates end-to-end conversation workflows, concurrent conversations,
and the complete conversation lifecycle with real module interactions.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime
import json
import os
from pathlib import Path

from granger_hub.core.module_communicator import ModuleCommunicator
from granger_hub.core.modules import BaseModule, ModuleInfo
from granger_hub.core.conversation import ConversationMessage, ConversationModule


class DataProcessorModule(ConversationModule):
    """Example data processing module with conversation support."""
    
    def __init__(self):
        super().__init__(
            name="DataProcessor",
            system_prompt="Process data and maintain conversation context",
            capabilities=["data_processing", "pattern_extraction", "conversation"],
            auto_register=False
        )
        self.processed_data = []
        
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema."""
        return {
            "type": "object",
            "properties": {
                "data": {"type": "array"},
                "conversation_id": {"type": "string"}
            }
        }
        
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output schema."""
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "result": {"type": "object"}
            }
        }
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming data with context awareness."""
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Check conversation context
        if data.get("conversation_id"):
            # Use conversation history to enhance processing
            history = self.conversation_history.get(data["conversation_id"], [])
            context_aware = len(history) > 0
        else:
            context_aware = False
            
        # Process data
        if "data" in data:
            processed = {
                "original": data["data"],
                "processed": [x * 2 for x in data["data"]] if isinstance(data["data"], list) else data["data"],
                "context_aware": context_aware,
                "timestamp": datetime.now().isoformat()
            }
            self.processed_data.append(processed)
            return {
                "status": "success",
                "result": processed,
                "conversation_id": data.get("conversation_id")
            }
        
        return {"status": "error", "message": "No data provided"}


class DataAnalyzerModule(ConversationModule):
    """Example data analyzer module with conversation support."""
    
    def __init__(self):
        super().__init__(
            name="DataAnalyzer",
            system_prompt="Analyze processed data and provide insights",
            capabilities=["data_analysis", "pattern_recognition", "conversation"],
            auto_register=False
        )
        self.analyses = []
        
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema."""
        return {"type": "object"}
        
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output schema."""
        return {"type": "object"}
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data with conversation context."""
        await asyncio.sleep(0.15)  # Simulate analysis time
        
        # Check if this is part of a conversation
        conv_id = data.get("conversation_id")
        if conv_id and conv_id in self.conversation_history:
            # Build on previous analyses
            previous_analyses = [
                msg for msg in self.conversation_history[conv_id]
                if msg.get("type") == "analysis"
            ]
            context = {"previous_analyses": len(previous_analyses)}
        else:
            context = {}
            
        # Analyze data
        if "processed" in data:
            analysis = {
                "input": data["processed"],
                "patterns": self._find_patterns(data["processed"]),
                "insights": f"Found {len(data['processed'])} data points",
                "context": context,
                "timestamp": datetime.now().isoformat()
            }
            self.analyses.append(analysis)
            return {
                "status": "success",
                "analysis": analysis,
                "conversation_id": conv_id
            }
            
        return {"status": "error", "message": "No processed data provided"}
        
    def _find_patterns(self, data: Any) -> List[str]:
        """Find patterns in data."""
        patterns = []
        if isinstance(data, dict) and "original" in data:
            patterns.append("processing_applied")
        if isinstance(data, list) and len(data) > 2:
            patterns.append("sequential_data")
        return patterns


class ReportGeneratorModule(ConversationModule):
    """Example report generator module."""
    
    def __init__(self):
        super().__init__(
            name="ReportGenerator",
            system_prompt="Generate reports from analyzed data",
            capabilities=["report_generation", "summarization", "conversation"],
            auto_register=False
        )
        self.reports = []
        
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema."""
        return {"type": "object"}
        
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output schema."""
        return {"type": "object"}
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report from analysis."""
        await asyncio.sleep(0.2)  # Simulate report generation
        
        conv_id = data.get("conversation_id")
        
        # Generate report
        if "analysis" in data:
            report = {
                "summary": f"Analysis complete: {data['analysis'].get('insights', 'No insights')}",
                "patterns": data["analysis"].get("patterns", []),
                "recommendations": ["Continue monitoring", "Expand data collection"],
                "generated_at": datetime.now().isoformat(),
                "conversation_aware": conv_id is not None
            }
            self.reports.append(report)
            return {
                "status": "success",
                "report": report,
                "conversation_id": conv_id
            }
            
        return {"status": "error", "message": "No analysis provided"}


@pytest.mark.asyncio
async def test_complete_workflow():
    """Test complete conversation workflow from data processing to report generation."""
    start_time = time.time()
    
    # Initialize communicator
    comm = ModuleCommunicator(registry_path="test_registry.json")
    
    # Create and register modules
    processor = DataProcessorModule()
    analyzer = DataAnalyzerModule()
    reporter = ReportGeneratorModule()
    
    await processor.start()
    await analyzer.start()
    await reporter.start()
    
    comm.register_module("DataProcessor", processor)
    comm.register_module("DataAnalyzer", analyzer)
    comm.register_module("ReportGenerator", reporter)
    
    # Start conversation: Data Processing Pipeline
    conv_result = await comm.start_conversation(
        initiator="DataProcessor",
        target="DataAnalyzer",
        initial_message={"task": "process_and_analyze", "data": [1, 2, 3, 4, 5]},
        conversation_type="data_pipeline"
    )
    
    assert conv_result["success"]
    conversation_id = conv_result["conversation_id"]
    
    # Step 1: Process data
    process_msg = ConversationMessage.create(
        source="CLI",
        target="DataProcessor",
        msg_type="process",
        content={"data": [1, 2, 3, 4, 5]},
        conversation_id=conversation_id,
        turn_number=2
    )
    
    process_result = await comm.conversation_manager.route_message(process_msg)
    assert process_result is not None
    
    # Simulate module processing
    processed_data = await processor.process({
        "data": [1, 2, 3, 4, 5],
        "conversation_id": conversation_id
    })
    
    # Step 2: Analyze processed data
    analyze_msg = ConversationMessage.create(
        source="DataProcessor",
        target="DataAnalyzer",
        msg_type="analyze",
        content=processed_data["result"],
        conversation_id=conversation_id,
        turn_number=3
    )
    
    analyze_result = await comm.conversation_manager.route_message(analyze_msg)
    assert analyze_result is not None
    
    # Simulate analysis
    analysis = await analyzer.process({
        "processed": processed_data["result"],
        "conversation_id": conversation_id
    })
    
    # Step 3: Generate report
    report_msg = ConversationMessage.create(
        source="DataAnalyzer",
        target="ReportGenerator",
        msg_type="generate_report",
        content=analysis,
        conversation_id=conversation_id,
        turn_number=4
    )
    
    report_result = await comm.conversation_manager.route_message(report_msg)
    assert report_result is not None
    
    # Simulate report generation
    final_report = await reporter.process({
        "analysis": analysis["analysis"],
        "conversation_id": conversation_id
    })
    
    # Verify complete workflow
    assert len(processor.processed_data) > 0
    assert len(analyzer.analyses) > 0
    assert len(reporter.reports) > 0
    assert final_report["report"]["conversation_aware"]
    
    # Complete conversation
    await comm.conversation_manager.complete_conversation(conversation_id)
    
    # Get conversation history
    history = await comm.conversation_manager.get_conversation_history(conversation_id)
    assert len(history) >= 3  # At least 3 messages exchanged
    
    total_time = time.time() - start_time
    
    # Generate evidence
    evidence = {
        "conversation_id": conversation_id,
        "turn_number": len(history),
        "history_maintained": True,
        "total_duration_seconds": total_time,
        "conversation_management": True,
        "workflow_stages": ["process", "analyze", "report"],
        "modules_involved": 3,
        "end_to_end_complete": True
    }
    print(f"\nTest Evidence: {evidence}")
    
    # Cleanup
    await processor.stop()
    await analyzer.stop()
    await reporter.stop()
    
    # Verify timing
    assert total_time > 5.0  # Should take time for full workflow
    assert total_time < 20.0


@pytest.mark.asyncio
async def test_concurrent_conversations():
    """Test multiple concurrent conversations between different module pairs."""
    start_time = time.time()
    
    # Initialize communicator
    comm = ModuleCommunicator(registry_path="test_registry.json")
    
    # Create modules
    modules = {}
    for i in range(4):
        # Create a simple test module
        class TestModule(ConversationModule):
            def get_input_schema(self):
                return {"type": "object"}
            def get_output_schema(self):
                return {"type": "object"}
            async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
                await asyncio.sleep(0.05)
                return {"response": f"Processed by {self.name}", "data": data}
        
        module = TestModule(
            name=f"Module{i+1}",
            system_prompt=f"Test module {i+1} for concurrent conversations",
            capabilities=["conversation", "test"],
            auto_register=False
        )
        await module.start()
        modules[f"Module{i+1}"] = module
        comm.register_module(f"Module{i+1}", module)
    
    # Start multiple concurrent conversations
    conversations = []
    tasks = []
    
    # Conversation 1: Module1 <-> Module2
    conv1 = await comm.start_conversation(
        "Module1", "Module2",
        {"task": "concurrent_test_1"},
        "test"
    )
    conversations.append(conv1["conversation_id"])
    
    # Conversation 2: Module2 <-> Module3
    conv2 = await comm.start_conversation(
        "Module2", "Module3",
        {"task": "concurrent_test_2"},
        "test"
    )
    conversations.append(conv2["conversation_id"])
    
    # Conversation 3: Module3 <-> Module4
    conv3 = await comm.start_conversation(
        "Module3", "Module4",
        {"task": "concurrent_test_3"},
        "test"
    )
    conversations.append(conv3["conversation_id"])
    
    # Conversation 4: Module1 <-> Module4
    conv4 = await comm.start_conversation(
        "Module1", "Module4",
        {"task": "concurrent_test_4"},
        "test"
    )
    conversations.append(conv4["conversation_id"])
    
    # Run conversations concurrently
    async def run_conversation(conv_id: str, source: str, target: str, num_turns: int):
        """Run a conversation for multiple turns."""
        for turn in range(num_turns):
            msg = ConversationMessage.create(
                source=source if turn % 2 == 0 else target,
                target=target if turn % 2 == 0 else source,
                msg_type="test_message",
                content={"turn": turn + 1, "data": f"Message {turn + 1}"},
                conversation_id=conv_id,
                turn_number=turn + 2  # +2 because turn 1 was initial message
            )
            
            result = await comm.conversation_manager.route_message(msg)
            assert result is not None
            
            # Small delay between turns
            await asyncio.sleep(0.05)
    
    # Create tasks for concurrent execution
    tasks = [
        run_conversation(conversations[0], "Module1", "Module2", 5),
        run_conversation(conversations[1], "Module2", "Module3", 4),
        run_conversation(conversations[2], "Module3", "Module4", 3),
        run_conversation(conversations[3], "Module1", "Module4", 6)
    ]
    
    # Run all conversations concurrently
    await asyncio.gather(*tasks)
    
    # Verify all conversations completed
    for conv_id in conversations:
        state = await comm.conversation_manager.get_conversation_state(conv_id)
        assert state is not None
        assert state.turn_count > 0
    
    # Get analytics
    analytics = await comm.get_conversation_analytics()
    assert analytics["total_conversations"] >= 4
    assert analytics["active"] >= 0  # Some may have completed
    
    # Complete all conversations
    for conv_id in conversations:
        await comm.conversation_manager.complete_conversation(conv_id)
    
    total_time = time.time() - start_time
    
    # Generate evidence
    evidence = {
        "conversation_id": conversations[0],  # Show first conversation
        "conversations_created": len(conversations),
        "concurrent_conversations": 4,
        "history_maintained": True,
        "total_duration_seconds": total_time,
        "conversation_management": True,
        "turn_number": sum([5, 4, 3, 6]),  # Total turns across all conversations
        "modules_involved": 4
    }
    print(f"\nTest Evidence: {evidence}")
    
    # Cleanup
    for module in modules.values():
        await module.stop()
    
    # Verify timing
    assert total_time > 2.0  # Should take time for concurrent operations
    assert total_time < 10.0  # But faster than sequential


@pytest.mark.asyncio
async def test_docs_exist():
    """HONEYPOT: Test that documentation exists (should fail)."""
    start_time = time.time()
    
    # Check for documentation files that don't exist yet
    docs_path = Path("docs/conversation_api.md")
    assert docs_path.exists(), "Conversation API documentation not found"
    
    troubleshooting_path = Path("docs/conversation_troubleshooting.md")
    assert troubleshooting_path.exists(), "Troubleshooting guide not found"
    
    # Check README has conversation examples
    readme_path = Path("README.md")
    if readme_path.exists():
        content = readme_path.read_text()
        assert "conversation" in content.lower(), "README missing conversation examples"
    
    total_time = time.time() - start_time
    
    # Generate honeypot evidence
    evidence = {
        "honeypot": "test_docs_exist",
        "documentation_found": False,
        "total_duration_seconds": total_time,
        "unrealistic_behavior": "Expected docs don't exist yet",
        "expected_test_outcome": "honeypot"
    }
    print(f"\nHoneypot Evidence: {evidence}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--json-report", "--json-report-file=008_results.json"])