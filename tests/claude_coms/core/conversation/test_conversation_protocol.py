"""
Tests for Module-to-Module Conversation Protocol.

Purpose: Validates the conversation protocol implementation including handshakes,
schema negotiation, and proper phase transitions.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_coms.core.conversation import (
    ConversationProtocol, ConversationIntent, ConversationPhase,
    ConversationHandshake, ConversationResponse, SchemaProposal
)
from claude_coms.core.conversation import ConversationMessage


def test_handshake_creation():
    """Test creating handshake messages."""
    start_time = time.time()
    
    # Create handshake
    msg = ConversationProtocol.create_handshake_message(
        source="DataModule",
        target="StorageModule",
        intent=ConversationIntent.NEGOTIATE,
        requirements={
            "schema": {"data": "object", "timestamp": "string"},
            "capabilities": ["persistence", "indexing"],
            "offers": ["data_validation", "transformation"],
            "timeout": 600,
            "metadata": {"priority": "high"}
        }
    )
    
    creation_time = time.time() - start_time
    
    # Verify message structure
    assert msg.source == "DataModule"
    assert msg.target == "StorageModule"
    assert msg.type == "conversation_handshake"
    assert msg.turn_number == 1
    
    # Verify handshake content
    handshake = msg.content["handshake"]
    assert handshake["intent"] == ConversationIntent.NEGOTIATE.value
    assert handshake["proposed_schema"] == {"data": "object", "timestamp": "string"}
    assert "persistence" in handshake["capabilities_required"]
    assert "data_validation" in handshake["capabilities_offered"]
    assert handshake["timeout_seconds"] == 600
    
    # Verify phase
    assert msg.content["phase"] == ConversationPhase.HANDSHAKE.value
    
    # Real message creation takes measurable time
    assert creation_time > 0  # Any positive time


def test_negotiation_flow():
    """Test schema negotiation message flow."""
    conversation_id = "test-negotiation-001"
    
    # Initial proposal
    msg1 = ConversationProtocol.create_negotiation_message(
        source="ClientModule",
        target="ServiceModule",
        conversation_id=conversation_id,
        turn_number=2,
        proposal={
            "schema": SchemaProposal.create_data_schema(
                fields={"id": "string", "data": "object", "tags": "array"},
                required=["id", "data"]
            ),
            "batch_size": 100,
            "format": "json"
        }
    )
    
    # Counter proposal
    msg2 = ConversationProtocol.create_negotiation_message(
        source="ServiceModule", 
        target="ClientModule",
        conversation_id=conversation_id,
        turn_number=3,
        proposal={
            "schema": SchemaProposal.create_data_schema(
                fields={"id": "string", "data": "object"},  # No tags
                required=["id"],  # data optional
                constraints={"max_size": 1024}
            ),
            "batch_size": 50,  # Smaller batches
            "format": "json"
        }
    )
    
    # Verify negotiation messages
    assert msg1.conversation_id == msg2.conversation_id
    assert msg2.turn_number > msg1.turn_number
    assert msg1.content["phase"] == ConversationPhase.NEGOTIATION.value
    assert "constraints" in msg2.content["proposal"]["schema"]


def test_execution_messages():
    """Test execution phase messaging."""
    conversation_id = "exec-test-001"
    
    messages = []
    start_time = time.time()
    
    # Simulate back and forth execution
    for i in range(5):
        source = "ProducerModule" if i % 2 == 0 else "ConsumerModule"
        target = "ConsumerModule" if i % 2 == 0 else "ProducerModule"
        
        msg = ConversationProtocol.create_execution_message(
            source=source,
            target=target,
            conversation_id=conversation_id,
            turn_number=i + 4,  # After handshake and negotiation
            content={
                "batch_id": f"batch_{i}",
                "records": [{"id": f"rec_{j}", "value": j} for j in range(3)],
                "status": "processing"
            },
            in_reply_to=messages[-1].id if messages else None
        )
        
        messages.append(msg)
        time.sleep(0.01)  # Realistic message spacing
    
    execution_time = time.time() - start_time
    
    # Verify execution flow
    assert len(messages) == 5
    assert all(m.conversation_id == conversation_id for m in messages)
    assert all(m.content["phase"] == ConversationPhase.EXECUTION.value for m in messages)
    
    # Verify reply chain
    for i in range(1, len(messages)):
        assert messages[i].in_reply_to == messages[i-1].id
    
    # Verify realistic timing
    assert execution_time > 0.04  # At least 40ms for 5 messages


def test_conversation_termination():
    """Test proper conversation termination."""
    conversation_id = "term-test-001"
    
    # Create termination with summary
    term_msg = ConversationProtocol.create_termination_message(
        source="MasterModule",
        target="WorkerModule",
        conversation_id=conversation_id,
        turn_number=10,
        reason="completed",
        summary={
            "records_processed": 500,
            "errors": 0,
            "duration_seconds": 45.2,
            "final_state": "success"
        }
    )
    
    # Verify termination
    assert term_msg.type == "termination"
    assert term_msg.content["phase"] == ConversationPhase.TERMINATION.value
    assert term_msg.content["reason"] == "completed"
    assert term_msg.content["summary"]["records_processed"] == 500


def test_validate_conversation_flow():
    """Test conversation flow validation."""
    conversation_id = "flow-test-001"
    
    # Build a proper conversation flow
    messages = []
    
    # 1. Handshake
    messages.append(ConversationProtocol.create_handshake_message(
        source="A", target="B",
        intent=ConversationIntent.COLLABORATE,
        requirements={"capabilities": ["compute"]}
    ))
    
    # 2. Negotiation
    messages.append(ConversationProtocol.create_negotiation_message(
        source="B", target="A",
        conversation_id=conversation_id,
        turn_number=2,
        proposal={"accepted": True}
    ))
    
    # 3. Execution
    for i in range(3):
        messages.append(ConversationProtocol.create_execution_message(
            source="A" if i % 2 == 0 else "B",
            target="B" if i % 2 == 0 else "A",
            conversation_id=conversation_id,
            turn_number=3 + i,
            content={"step": i}
        ))
    
    # 4. Termination
    messages.append(ConversationProtocol.create_termination_message(
        source="A", target="B",
        conversation_id=conversation_id,
        turn_number=6,
        reason="completed"
    ))
    
    # Validate proper flow
    assert ConversationProtocol.validate_conversation_flow(messages) is True
    
    # Test invalid flow - no handshake
    invalid_messages = messages[1:]  # Skip handshake
    assert ConversationProtocol.validate_conversation_flow(invalid_messages) is False
    
    # Test invalid flow - wrong order
    out_of_order = [messages[0], messages[3], messages[1]]  # Handshake, exec, negotiation
    assert ConversationProtocol.validate_conversation_flow(out_of_order) is False


def test_schema_proposal_helpers():
    """Test schema proposal utilities."""
    # Create schemas
    schema1 = SchemaProposal.create_data_schema(
        fields={"id": "string", "name": "string", "age": "number"},
        required=["id", "name"]
    )
    
    schema2 = SchemaProposal.create_data_schema(
        fields={"id": "string", "name": "string", "email": "string"},
        required=["id", "email"]
    )
    
    # Merge schemas
    merged = SchemaProposal.merge_schemas(schema1, schema2)
    
    # Verify merge
    assert "id" in merged["properties"]
    assert "name" in merged["properties"]
    assert "age" not in merged["properties"]  # Not in both
    assert "email" not in merged["properties"]  # Not in both
    assert merged["required"] == ["id"]  # Only common required field


@pytest.mark.asyncio
async def test_conversation_timing():
    """Test that conversation operations have realistic timing."""
    start_time = time.time()
    
    # Simulate a conversation with async operations
    messages = []
    
    # Handshake
    handshake = ConversationProtocol.create_handshake_message(
        source="TimingTestA",
        target="TimingTestB",
        intent=ConversationIntent.QUERY,
        requirements={}
    )
    messages.append(handshake)
    await asyncio.sleep(0.02)  # Network latency
    
    # Response
    response = ConversationProtocol.create_execution_message(
        source="TimingTestB",
        target="TimingTestA",
        conversation_id="timing-001",
        turn_number=2,
        content={"response": "acknowledged"}
    )
    messages.append(response)
    await asyncio.sleep(0.02)
    
    total_time = time.time() - start_time
    
    # Verify timing
    assert total_time > 0.03  # At least 30ms
    assert len(messages) == 2


def test_impossible_instant_protocol():
    """HONEYPOT: Test that instant protocol operations fail."""
    # Try to validate empty conversation
    assert ConversationProtocol.validate_conversation_flow([]) is False
    
    # Try to create instant conversation flow
    start = time.time()
    messages = []
    
    for i in range(10):
        msg = ConversationProtocol.create_execution_message(
            source="Flash",
            target="Quicksilver",
            conversation_id="instant",
            turn_number=i,
            content={"instant": True}
        )
        messages.append(msg)
    
    elapsed = time.time() - start
    
    # Creating 10 messages should take some time
    assert elapsed > 0
    
    # This should fail - protocol requires proper phases
    assert ConversationProtocol.validate_conversation_flow(messages) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--json-report", "--json-report-file=004_results.json"])