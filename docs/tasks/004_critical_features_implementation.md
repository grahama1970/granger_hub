# Task 004: Critical Features Implementation for Claude Module Communicator

## Overview
This task addresses critical missing functionality identified through analysis of 11 interconnected projects. The goal is to enable seamless communication between all projects by implementing protocol adapters, binary data handling, and event-driven patterns.

## Context
Analysis revealed that projects use diverse communication methods:
- **MCP Protocol**: 5 projects (arxiv-mcp-server, mcp-screenshot, etc.)
- **CLI with JSON**: 8 projects (marker, youtube_transcripts, etc.)
- **REST APIs**: 3 projects (claude_max_proxy, sparta, arangodb)
- **Direct Python**: 4 projects (unsloth_wip, marker-ground-truth, etc.)

## Critical Features to Implement

### 1. Protocol Adapter Framework

#### 1.1 Base Protocol Adapter
```python
# src/claude_coms/core/adapters/base_adapter.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ProtocolAdapter(ABC):
    """Base class for protocol adapters."""
    
    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message using the protocol."""
        pass
    
    @abstractmethod
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive a message from the protocol."""
        pass
    
    @abstractmethod
    async def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to the service."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the service."""
        pass
```

#### 1.2 MCP Adapter
- Integrate with fastmcp for MCP protocol support
- Handle tool registration and invocation
- Support streaming responses

#### 1.3 CLI Adapter
- Execute CLI commands with subprocess
- Parse JSON output
- Handle stderr and exit codes
- Support interactive CLI sessions

#### 1.4 REST Adapter
- HTTP client with retry logic
- Authentication support (API keys, OAuth)
- Request/response transformation

### 2. Binary Data Handling

#### 2.1 Enhanced Message Types
```python
# src/claude_coms/core/messages/binary_message.py
from typing import Optional, Union
import mimetypes

class BinaryMessage(Message):
    """Message type for binary data."""
    
    def __init__(
        self,
        data: Union[bytes, bytearray],
        mime_type: Optional[str] = None,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.data = data
        self.mime_type = mime_type or self._detect_mime_type(filename)
        self.filename = filename
        self.metadata = metadata or {}
```

#### 2.2 File Reference System
- Support large files via references
- Temporary file management
- Cleanup policies
- Streaming support for large files

#### 2.3 Content Type Handlers
- Image processing (PNG, JPEG, etc.)
- PDF handling
- Audio/video metadata extraction
- Automatic format conversion

### 3. Event-Driven Communication

#### 3.1 Event Bus Implementation
```python
# src/claude_coms/core/events/event_bus.py
from typing import Dict, List, Callable, Any
import asyncio

class EventBus:
    """Central event distribution system."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
    
    async def publish(self, event_type: str, data: Any) -> None:
        """Publish an event to all subscribers."""
        pass
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type."""
        pass
```

#### 3.2 Event Types
- Module lifecycle events (started, stopped, error)
- Data processing events (received, processed, completed)
- System events (discovery, health_check, configuration_change)

#### 3.3 WebSocket Support
- Real-time event streaming
- Bidirectional communication
- Connection management
- Heartbeat/keepalive

## Implementation Order

### Phase 1: Protocol Adapters (Week 1-2)
1. Implement base ProtocolAdapter class
2. Create CLIAdapter for subprocess communication
3. Create RESTAdapter for HTTP APIs
4. Create MCPAdapter for MCP protocol
5. Add adapter registry and factory

### Phase 2: Binary Data (Week 3)
1. Implement BinaryMessage class
2. Add file reference system
3. Create content type handlers
4. Update existing modules to support binary data
5. Add streaming support

### Phase 3: Event System (Week 4)
1. Implement EventBus
2. Define standard event types
3. Add WebSocket support
4. Create event-driven module base class
5. Add event persistence and replay

## Testing Strategy

### Unit Tests
- Protocol adapter mocking
- Binary data serialization
- Event bus pub/sub
- Message transformation

### Integration Tests
- Cross-protocol communication
- Large file handling
- Event propagation
- Error scenarios

### End-to-End Tests
- SPARTA → Marker → ArangoDB pipeline
- MCP server communication
- Multi-protocol orchestration

## Success Criteria
1. All 11 projects can communicate through claude-module-communicator
2. Binary files (PDFs, images) can be passed between modules
3. Real-time events propagate to all interested modules
4. Protocol differences are transparent to module developers
5. System remains responsive under load

## Module Integration Examples

### Example 1: SPARTA → Marker Pipeline
```python
# SPARTA produces text, Marker needs file path
async def sparta_to_marker_pipeline():
    # SPARTA outputs via CLI
    sparta_adapter = CLIAdapter(command="sparta-cli extract")
    text_result = await sparta_adapter.send({"url": "https://example.com"})
    
    # Save to temp file for Marker
    temp_file = await file_manager.create_temp(text_result["content"])
    
    # Marker processes via CLI
    marker_adapter = CLIAdapter(command="marker")
    pdf_result = await marker_adapter.send({"input": temp_file})
    
    # Result is binary PDF
    return BinaryMessage(
        data=pdf_result["pdf_data"],
        mime_type="application/pdf"
    )
```

### Example 2: Real-time Progress Updates
```python
# Long-running operation with progress
async def process_with_progress(data):
    event_bus = EventBus()
    
    # Subscriber receives real-time updates
    event_bus.subscribe("progress", lambda e: print(f"Progress: {e['percent']}%"))
    
    # Module publishes progress events
    for i in range(100):
        await event_bus.publish("progress", {"percent": i, "step": "Processing"})
        await asyncio.sleep(0.1)
```

## Dependencies
- fastmcp (for MCP protocol)
- aiohttp (for REST adapter)
- websockets (for WebSocket support)
- python-magic (for MIME type detection)
- aiofiles (for async file operations)

## Risks and Mitigations
1. **Risk**: Protocol incompatibilities
   - **Mitigation**: Comprehensive adapter testing, fallback mechanisms

2. **Risk**: Memory issues with large binaries
   - **Mitigation**: Streaming support, file references, cleanup policies

3. **Risk**: Event storm overwhelming system
   - **Mitigation**: Rate limiting, event batching, backpressure

## Next Steps
1. Review and approve implementation plan
2. Set up development branches
3. Begin Phase 1 implementation
4. Schedule weekly progress reviews