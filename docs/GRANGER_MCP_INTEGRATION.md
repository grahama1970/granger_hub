# Granger MCP Integration for Claude Module Communicator

This document describes the enhanced MCP (Model Context Protocol) integration for Claude Module Communicator, featuring the Granger edition improvements.

## Overview

The Granger integration brings advanced features to the Claude Module Communicator:

- **Dynamic Prompt Infrastructure**: Flexible prompt management system
- **Hub-Specific Prompts**: Tailored prompts for module orchestration
- **Smart Command Bundling**: Intelligent grouping of related commands
- **Enhanced MCP Server**: FastMCP-based server with analytics
- **Unified CLI/MCP Experience**: Seamless integration between CLI and MCP

## Key Components

### 1. Granger Slash MCP Mixin (`granger_slash_mcp_mixin.py`)

Enhanced version of the slash command generator with:

```python
from claude_coms.cli.granger_slash_mcp_mixin import add_slash_mcp_commands

# Add to any Typer app
add_slash_mcp_commands(
    app,
    prompt_registry=registry,
    enable_analytics=True,
    enable_smart_bundling=True
)
```

Features:
- Automatic parameter extraction and documentation
- Smart example generation
- Command bundling for workflows
- Prompt integration
- Analytics tracking

### 2. Prompt Infrastructure (`mcp/prompts.py`)

Core prompt management system:

```python
from claude_coms.mcp import Prompt, PromptRegistry

# Create a prompt
prompt = Prompt(
    name="orchestrate_modules",
    description="Orchestrate module communication",
    template="...",
    parameters={...},
    required_params=["task_description", "modules"]
)

# Register it
registry = get_prompt_registry()
registry.register(prompt)
```

### 3. Hub-Specific Prompts (`mcp/hub_prompts.py`)

Pre-defined prompts for common hub operations:

- `orchestrate_modules`: Plan multi-module workflows
- `analyze_module_compatibility`: Check module integration
- `design_communication_pattern`: Select optimal patterns
- `generate_integration_code`: Create integration code
- `debug_module_communication`: Troubleshoot issues
- `optimize_module_pipeline`: Improve performance
- `discover_module_capabilities`: Document modules
- `generate_integration_scenario`: Create test scenarios

### 4. FastMCP Server (`mcp/fastmcp_server.py`)

Enhanced MCP server with full feature support:

```python
from claude_coms.mcp.fastmcp_server import create_hub_mcp_server

# Create server with all features
mcp = create_hub_mcp_server(
    name="my-hub",
    enable_analytics=True
)
```

## Usage

### CLI Commands

#### Generate Claude Slash Commands

```bash
# Generate slash commands with bundling
cmc-cli generate-claude --bundle --verbose

# Generate with custom prefix
cmc-cli generate-claude --prefix hub --output .claude/hub-commands
```

#### Generate MCP Configuration

```bash
# Generate enhanced MCP config with prompts
cmc-cli generate-mcp-config --name my-hub --prompts

# Without prompts
cmc-cli generate-mcp-config --no-prompts
```

#### Serve MCP Server

```bash
# Run FastMCP server
cmc-cli serve-mcp-fastmcp --debug --reload

# Use generated config
cmc-cli serve-mcp-fastmcp --config mcp_config.json
```

#### Manage Prompts

```bash
# List all prompts
cmc-cli list-prompts

# Filter by category
cmc-cli list-prompts --category orchestration

# Show prompt details
cmc-cli show-prompt orchestrate_modules --example
```

### MCP Integration

#### Claude Desktop Configuration

Add to Claude Desktop's MCP config:

```json
{
  "mcpServers": {
    "claude-module-communicator": {
      "command": "python",
      "args": ["-m", "claude_coms.mcp.fastmcp_server"],
      "env": {
        "PYTHONPATH": "./src"
      }
    }
  }
}
```

#### Using Tools

In Claude Desktop, the tools are available:

```
Use the list_modules tool to see available modules
Use the execute_pipeline tool to run a multi-step workflow
Use the execute_prompt tool with prompt_name="orchestrate_modules"
```

### Prompt Examples

#### Orchestrate Modules

```python
registry = get_prompt_registry()
prompt = registry.get_prompt("orchestrate_modules")

rendered = prompt.render(
    task_description="Process PDFs and store in database",
    modules=[
        {"name": "marker", "description": "PDF processor"},
        {"name": "arangodb", "description": "Graph database"}
    ],
    requirements="Preserve document structure"
)
```

#### Debug Communication

```python
debug_prompt = registry.get_prompt("debug_module_communication")

rendered = debug_prompt.render(
    error_description="Timeout when sending to module",
    module_a={"name": "sender", "status": "active"},
    module_b={"name": "receiver", "status": "unknown"},
    communication_log="[2024-01-01] Send failed: timeout"
)
```

## Advanced Features

### Smart Command Bundling

The system automatically groups related commands:

- **CRUD Bundle**: create, read, update, delete commands
- **Data Bundle**: import, export, transform, validate
- **Analysis Bundle**: analyze, report, visualize, summarize
- **Management Bundle**: start, stop, restart, status

### Analytics Integration

When enabled, tracks:
- Tool usage frequency
- Module communication patterns
- Error rates and types
- Performance metrics

### Hot Reload Development

For development, use reload mode:

```bash
cmc-cli serve-mcp-fastmcp --reload --debug
```

Changes to prompts and tools are automatically picked up.

## Best Practices

1. **Organize Prompts by Category**: Use consistent categories for prompts
2. **Version Prompts**: Include version in prompt metadata
3. **Test with Examples**: Always provide examples for prompts
4. **Bundle Related Commands**: Group commands that work together
5. **Use Analytics**: Monitor usage to improve the system

## Troubleshooting

### Prompts Not Loading

```python
# Check registry
registry = get_prompt_registry()
print(f"Loaded prompts: {len(registry.list_prompts())}")

# List categories
print(f"Categories: {registry.list_categories()}")
```

### MCP Server Issues

```bash
# Test server creation
python -m claude_coms.mcp.fastmcp_server

# Check with debug mode
cmc-cli serve-mcp-fastmcp --debug
```

### Command Generation

```bash
# Verbose output for debugging
cmc-cli generate-claude --verbose --no-bundle
```

## Migration from Standard Integration

1. Update imports:
   ```python
   # Old
   from claude_coms.cli.slash_mcp_mixin import add_slash_mcp_commands
   
   # New
   from claude_coms.cli.granger_slash_mcp_mixin import add_slash_mcp_commands
   ```

2. Add prompt registry:
   ```python
   from claude_coms.mcp import get_prompt_registry
   registry = get_prompt_registry()
   
   add_slash_mcp_commands(app, prompt_registry=registry)
   ```

3. Update MCP config to use new server:
   ```json
   {
     "command": "python",
     "args": ["-m", "claude_coms.mcp.fastmcp_server"]
   }
   ```

## Future Enhancements

- **Prompt Templates from Files**: Load prompts from .j2 files
- **Prompt Versioning**: Track prompt changes over time
- **A/B Testing**: Test different prompts for effectiveness
- **Multi-Language Support**: Prompts in multiple languages
- **Prompt Chains**: Link prompts for complex workflows

## Contributing

To add new hub-specific prompts:

1. Add to `hub_prompts.py`:
   ```python
   registry.register(Prompt(
       name="your_prompt",
       description="What it does",
       template="...",
       category="appropriate_category"
   ))
   ```

2. Add examples to `get_hub_prompt_examples()`

3. Test with:
   ```bash
   cmc-cli show-prompt your_prompt
   ```