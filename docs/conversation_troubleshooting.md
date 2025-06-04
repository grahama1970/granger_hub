# Conversation Troubleshooting Guide

## Common Issues and Solutions

### 1. Conversation Timeout Issues

**Problem**: Conversations timing out before completion

**Symptoms**:
- Conversation status changes to "timeout"
- Messages stop being routed
- Modules report lost context

**Solutions**:
```python
# Increase timeout when creating ConversationManager
manager = ConversationManager(
    registry=registry,
    conversation_timeout=600  # 10 minutes instead of 5
)

# Or override for specific conversations
async def start_long_conversation():
    conv = await manager.create_conversation(...)
    # Custom monitoring with longer timeout
```

### 2. Message Routing Failures

**Problem**: Messages not reaching target modules

**Symptoms**:
- `route_message()` returns None
- "Target module not available" errors
- Missing messages in conversation history

**Debugging Steps**:
```python
# Check module registration
modules = registry.list_modules()
print(f"Registered modules: {[m.name for m in modules]}")

# Verify conversation exists
conv_state = await manager.get_conversation_state(conversation_id)
if not conv_state:
    print("Conversation not found!")
    
# Check conversation participants
if target not in conv_state.participants:
    print(f"{target} not in conversation participants")
```

### 3. Context Loss Between Turns

**Problem**: Modules not maintaining conversation context

**Symptoms**:
- Responses don't reference previous messages
- Repeated questions or processing
- Context-dependent features not working

**Fix in Module Implementation**:
```python
class MyModule(ConversationModule):
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        conv_id = data.get("conversation_id")
        
        # Always check for conversation context
        if conv_id and conv_id in self.conversation_history:
            history = self.conversation_history[conv_id]
            # Use history to inform processing
            last_message = history[-1] if history else None
            
        # Include conversation_id in response
        return {
            "result": "...",
            "conversation_id": conv_id,
            "context_preserved": True
        }
```

### 4. Database Connection Issues

**Problem**: SQLite database errors

**Symptoms**:
- "database is locked" errors
- Failed to persist conversation
- Missing conversation history

**Solutions**:
```python
# Use WAL mode for better concurrency
conn = sqlite3.connect(db_path)
conn.execute("PRAGMA journal_mode=WAL")

# Implement retry logic
async def persist_with_retry(conversation, max_retries=3):
    for i in range(max_retries):
        try:
            await manager._persist_conversation(conversation)
            break
        except sqlite3.OperationalError:
            if i < max_retries - 1:
                await asyncio.sleep(0.1 * (i + 1))
            else:
                raise
```

### 5. Memory Leaks in Long-Running Conversations

**Problem**: Memory usage growing with active conversations

**Symptoms**:
- Increasing memory consumption
- Slow message routing
- System performance degradation

**Prevention**:
```python
# Implement conversation cleanup
async def cleanup_old_conversations():
    for conv_id, conv in list(manager.active_conversations.items()):
        if conv.is_stale():  # Define staleness criteria
            await manager.end_conversation(conv_id)
            
# Limit message history per conversation
MAX_HISTORY_SIZE = 100
if len(self.message_history[conv_id]) > MAX_HISTORY_SIZE:
    self.message_history[conv_id] = self.message_history[conv_id][-MAX_HISTORY_SIZE:]
```

### 6. Concurrent Conversation Conflicts

**Problem**: Race conditions in concurrent conversations

**Symptoms**:
- Mixed context between conversations
- Incorrect turn numbers
- Lost messages

**Solution with Locks**:
```python
conversation_locks = {}

async def safe_route_message(message):
    conv_id = message.conversation_id
    
    # Get or create lock for conversation
    if conv_id not in conversation_locks:
        conversation_locks[conv_id] = asyncio.Lock()
        
    async with conversation_locks[conv_id]:
        return await manager.route_message(message)
```

### 7. Module Not Responding

**Problem**: Module doesn't process conversation messages

**Symptoms**:
- No response from module
- Conversation stalls
- Timeout without progress

**Debugging**:
```python
# Add logging to module
class DebugModule(ConversationModule):
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"Received data: {data}")
        
        try:
            result = await self._actual_process(data)
            logger.debug(f"Returning result: {result}")
            return result
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            raise
```

### 8. Test Failures in CI/CD

**Problem**: Conversation tests failing in CI but passing locally

**Common Causes**:
- Timing issues
- Database permissions
- Missing environment variables

**Robust Test Pattern**:
```python
@pytest.mark.asyncio
async def test_conversation_with_retry():
    # Use longer timeouts in CI
    timeout = 10 if os.getenv("CI") else 5
    
    # Ensure clean state
    if Path("test_conversations.db").exists():
        Path("test_conversations.db").unlink()
        
    # Create test with proper cleanup
    try:
        comm = ModuleCommunicator()
        # ... run test
    finally:
        await comm.shutdown()
```

## Performance Optimization

### 1. Batch Message Processing
```python
# Process multiple messages in one go
messages = await manager.get_conversation_messages(conv_id, limit=10)
results = await asyncio.gather(*[
    module.process(msg) for msg in messages
])
```

### 2. Conversation Caching
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_conversation_state(conv_id: str):
    return manager.get_conversation_state(conv_id)
```

### 3. Async Context Managers
```python
class ConversationContext:
    async def __aenter__(self):
        self.conv = await manager.create_conversation(...)
        return self.conv
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await manager.end_conversation(self.conv.conversation_id)
        
async with ConversationContext() as conv:
    # Use conversation
    pass  # Automatically cleaned up
```

## Monitoring and Debugging

### Enable Debug Logging
```python
import logging
logging.getLogger("claude_coms.conversation").setLevel(logging.DEBUG)
```

### Conversation Health Check
```python
async def check_conversation_health():
    issues = []
    
    # Check for stale conversations
    for conv_id, conv in manager.active_conversations.items():
        last_activity = datetime.fromisoformat(conv.last_activity)
        if (datetime.now() - last_activity).seconds > 300:
            issues.append(f"Stale conversation: {conv_id}")
            
    # Check database connectivity
    try:
        await manager._persist_conversation(test_conv)
    except Exception as e:
        issues.append(f"Database issue: {e}")
        
    return issues
```

## Getting Help

1. Check logs: Look for ERROR and WARNING level messages
2. Enable debug mode: Set log level to DEBUG
3. Use conversation analytics to identify patterns
4. Check the examples directory for working code
5. Submit issues with:
   - Error messages
   - Relevant code snippets
   - Conversation IDs and timestamps
   - Module configurations