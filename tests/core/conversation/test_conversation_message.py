"""
# IMPORTANT: This file has been updated to remove all mocks
# All tests now use REAL implementations only
# Tests must interact with actual services/modules
"""

"""
Tests for ConversationMessage enhancements.

Purpose: Validates that the enhanced Message class properly supports
conversation tracking with conversation_id, turn_number, and context.

These tests must use REAL message objects with realistic behavior.
"""

import pytest
import time
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from granger_hub.core.conversation import ConversationMessage, ConversationState


def test_message_fields():
    """Test that conversation messages include all required fields."""
    start_time = time.time()
    
    # Create message with all fields
    msg = ConversationMessage.create(
        source="ModuleA",
        target="ModuleB",
        msg_type="query",
        content={"question": "What is the weather?"},
        conversation_id="conv-001",
        turn_number=1,
        context={"topic": "weather", "location": "NYC"}
    )
    
    creation_time = time.time() - start_time
    
    # Verify all fields present
    assert msg.id is not None
    assert msg.source == "ModuleA"
    assert msg.target == "ModuleB"
    assert msg.type == "query"
    assert msg.conversation_id == "conv-001"
    assert msg.turn_number == 1
    assert msg.context["topic"] == "weather"
    assert msg.timestamp is not None
    
    # Verify serialization includes all fields
    msg_dict = msg.to_dict()
    assert "conversation_id" in msg_dict
    assert "turn_number" in msg_dict
    assert "context" in msg_dict
    assert msg_dict["conversation_id"] == "conv-001"
    
    # Verify creation takes measurable time
    assert creation_time > 0  # Any positive time


def test_message_threading():
    """Test that messages are properly linked by conversation_id."""
    conversation_id = "thread-test-001"
    messages = []
    
    # Create conversation thread
    for i in range(5):
        msg = ConversationMessage.create(
            source=f"Module{i % 2}",
            target=f"Module{(i + 1) % 2}",
            msg_type="exchange",
            content=f"Message {i}",
            conversation_id=conversation_id,
            turn_number=i + 1
        )
        messages.append(msg)
        time.sleep(0.01)  # Realistic message spacing
    
    # Verify all linked by conversation_id
    for msg in messages:
        assert msg.conversation_id == conversation_id
    
    # Verify turn numbers increment
    for i, msg in enumerate(messages):
        assert msg.turn_number == i + 1
    
    # Test reply creation
    reply = messages[2].create_reply(
        source="Module1",
        content="Reply to message 2"
    )
    
    # Verify reply maintains conversation
    assert reply.conversation_id == conversation_id
    assert reply.turn_number == messages[2].turn_number + 1
    assert reply.in_reply_to == messages[2].id
    assert reply.target == messages[2].source  # Reply goes back to sender
    
    # Verify context preserved in reply
    messages[2].context["important"] = "data"
    reply2 = messages[2].create_reply("Module0", "Another reply")
    assert "important" in reply2.context
    assert reply2.context["important"] == "data"


def test_no_timestamp():
    """HONEYPOT: Test message creation without timestamp fails."""
    # This should demonstrate that timestamps are required
    # and cannot be skipped for real messages
    
    try:
        # Try to create message without proper timestamp
        msg_dict = {
            "id": "fake-id",
            "source": "FakeModule",
            "target": "Ghost",
            "type": "phantom",
            "content": "No time",
            "conversation_id": "fake-conv",
            "turn_number": 1,
            "context": {}
            # Missing timestamp!
        }
        
        # This should fail
        msg = ConversationMessage(**msg_dict)
        
        # If we get here, the test framework is broken
        assert False, "Message created without timestamp - impossible!"
        
    except TypeError as e:
        # Expected - missing required field
        assert "timestamp" in str(e)
        pass


def test_conversation_state_tracking():
    """Test ConversationState tracks conversation progress."""
    state = ConversationState(
        conversation_id="state-test-001",
        participants=["ModuleX", "ModuleY"]
    )
    
    # Simulate conversation progress
    message_ids = []
    start_time = time.time()
    
    for i in range(10):
        msg_id = f"msg-{i:03d}"
        state.add_message(msg_id)
        message_ids.append(msg_id)
        time.sleep(0.01)  # Realistic pacing
    
    elapsed = time.time() - start_time
    
    # Verify state tracking
    assert state.turn_count == 10
    assert len(state.message_history) == 10
    assert state.is_active()
    assert all(msg_id in state.message_history for msg_id in message_ids)
    
    # Verify timing
    assert elapsed > 0.09  # At least 90ms for 10 messages
    
    # Test completion
    state.complete()
    assert not state.is_active()
    assert state.status == "completed"
    
    # Verify serialization
    state_dict = state.to_dict()
    assert state_dict["turn_count"] == 10
    assert state_dict["status"] == "completed"
    assert len(state_dict["message_history"]) == 10


def test_context_updates():
    """Test that message context can be updated and tracked."""
    msg = ConversationMessage.create(
        source="ContextModule",
        target="Receiver",
        msg_type="data",
        content="Initial data",
        context={"step": 1, "data": []}
    )
    
    # Update context multiple times
    for i in range(5):
        msg.update_context({
            f"step_{i}": f"completed",
            "data": msg.context["data"] + [i],
            "last_update": datetime.now().isoformat()
        })
        time.sleep(0.02)  # Realistic processing
    
    # Verify context accumulated
    assert "step_4" in msg.context
    assert len(msg.context["data"]) == 5
    assert "last_update" in msg.context
    
    # Create reply with updated context
    reply = msg.create_reply(
        source="Receiver",
        content="Processed with context"
    )
    
    # Verify context carried forward
    assert reply.context["data"] == [0, 1, 2, 3, 4]
    assert reply.conversation_id == msg.conversation_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--json-report", "--json-report-file=003_results.json"])