# Claude Module Communicator

A Python framework for enabling communication between independent modules with schema negotiation, compatibility verification, and progress tracking.

## Overview

Claude Module Communicator provides a robust infrastructure for modules to communicate with each other through:
- **Schema Negotiation** - Modules can negotiate data schemas to ensure compatibility
- **Pipeline Validation** - Verify that modules in a pipeline can communicate properly
- **Progress Tracking** - Real-time monitoring of module communication sessions
- **Compatibility Verification** - Ensure modules can exchange data before runtime

## Features

### 🔄 Schema Negotiation
Modules can dynamically negotiate schemas to establish a common data format for communication.

### ✅ Compatibility Verification
Validate that output schemas from one module match input schemas of the next module in a pipeline.

### 📊 Progress Tracking
- Real-time session monitoring
- SQLite-based progress persistence
- Detailed operation logging
- Performance metrics tracking

### 🔗 Pipeline Management
- Define multi-module pipelines
- Validate end-to-end compatibility
- Monitor pipeline execution

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/grahama1970/claude-module-communicator.git@master

# Or clone and install locally
git clone https://github.com/grahama1970/claude-module-communicator.git
cd claude-module-communicator
pip install -e .
```

## Usage

### Quick Start with CLI

The `claude-comm` CLI provides easy access to module communication:

```bash
# List all messages
claude-comm list

# List messages for a specific module
claude-comm list --target marker

# Show full message details
claude-comm show 1

# List progress entries
claude-comm progress

# Send a message
claude-comm send sparta marker "Hello from SPARTA"
```

### Python API

```python
from claude_module_communicator import ModuleCommunicator

# Initialize communicator
comm = ModuleCommunicator("my_module")

# Send a message
msg_id = comm.send_message("source", "target", {
    "type": "request",
    "data": "some data"
})

# Get messages
messages = comm.get_messages("my_module")

# Track progress
comm.track_progress("task_name", 50, 100)

# Negotiate schema
schema = comm.negotiate_schema("target_module", sample_data)
```

### Advanced CLI Commands

#### Schema Negotiation
```bash
# Negotiate schema between two modules
python -m claude_coms.cli negotiate-schema config.json
```

Example config.json:
```json
{
    "source_module": "data_producer",
    "target_module": "data_processor",
    "schema": {
        "input": {
            "type": "object",
            "properties": {
                "data": {"type": "array"},
                "timestamp": {"type": "string"}
            }
        },
        "output": {
            "type": "object",
            "properties": {
                "processed_data": {"type": "array"},
                "metadata": {"type": "object"}
            }
        }
    }
}
```

#### Pipeline Validation
```bash
# Validate a pipeline configuration
python -m claude_coms.cli validate-pipeline pipeline.json
```

Example pipeline.json:
```json
{
    "pipeline_name": "data_processing_pipeline",
    "modules": [
        {
            "name": "ingestion_module",
            "version": "1.0.0",
            "output_schema": {
                "type": "object",
                "properties": {
                    "raw_data": {"type": "array"}
                }
            }
        },
        {
            "name": "transformation_module",
            "version": "1.0.0",
            "input_schema": {
                "type": "object",
                "properties": {
                    "raw_data": {"type": "array"}
                }
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "transformed_data": {"type": "array"}
                }
            }
        }
    ]
}
```

#### Monitor Communication
```bash
# Monitor a communication session
python -m claude_coms.cli monitor-session session_config.json --duration 60
```

### Python API

```python
import asyncio
from claude_coms.core.progress_utils import (
    init_database,
    update_session_stats,
    track_module_communication
)

async def main():
    # Initialize progress tracking database
    await init_database("./progress.db")
    
    # Start a communication session
    session_id = "session_001"
    await update_session_stats(
        db_path="./progress.db",
        session_id=session_id,
        modules_active=["module_a", "module_b"],
        start_time=datetime.now().isoformat()
    )
    
    # Track module communication
    await track_module_communication(
        db_path="./progress.db",
        session_id=session_id,
        source_module="module_a",
        target_module="module_b",
        message_type="data_transfer",
        status="SUCCESS",
        metrics={"records": 1000, "duration_ms": 150}
    )

asyncio.run(main())
```

## Architecture

### Core Components

1. **CLI Module** (`src/cli/`)
   - Command-line interface for module communication operations
   - Schema negotiation commands
   - Pipeline validation commands
   - Session monitoring commands

2. **Core Module** (`src/core/`)
   - `progress_tracker.py` - Async progress tracking functionality
   - `progress_utils.py` - Database operations and utility functions

3. **MCP Module** (`src/mcp/`)
   - Ready for Model Context Protocol (MCP) server implementation
   - Will enable modules to communicate via MCP protocol

### Database Schema

The framework uses SQLite for progress tracking with three main tables:
- `session_stats` - Overall session statistics
- `file_operations` - Detailed operation logs
- `module_communications` - Module-to-module communication records

## Testing

The project includes comprehensive tests with real data validation:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Development

### Project Structure
```
claude-module-communicator/
├── src/
│   ├── claude_coms/
│   │   ├── cli/          # CLI commands
│   │   ├── core/         # Core functionality
│   │   └── mcp/          # MCP server (future)
│   ├── cli/              # Legacy CLI location
│   ├── core/             # Legacy core location
│   └── mcp/              # Legacy MCP location
├── tests/
│   ├── cli/              # CLI tests
│   ├── core/             # Core tests
│   ├── claude_coms/      # Module tests
│   └── mcp/              # MCP tests
├── docs/
│   ├── tasks/            # Task documentation
│   └── reports/          # Test reports
└── pyproject.toml        # Project configuration
```

### Contributing

1. Follow the coding standards in `CLAUDE.md`
2. All tests must use real data (no mocking)
3. Maintain test coverage above 80%
4. Use type hints for all functions

## License

MIT License - see LICENSE file for details

## Roadmap

- [ ] Complete MCP server implementation
- [ ] Add WebSocket support for real-time communication
- [ ] Implement authentication for secure module communication
- [ ] Add support for binary data transfer
- [ ] Create module registry for dynamic discovery
- [ ] Add distributed tracing support