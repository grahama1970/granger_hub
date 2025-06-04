# CLAUDE MODULE COMMUNICATOR CONTEXT — CLAUDE.md

> **Inherits standards from global and workspace CLAUDE.md files with overrides below.**

## Project Context
**Purpose:** Inter-project communication and orchestration framework  
**Type:** Hub (Core Infrastructure)  
**Status:** Active  
**Pipeline Position:** Communication hub for all modules

## Project-Specific Overrides

### Special Dependencies
```toml
# Module Communicator specific packages
fastapi = "^0.104.0"
websockets = "^12.0"
aioredis = "^2.0.0"
pydantic = "^2.0.0"
```

### Environment Variables  
```bash
# .env additions for Module Communicator
HUB_PORT=8000
REDIS_URL=redis://localhost:6379
WEBSOCKET_TIMEOUT=30
MAX_CONCURRENT_MODULES=10
SCHEMA_VALIDATION_STRICT=true
```
### Integration Schema
```json
{
  "module_registration": {
    "module_name": "string",
    "capabilities": ["array"],
    "endpoints": {"object"},
    "schema_version": "string"
  },
  "communication_event": {
    "source_module": "string", 
    "target_module": "string",
    "event_type": "string",
    "payload": {"object"},
    "timestamp": "datetime"
  }
}
```

### Special Considerations
- **Real-time Communication:** WebSocket-based inter-module messaging
- **Schema Registry:** Maintains all module communication schemas
- **Progress Tracking:** Coordinates multi-module workflows
- **Resource Orchestration:** Manages compute and memory allocation

---

## License

MIT License — see [LICENSE](LICENSE) for details.