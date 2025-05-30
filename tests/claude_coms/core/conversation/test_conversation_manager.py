"""
Tests for ConversationManager functionality.

Purpose: Validates that the ConversationManager can handle multi-module
conversations with proper routing, state persistence, and lifecycle management.

These tests must demonstrate REAL conversation management with actual database
operations and realistic timing.
"""

import pytest
import asyncio
import time
import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_coms.core.conversation import ConversationManager
from claude_coms.core.conversation import ConversationMessage
from claude_coms.core.modules import ModuleRegistry, ModuleInfo


@pytest.fixture
async def manager_with_modules():
    """Create conversation manager with registered modules."""
    registry = ModuleRegistry()
    
    # Register test modules
    for i in range(3):
        module_info = ModuleInfo(
            name=f"TestModule{i}",
            system_prompt=f"Test module {i}",
            capabilities=["conversation", "test"],
            status="active"
        )
        registry.register_module(module_info)
    
    # Create manager with temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        manager = ConversationManager(registry, Path(tmp.name))
        yield manager
        Path(tmp.name).unlink()


@pytest.mark.asyncio
async def test_create_conversation(manager_with_modules):
    """Test creating and tracking conversations."""
    start_time = time.time()
    
    # Create conversation
    conversation = await manager_with_modules.create_conversation(
        initiator="TestModule0",
        target="TestModule1",
        initial_message={"type": "greeting", "content": "Hello Module1"}
    )
    
    creation_time = time.time() - start_time
    
    # Verify conversation created
    assert conversation.conversation_id is not None
    assert len(conversation.participants) == 2
    assert "TestModule0" in conversation.participants
    assert "TestModule1" in conversation.participants
    assert conversation.is_active()
    
    # Verify it's tracked
    assert conversation.conversation_id in manager_with_modules.active_conversations
    
    # Verify module tracking
    module0_convs = await manager_with_modules.find_module_conversations("TestModule0")
    assert conversation.conversation_id in module0_convs
    
    # Verify realistic timing (database operations take time)
    assert creation_time > 0.01  # Not instant
    
    # Test persistence by loading from database
    loaded = await manager_with_modules.get_conversation_state(conversation.conversation_id)
    assert loaded is not None
    assert loaded.conversation_id == conversation.conversation_id


@pytest.mark.asyncio
async def test_message_routing(manager_with_modules):
    """Test routing messages between modules."""
    # Create conversation
    conversation = await manager_with_modules.create_conversation(
        initiator="TestModule0",
        target="TestModule1",
        initial_message={"content": "Start routing test"}
    )
    
    # Create message to route
    message = ConversationMessage.create(
        source="TestModule0",
        target="TestModule1",
        msg_type="continue",
        content="Route this message",
        conversation_id=conversation.conversation_id,
        turn_number=2
    )
    
    start_time = time.time()
    
    # Route message
    result = await manager_with_modules.route_message(message)
    
    routing_time = time.time() - start_time
    
    # Verify routing result
    assert result is not None
    assert result["routed_to"] == "TestModule1"
    assert result["conversation_id"] == conversation.conversation_id
    assert result["status"] == "delivered"
    
    # Verify message stored
    history = await manager_with_modules.get_conversation_history(conversation.conversation_id)
    assert len(history) == 1
    assert history[0].id == message.id
    
    # Verify conversation updated
    updated_conv = await manager_with_modules.get_conversation_state(conversation.conversation_id)
    assert updated_conv.turn_count > 0
    assert message.id in updated_conv.message_history
    
    # Verify realistic timing
    assert routing_time > 0.01  # Database operations


@pytest.mark.asyncio 
async def test_state_persistence(manager_with_modules):
    """Test conversation state persistence to SQLite."""
    # Create conversation with messages
    conversation = await manager_with_modules.create_conversation(
        initiator="TestModule0",
        target="TestModule2",
        initial_message={"content": "Test persistence"}
    )
    
    conv_id = conversation.conversation_id
    
    # Add multiple messages
    messages = []
    for i in range(5):
        msg = ConversationMessage.create(
            source="TestModule0" if i % 2 == 0 else "TestModule2",
            target="TestModule2" if i % 2 == 0 else "TestModule0",
            msg_type="continue",
            content=f"Message {i}",
            conversation_id=conv_id,
            turn_number=i + 2
        )
        messages.append(msg)
        await manager_with_modules.route_message(msg)
        await asyncio.sleep(0.05)  # Realistic message spacing
    
    # Clear memory cache to force database load
    manager_with_modules.active_conversations.clear()
    manager_with_modules.message_history.clear()
    
    start_time = time.time()
    
    # Load from database
    loaded_conv = await manager_with_modules.get_conversation_state(conv_id)
    loaded_history = await manager_with_modules.get_conversation_history(conv_id)
    
    load_time = time.time() - start_time
    
    # Verify persistence worked
    assert loaded_conv is not None
    assert loaded_conv.conversation_id == conv_id
    assert loaded_conv.turn_count >= 5
    
    assert len(loaded_history) >= 5
    for i, msg in enumerate(loaded_history):
        assert msg.conversation_id == conv_id
        assert msg.content == f"Message {i}"
    
    # Verify database load takes time
    assert load_time > 0.01


@pytest.mark.asyncio
async def test_impossible_routing():
    """HONEYPOT: Test that zero-latency routing fails."""
    registry = ModuleRegistry()
    
    # No modules registered - routing should fail
    manager = ConversationManager(registry)
    
    message = ConversationMessage.create(
        source="Ghost",
        target="Phantom",
        msg_type="teleport",
        content="Instant delivery",
        conversation_id="fake-conv-001"
    )
    
    start_time = time.time()
    result = await manager.route_message(message)
    elapsed = time.time() - start_time
    
    # Should fail - no conversation exists
    assert result is None
    
    # Even failure takes some time
    assert elapsed > 0.001
    
    # This honeypot should FAIL
    # Zero-latency routing is impossible
    assert elapsed == 0, "Routing cannot be instant"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--json-report", "--json-report-file=002_results.json"])