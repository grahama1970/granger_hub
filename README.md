# Claude Module Communicator

A powerful Python framework for enabling communication between independent modules with schema negotiation, compatibility verification, progress tracking, graph database integration, and seamless access to external LLMs including Claude, Gemini, and GPT models.

## 🚀 Overview

Claude Module Communicator provides a robust infrastructure for modules to communicate with each other through:
- **Schema Negotiation** - Modules can negotiate data schemas to ensure compatibility
- **Pipeline Validation** - Verify that modules in a pipeline can communicate properly
- **Progress Tracking** - Real-time monitoring of module communication sessions
- **Graph Database Integration** - ArangoDB support for complex relationship modeling
- **External LLM Access** - Easy integration with Claude, Gemini, GPT-4, and more
- **MCP Server Support** - Model Context Protocol integration for Claude Desktop
- **Bidirectional Communication** - Claude instances can both give AND receive instructions

## ✨ Key Features

### 🤖 External LLM Integration
- **Multi-Model Support**: Access Claude, Gemini, GPT-4, and other models through a unified interface
- **Claude-to-Claude Communication**: Enable dialogue between Claude instances
- **Intelligent Routing**: Automatically select the best model for each task
- **Model Comparison**: Get perspectives from multiple models simultaneously

### 📸 Screenshot & Browser Automation
- **Screen Capture**: Take screenshots of full screen or specific regions
- **Web Screenshots**: Capture web pages with dynamic content support
- **AI-Powered Description**: Automatically describe screenshots using AI
- **Browser Automation**: Navigate, click, fill forms, and interact with web pages
- **Visual Verification**: Analyze visualizations with expert modes

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

### 🕸️ Graph Database Integration
- ArangoDB backend for complex relationships
- Graph traversal and analysis
- Module dependency tracking
- Knowledge gap detection

### 🎯 Hybrid Query Interface
- Natural language queries: "Find modules that support batch processing"
- Slash commands: `/arango-find modules with capability:batch_processing`
- Direct AQL: `AQL: FOR m IN modules RETURN m`
- Progressive complexity - start simple, go deeper when needed

### 🖥️ MCP Server Integration
- Full Model Context Protocol support
- WebSocket and SSE communication
- Claude Desktop integration
- Real-time module updates

### 🧠 Reinforcement Learning (RL) Integration
- **Ollama-Powered Optimization**: Uses local LLMs for immediate route and schema optimization
- **DeepRetrieval-Style Rewards**: Tiered reward system that incentivizes performance
- **Episode Collection**: Learn from real communication patterns
- **Auto Model Selection**: Automatically selects best available Ollama model
- **Fallback Strategies**: Intelligent defaults when LLM optimization fails

## 📦 Installation

```bash
# Install from GitHub
pip install git+https://github.com/grahama1970/claude-module-communicator.git@master

# Or clone and install locally
git clone https://github.com/grahama1970/claude-module-communicator.git
cd claude-module-communicator
pip install -e .
```

### External LLM Setup
The project includes `claude_max_proxy` for LLM access:
```bash
# Set API keys for external models
export ANTHROPIC_API_KEY="your-claude-api-key"
export GEMINI_API_KEY="your-gemini-api-key" 
export OPENAI_API_KEY="your-openai-api-key"
```

### Ollama Setup (for RL optimization)
```bash
# Install and start Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve

# Pull recommended models (in order of preference)
ollama pull codellama:latest      # Good for code/schema tasks
ollama pull qwen2.5:3b-instruct   # Fast general purpose
ollama pull phi3:mini             # Efficient fallback
```

## 🔧 Usage

### Quick Start with ModuleCommunicator

```python
from claude_module_communicator import ModuleCommunicator
from claude_coms.example_modules import DataProducerModule, DataProcessorModule

# Initialize communicator
comm = ModuleCommunicator()

# Register modules
producer = DataProducerModule(comm.registry)
processor = DataProcessorModule(comm.registry)

comm.register_module("producer", producer)
comm.register_module("processor", processor)

# Send messages between modules
result = await comm.send_message(
    target="producer",
    action="process",
    data={"data_type": "numeric", "count": 10}
)

# Execute natural language tasks
result = await comm.execute_task(
    instruction="Generate 10 data points and process them",
    parameters={"data_type": "numeric"}
)
```

### External LLM Access

```python
from claude_coms.external_llm_module import ExternalLLMModule

# Create external LLM module
external_llm = ExternalLLMModule(registry)
await external_llm.start()

# Query any model
result = await external_llm.process({
    "action": "ask_model",
    "model": "gemini/gemini-2.0-flash-exp",
    "prompt": "Explain the key principles of modular design"
})

# Claude-to-Claude dialogue
result = await external_llm.process({
    "action": "claude_dialogue", 
    "model": "claude-3-opus-20240229",
    "prompt": "Let's collaborate on improving this module architecture"
})

# Compare multiple models
result = await external_llm.process({
    "action": "compare_models",
    "models": ["gemini/gemini-pro", "claude-3-opus-20240229", "gpt-4"],
    "prompt": "What's the best approach for inter-module communication?"
})
```

### CLI Interface

```bash
# List all messages
claude-comm list

# Send a message
claude-comm send sparta marker "Hello from SPARTA"

# Show progress
claude-comm progress

# MCP server operations
claude-comm mcp start
claude-comm mcp status

# Screenshot capture
claude-comm screenshot                              # Full screen capture
claude-comm screenshot --region center --quality 85 # Capture center region
claude-comm screenshot --url https://example.com    # Capture website
claude-comm screenshot --describe                   # Capture and describe
claude-comm screenshot --output chart.jpg --describe --prompt "Analyze this chart"

# Browser automation
claude-comm browser navigate --url https://example.com
claude-comm browser click --selector "#submit-button"
claude-comm browser fill --selector "#username" --value "user123"
claude-comm browser screenshot --output page.png
claude-comm browser navigate --url https://example.com --headed  # See the browser
```

### Screenshot and Browser Automation

```python
from claude_coms.core.modules import ScreenshotModule, BrowserAutomationModule

# Screenshot module
screenshot_module = ScreenshotModule()

# Capture screenshot
result = await screenshot_module.process({
    "action": "capture",
    "region": "full",
    "output": "dashboard.jpg",
    "quality": 80
})

# Capture and describe
result = await screenshot_module.process({
    "action": "capture",
    "url": "https://d3js.org",
    "wait": 5
})
if result["success"]:
    desc_result = await screenshot_module.process({
        "action": "describe",
        "file": result["result"]["file"],
        "prompt": "What visualization library is being showcased?"
    })

# Browser automation
browser_module = BrowserAutomationModule()
await browser_module.start()

# Navigate and interact
await browser_module.process({
    "action": "navigate",
    "url": "https://example.com/login"
})

await browser_module.process({
    "action": "fill",
    "selector": "#username",
    "value": "test_user"
})

await browser_module.process({
    "action": "click",
    "selector": "#login-button"
})

# Take screenshot of result
await browser_module.process({
    "action": "screenshot",
    "output_path": "login_result.png"
})

await browser_module.stop()
```

### PDF Processing via Marker Integration

Claude Module Communicator integrates with [Marker](https://github.com/VikParuchuri/marker) for advanced PDF processing, leveraging Marker's sophisticated table extraction and AI-powered content analysis.

```python
from claude_coms.core.adapters import MarkerAdapter, AdapterConfig

# Create Marker adapter
config = AdapterConfig(name="pdf-processor", protocol="marker")
adapter = MarkerAdapter(config)

# Connect to Marker
await adapter.connect()

# Extract tables from page 42
result = await adapter.send({
    "action": "extract_tables",
    "file_path": "document.pdf", 
    "page": 42,
    "claude_config": "tables_only"  # Use AI for better accuracy
})

if result["success"]:
    for table in result["tables"]:
        print(f"Table: {table['title']}")
        print(f"Confidence: {table.get('confidence', 0):.2f}")
        print(f"Headers: {table.get('headers', [])}")
        print(f"Rows: {len(table.get('rows', []))}")
```

#### CLI Usage for PDF Processing

```bash
# Extract page 42 with basic processing
cmc-cli pdf document.pdf --page 42

# Extract tables from page 42
cmc-cli pdf document.pdf --page 42 --tables

# Use Claude AI for better table extraction
cmc-cli pdf document.pdf --page 42 --tables --claude-config tables_only

# High accuracy mode (slower but better results)
cmc-cli pdf document.pdf --page 42 --tables --claude-config accuracy

# Save output as JSON
cmc-cli pdf document.pdf --page 42 --tables --output ./analysis/ --format json

# Save as Markdown
cmc-cli pdf document.pdf --page 42 --output ./analysis/ --format markdown
```

#### Claude Configuration Options

- `disabled` - No AI assistance (fastest)
- `minimal` - Basic AI enhancement
- `tables_only` - AI focused on table extraction
- `accuracy` - High accuracy mode
- `research` - Maximum quality (slowest)

### Graph Database Queries

```python
from claude_module_communicator import ArangoHybrid

# Initialize hybrid interface
arango = ArangoHybrid()

# Natural language queries
result = arango.query("Find modules that support batch processing")
result = arango.query("Show me communication patterns between modules")

# Slash commands
result = arango.query("/arango-find modules with capability:llm_access")
result = arango.query("/arango-analyze information-flow")

# Direct AQL
result = arango.query("AQL: FOR m IN modules FILTER 'external_llm_access' IN m.capabilities RETURN m")
```

### Reinforcement Learning Optimization

```python
from claude_coms.rl import OllamaClient, CommunicationReward, OllamaConfig

# Auto-selects best available model
client = OllamaClient()

# Optimize communication routes
task = {
    'source': 'DataProducer',
    'target': 'DataAnalyzer',
    'constraints': {'max_latency_ms': 500}
}
optimized_route = client.generate_route_optimization(task)

# Adapt schemas intelligently
adaptation = client.generate_schema_adaptation(
    source_schema={"temp_c": "number"},
    target_schema={"temperature_fahrenheit": "number"},
    sample_data={"temp_c": 25}
)

# Calculate rewards for learning
reward_fn = CommunicationReward()
reward = reward_fn.compute_route_reward({
    'success_rate': 0.95,
    'latency_ms': 120,
    'schema_compatibility': 0.9
})
```

## 🏗️ Architecture

### Core Components

1. **Module System** (`src/claude_coms/`)
   - `base_module.py` - Base class for all modules
   - `module_registry.py` - Dynamic module discovery
   - `module_communicator.py` - High-level communication API
   - `external_llm_module.py` - External LLM integration
   - `rl/` - Reinforcement learning optimization

2. **Graph Components** (`src/claude_module_communicator/`)
   - `graph_backend.py` - ArangoDB integration
   - `arango_expert.py` - Graph algorithms and patterns
   - `arango_hybrid.py` - Hybrid query interface

3. **MCP Server** (`src/mcp/`)
   - Full Model Context Protocol implementation
   - WebSocket and SSE support
   - Claude Desktop integration

4. **CLI** (`src/cli/`)
   - Command-line interface
   - Schema negotiation
   - Pipeline validation

### Available Models

#### Claude Models
- `claude-3-opus-20240229` - Most capable
- `claude-3-sonnet-20240229` - Balanced
- `claude-3-haiku-20240307` - Fast

#### Gemini Models
- `gemini/gemini-2.0-flash-exp` - Latest, very fast
- `gemini/gemini-pro` - Standard
- `gemini/gemini-pro-vision` - Multimodal

#### OpenAI Models
- `gpt-4-turbo-preview` - Latest GPT-4
- `gpt-4` - Standard GPT-4
- `gpt-3.5-turbo` - Fast and economical

## 🧪 Testing

All tests use real data validation (no mocking). Test structure mirrors source code for easy navigation:

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/claude_coms/core/ -v        # Core functionality
pytest tests/claude_coms/forecast/ -v    # Forecasting tests
pytest tests/claude_coms/cli/ -v         # CLI tests

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# See tests/README.md for complete testing guide
```

## 📚 Examples

### Complete Examples
- `examples/claude_external_models_demo.py` - External LLM integration
- `examples/llm_integration_example.py` - LLM-enhanced modules
- `demo_module_system.py` - Basic module system demo
- `demo_dynamic_communication.py` - Dynamic module discovery

### Running Examples
```bash
cd examples
python claude_external_models_demo.py
```

## 📖 Documentation

- [External Models Guide](docs/EXTERNAL_MODELS_GUIDE.md) - Complete LLM integration guide
- [Testing Documentation](docs/TESTING_CHANGES.md) - Real data testing approach
- [MCP Setup Guide](docs/usage/MCP_SETUP_CLAUDE_CODE.md) - Claude Desktop integration
- [Task Planning Guide](docs/usage/TASK_LIST_TEMPLATE_GUIDE.md) - Project planning

## 🛠️ Development

### Coding Standards
Follow the guidelines in `CLAUDE.md`:
- NO mocking in tests - use real data
- Function-first design (classes only when needed)
- Type hints for all functions
- Real data validation before tests

### Project Structure
```
claude-module-communicator/
├── src/
│   └── claude_coms/          # Main package
│       ├── cli/              # CLI interface
│       ├── core/             # Core functionality
│       │   ├── conversation/ # Conversation system
│       │   ├── llm/         # LLM integrations
│       │   ├── modules/     # Module system
│       │   └── storage/     # Storage backends
│       ├── forecast/        # Time series forecasting
│       ├── mcp/            # MCP server
│       └── rl/             # Reinforcement learning
├── tests/                   # Tests (mirrors src structure)
├── examples/               # Usage examples
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── data/                   # Data files (databases, etc.)
├── logs/                   # Log files (when generated)
└── archive/                # Archived/old files
```

## 🚦 Roadmap

- [x] Complete MCP server implementation
- [x] External LLM integration (Claude, Gemini, GPT)
- [x] Claude-to-Claude communication
- [x] ArangoDB graph backend
- [x] Real data testing framework
- [x] Reinforcement Learning optimization with Ollama
- [x] DeepRetrieval-style reward system
- [ ] VERL integration for full RL training
- [ ] WebSocket support for real-time updates
- [ ] Binary data transfer support
- [ ] Distributed module discovery
- [ ] Authentication system

## 🤝 Contributing

1. Follow coding standards in `CLAUDE.md`
2. Use real data in all tests (no mocking)
3. Add type hints to all functions
4. Update documentation for new features

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with `claude_max_proxy` for universal LLM access
- Uses ArangoDB for graph database capabilities
- Integrates with Claude Desktop via MCP protocol