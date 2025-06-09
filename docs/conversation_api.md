# Multi-Turn Conversation API Documentation

## Overview

The Granger Hub now supports multi-turn conversations between modules, enabling complex workflows, iterative processing, and context-aware communication. This document describes the conversation API and its usage.

## Core Components

### 1. ConversationManager

The `ConversationManager` handles conversation lifecycle, routing, and persistence.

```python
from claude_coms.core.conversation import ConversationManager

manager = ConversationManager(
    registry=module_registry,
    db_path=Path("conversations.db"),
    conversation_timeout=300  # 5 minutes
)
```

### 2. ConversationMessage

Messages in conversations carry context and maintain conversation state.

```python
from claude_coms.core.conversation import ConversationMessage

message = ConversationMessage.create(
    source="ModuleA",
    target="ModuleB", 
    msg_type="process",
    content="Process this data",
    data={"values": [1, 2, 3]},
    conversation_id="conv_123",
    turn_number=2
)
```

### 3. ConversationModule

Base class for modules that support conversations.

```python
from claude_coms.core.conversation import ConversationModule

class MyModule(ConversationModule):
    def __init__(self):
        super().__init__(
            name="MyModule",
            system_prompt="Process data with context",
            capabilities=["processing", "conversation"]
        )
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Access conversation history
        conv_id = data.get("conversation_id")
        if conv_id and conv_id in self.conversation_history:
            # Use previous context
            history = self.conversation_history[conv_id]
        
        # Process with context awareness
        return {"result": "processed", "context_used": True}
```

## Starting Conversations

### Using ModuleCommunicator

```python
from claude_coms.core.module_communicator import ModuleCommunicator

comm = ModuleCommunicator()

# Start a conversation
result = await comm.start_conversation(
    initiator="DataProcessor",
    target="DataAnalyzer",
    initial_message={"task": "analyze", "data": [1, 2, 3]},
    conversation_type="analysis"
)

conversation_id = result["conversation_id"]
```

### Direct ConversationManager Usage

```python
# Create conversation
conversation = await manager.create_conversation(
    initiator="ModuleA",
    target="ModuleB",
    initial_message={"type": "task", "content": {...}}
)

# Route messages
response = await manager.route_message(message)
```

## Conversation Lifecycle

### 1. Initiation
- Module A initiates conversation with Module B
- Unique conversation_id generated
- Initial context established

### 2. Message Exchange
- Messages routed through ConversationManager
- Each message increments turn_number
- Context preserved across turns

### 3. Completion
- Conversations can be completed explicitly
- Automatic timeout after inactivity
- State persisted to database

## Persistence

### SQLite Storage

Conversations are persisted to SQLite with two main tables:

1. **conversations**: Stores conversation metadata
   - conversation_id (PRIMARY KEY)
   - participants (JSON)
   - started_at, last_activity
   - status, turn_count
   - context (JSON)

2. **conversation_messages**: Stores individual messages
   - message_id (PRIMARY KEY)
   - conversation_id (FOREIGN KEY)
   - turn_number, source, target
   - content, timestamp

### ArangoDB Integration (Optional)

For graph-based analytics, use ArangoConversationStore:

```python
from claude_coms.core.storage.arango_conversation import ArangoConversationStore

store = ArangoConversationStore(
    host="localhost",
    port=8529,
    database="conversations"
)
await store.initialize()

# Save conversation
conv_id = await store.start_conversation(
    participants=["ModuleA", "ModuleB"],
    topic="Data Processing"
)
```

## Analytics

### Get Conversation Analytics

```python
analytics = await comm.get_conversation_analytics(
    start_date=datetime.now() - timedelta(days=7),
    end_date=datetime.now()
)

# Returns:
{
    "total_conversations": 42,
    "completed": 35,
    "failed": 2,
    "active": 5,
    "average_turns": 4.7,
    "average_duration_seconds": 125.3,
    "module_statistics": {
        "DataProcessor": {"initiated": 20, "participated": 25},
        "DataAnalyzer": {"initiated": 15, "participated": 30}
    }
}
```

## Advanced Features

### 1. Schema Negotiation

Modules can negotiate data schemas iteratively:

```python
# MarkerModule extracts schema from PDF
schema = await marker.extract_schema(pdf_path)

# ArangoModule validates and requests refinements
validation = await arango.validate_schema(schema)
if not validation["valid"]:
    refined = await marker.refine_schema(
        schema, 
        validation["feedback"]
    )
```

### 2. Concurrent Conversations

Modules can participate in multiple conversations:

```python
# Module A talks to B and C simultaneously
conv1 = await comm.start_conversation("A", "B", {...})
conv2 = await comm.start_conversation("A", "C", {...})

# Each conversation maintains separate context
```

### 3. Conversation Handoff

Conversations can be transferred between modules:

```python
# Module B hands off conversation to Module C
await manager.transfer_conversation(
    conversation_id,
    from_module="B",
    to_module="C",
    handoff_context={...}
)
```

## Best Practices

1. **Always check conversation_id**: Modules should check if a message is part of a conversation
2. **Maintain context**: Use conversation history to provide context-aware responses
3. **Handle timeouts**: Implement cleanup for timed-out conversations
4. **Limit conversation length**: Prevent infinite conversation loops
5. **Log important turns**: Use structured logging for debugging

## Error Handling

```python
try:
    result = await comm.start_conversation(...)
except ConversationError as e:
    logger.error(f"Conversation failed: {e}")
    # Handle appropriately
```

## Examples

See `examples/conversation_workflows.py` for complete examples including:
- Data processing pipeline with multiple stages
- Iterative refinement workflows
- Multi-module collaboration patterns