"""
Universal Slash Command and MCP Generation for Typer CLIs (Granger Edition)

This module provides enhanced slash command and MCP server generation for Typer CLIs,
with support for prompt infrastructure, tool bundling, and intelligent registration.

Key Features:
- Automatic tool discovery and registration
- Prompt infrastructure integration
- Smart parameter inference
- Async/sync command handling
- Rich output formatting
- MCP server with FastMCP

Usage:
    from claude_coms.cli.granger_slash_mcp_mixin import add_slash_mcp_commands
    
    app = typer.Typer()
    add_slash_mcp_commands(app)  # That's it!
"""

import typer
from pathlib import Path
from typing import Optional, Set, Callable, Any, Dict, List, Union
import json
import sys
import inspect
from functools import wraps
import asyncio
from contextlib import contextmanager, redirect_stdout
from io import StringIO
import traceback
from datetime import datetime

# Import prompt infrastructure
try:
    from ..mcp.prompts import PromptRegistry, get_prompt_registry
    PROMPTS_AVAILABLE = True
except ImportError:
    PROMPTS_AVAILABLE = False

# Import FastMCP for server functionality
try:
    from fastmcp import FastMCP
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False


def add_slash_mcp_commands(
    app: typer.Typer,
    skip_commands: Optional[Set[str]] = None,
    command_prefix: str = "generate",
    output_dir: str = ".claude/commands",
    prompt_registry: Optional['PromptRegistry'] = None,
    enable_analytics: bool = True,
    enable_smart_bundling: bool = True
) -> typer.Typer:
    """
    Add enhanced slash command and MCP generation capabilities to any Typer app.
    
    This is the Granger edition with advanced features:
    - Smart command bundling for related operations
    - Prompt infrastructure with dynamic prompts
    - Analytics and usage tracking
    - Enhanced error handling and recovery
    
    Args:
        app: The Typer application to enhance
        skip_commands: Set of command names to skip during generation
        command_prefix: Prefix for generation commands (default: "generate")
        output_dir: Default output directory for slash commands
        prompt_registry: Optional PromptRegistry for managing prompts
        enable_analytics: Enable command usage analytics
        enable_smart_bundling: Group related commands intelligently
        
    Returns:
        The enhanced Typer app
    """
    
    # Default skip list includes our generation commands
    default_skip = {
        f"{command_prefix}-claude",
        f"{command_prefix}-mcp-config", 
        f"{command_prefix}-mcp-server",
        "serve-mcp",
        "serve-mcp-fastmcp",
        f"{command_prefix}_claude",
        f"{command_prefix}_mcp_config",
        f"{command_prefix}_mcp_server",
        "serve_mcp",
        "list-prompts",
        "show-prompt"
    }
    
    if skip_commands:
        default_skip.update(skip_commands)
    
    # Use provided registry or get global one
    if PROMPTS_AVAILABLE:
        registry = prompt_registry or get_prompt_registry()
    else:
        registry = None
    
    @app.command(name=f"{command_prefix}-claude")
    def generate_claude_command(
        output_path: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
        prefix: Optional[str] = typer.Option(None, "--prefix", "-p", help="Command prefix"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
        bundle: bool = typer.Option(True, "--bundle/--no-bundle", help="Bundle related commands"),
        include_examples: bool = typer.Option(True, "--examples/--no-examples", help="Include usage examples")
    ):
        """Generate Claude Code slash commands for all CLI commands."""
        
        # Use provided output or default
        out_dir = output_path or Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        generated = 0
        bundles = {}
        
        # Analyze commands for bundling
        if enable_smart_bundling and bundle:
            bundles = _analyze_command_bundles(app, default_skip)
        
        # Generate individual commands
        for command in app.registered_commands:
            cmd_name = command.name or command.callback.__name__
            
            if cmd_name in default_skip:
                continue
                
            func = command.callback
            docstring = func.__doc__ or f"Run {cmd_name} command"
            
            # Clean docstring
            doc_lines = docstring.strip().split('\n')
            short_desc = doc_lines[0]
            
            # Add prefix if specified
            slash_name = f"{prefix}-{cmd_name}" if prefix else cmd_name
            
            # Get parameter info
            params_info = _extract_parameter_info(func)
            
            # Generate content with enhanced formatting
            content = _generate_slash_command_content(
                cmd_name=cmd_name,
                slash_name=slash_name,
                short_desc=short_desc,
                docstring=docstring,
                params_info=params_info,
                include_examples=include_examples
            )
            
            # Write file
            cmd_file = out_dir / f"{slash_name}.md"
            cmd_file.write_text(content)
            
            if verbose:
                typer.echo(f"✅ Created: {cmd_file}")
            else:
                typer.echo(f"✅ /project:{slash_name}")
                
            generated += 1
        
        # Generate bundle files if enabled
        if bundles:
            typer.echo(f"\n📦 Generating command bundles...")
            for bundle_name, commands in bundles.items():
                bundle_file = out_dir / f"{bundle_name}-bundle.md"
                bundle_content = _generate_bundle_content(bundle_name, commands)
                bundle_file.write_text(bundle_content)
                typer.echo(f"📦 Created bundle: {bundle_name}")
        
        typer.echo(f"\n📁 Generated {generated} commands in {out_dir}/")
        
        if enable_analytics:
            _track_generation_event("slash_commands", generated)
    
    @app.command(name=f"{command_prefix}-mcp-config")
    def generate_mcp_config_command(
        output: Path = typer.Option("mcp_config.json", "--output", "-o"),
        name: Optional[str] = typer.Option(None, "--name"),
        host: str = typer.Option("localhost", "--host"),
        port: int = typer.Option(5000, "--port"),
        include_prompts: bool = typer.Option(True, "--prompts/--no-prompts", help="Include prompts in config"),
        include_resources: bool = typer.Option(False, "--resources/--no-resources", help="Include resources")
    ):
        """Generate MCP (Model Context Protocol) configuration with enhanced features."""
        
        server_name = name or app.info.name or "claude-module-communicator"
        
        # Build tool definitions with enhanced metadata
        tools = {}
        tool_groups = {}
        
        for command in app.registered_commands:
            cmd_name = command.name or command.callback.__name__
            
            if cmd_name in default_skip:
                continue
                
            func = command.callback
            tool_def = _build_tool_definition(func, cmd_name)
            tools[cmd_name] = tool_def
            
            # Group tools by category
            category = _infer_tool_category(cmd_name, func)
            if category not in tool_groups:
                tool_groups[category] = []
            tool_groups[category].append(cmd_name)
        
        # Build prompts section if available
        prompts = {}
        if include_prompts and PROMPTS_AVAILABLE and registry:
            for prompt in registry.list_prompts():
                prompts[prompt.name] = {
                    "description": prompt.description,
                    "inputSchema": {
                        "type": "object",
                        "properties": prompt.parameters,
                        "required": prompt.required_params
                    },
                    "tags": prompt.tags,
                    "examples": prompt.examples
                }
        
        # Build resources section if requested
        resources = {}
        if include_resources:
            resources = _build_resource_definitions(app)
        
        # Build enhanced config
        config = {
            "name": server_name,
            "version": "2.0.0",
            "description": f"Enhanced MCP server for {server_name}",
            "metadata": {
                "author": "Claude Module Communicator",
                "generation_time": datetime.utcnow().isoformat(),
                "enhanced_features": ["prompts", "tool_groups", "analytics"]
            },
            "server": {
                "command": sys.executable,
                "args": ["-m", "claude_coms.cli.claude_comm", "serve-mcp", "--host", host, "--port", str(port)],
                "transport": "stdio"
            },
            "tools": tools,
            "tool_groups": tool_groups,
            "capabilities": {
                "tools": True,
                "prompts": bool(prompts),
                "resources": bool(resources),
                "logging": True
            }
        }
        
        if prompts:
            config["prompts"] = prompts
        
        if resources:
            config["resources"] = resources
        
        # Write config with pretty formatting
        output.write_text(json.dumps(config, indent=2, sort_keys=False))
        typer.echo(f"✅ Generated enhanced MCP config: {output}")
        typer.echo(f"📋 Includes {len(tools)} tools in {len(tool_groups)} groups")
        if prompts:
            typer.echo(f"💬 Includes {len(prompts)} prompts")
        if resources:
            typer.echo(f"📚 Includes {len(resources)} resources")
    
    @app.command(name="serve-mcp-fastmcp")
    def serve_mcp_fastmcp_command(
        host: str = typer.Option("localhost", "--host"),
        port: int = typer.Option(5000, "--port"),
        config: Optional[Path] = typer.Option(None, "--config"),
        debug: bool = typer.Option(False, "--debug"),
        reload: bool = typer.Option(False, "--reload", help="Auto-reload on changes")
    ):
        """Serve this CLI as an MCP server using FastMCP with enhanced features."""
        
        if not FASTMCP_AVAILABLE:
            typer.echo("❌ FastMCP not installed!")
            typer.echo("\nInstall with: uv add fastmcp")
            raise typer.Exit(1)
        
        # Load config if provided
        if config and config.exists():
            config_data = json.loads(config.read_text())
            server_name = config_data.get("name", "claude-module-communicator")
        else:
            server_name = app.info.name or "claude-module-communicator"
        
        # Create FastMCP instance with enhanced setup
        mcp = FastMCP(server_name)
        
        # Add metadata
        mcp.meta["version"] = "2.0.0"
        mcp.meta["features"] = ["prompts", "analytics", "hot-reload"]
        
        # Register all tools with enhanced wrappers
        registered_tools = _register_tools_with_fastmcp(app, mcp, default_skip, debug)
        
        # Register prompts if available
        registered_prompts = 0
        if PROMPTS_AVAILABLE and registry:
            registered_prompts = _register_prompts_with_fastmcp(mcp, registry)
        
        # Setup analytics if enabled
        if enable_analytics:
            _setup_mcp_analytics(mcp)
        
        typer.echo(f"🔧 Registered {registered_tools} tools")
        if registered_prompts:
            typer.echo(f"💬 Registered {registered_prompts} prompts")
        
        typer.echo(f"🚀 Starting enhanced MCP server on {host}:{port}")
        typer.echo(f"\n📡 Server endpoint: http://{host}:{port}")
        if reload:
            typer.echo("🔄 Auto-reload enabled")
        typer.echo("\nPress Ctrl+C to stop")
        
        try:
            # Run with optional reload
            if reload:
                import uvicorn
                uvicorn.run(
                    "claude_coms.mcp.server:app",
                    host=host,
                    port=port,
                    reload=True,
                    log_level="debug" if debug else "info"
                )
            else:
                mcp.run(
                    transport="stdio"
                )
        except KeyboardInterrupt:
            typer.echo("\n\n🛑 Server stopped gracefully")
    
    # Add prompt management commands if available
    if PROMPTS_AVAILABLE and registry:
        @app.command(name="list-prompts")
        def list_prompts_command(
            category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
            tags: Optional[List[str]] = typer.Option(None, "--tag", "-t", help="Filter by tags")
        ):
            """List all available prompts in the registry."""
            prompts = registry.list_prompts(category=category, tags=tags)
            
            if not prompts:
                typer.echo("No prompts found matching criteria")
                return
            
            # Group by category
            by_category = {}
            for prompt in prompts:
                cat = prompt.category or "general"
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(prompt)
            
            # Display prompts
            for cat, cat_prompts in sorted(by_category.items()):
                typer.echo(f"\n📁 {cat.upper()}")
                typer.echo("─" * 40)
                for prompt in sorted(cat_prompts, key=lambda p: p.name):
                    typer.echo(f"  • {prompt.name}: {prompt.description}")
                    if prompt.tags:
                        typer.echo(f"    Tags: {', '.join(prompt.tags)}")
        
        @app.command(name="show-prompt")
        def show_prompt_command(
            name: str = typer.Argument(..., help="Prompt name"),
            format: str = typer.Option("text", "--format", "-f", help="Output format: text, json, yaml"),
            example: bool = typer.Option(False, "--example", "-e", help="Show example usage")
        ):
            """Show details of a specific prompt."""
            prompt = registry.get_prompt(name)
            if not prompt:
                typer.echo(f"❌ Prompt not found: {name}")
                raise typer.Exit(1)
            
            if format == "json":
                output = {
                    "name": prompt.name,
                    "description": prompt.description,
                    "category": prompt.category,
                    "tags": prompt.tags,
                    "parameters": prompt.parameters,
                    "required_params": prompt.required_params,
                    "template": prompt.template,
                    "examples": prompt.examples
                }
                typer.echo(json.dumps(output, indent=2))
            else:
                typer.echo(f"📋 {prompt.name}")
                typer.echo(f"Description: {prompt.description}")
                if prompt.category:
                    typer.echo(f"Category: {prompt.category}")
                if prompt.tags:
                    typer.echo(f"Tags: {', '.join(prompt.tags)}")
                
                if prompt.parameters:
                    typer.echo("\nParameters:")
                    for param, schema in prompt.parameters.items():
                        required = "required" if param in prompt.required_params else "optional"
                        typer.echo(f"  • {param} ({required}): {schema.get('description', 'No description')}")
                
                if example and prompt.examples:
                    typer.echo("\nExample:")
                    typer.echo(prompt.examples[0])
    
    return app


# Helper functions

def _extract_parameter_info(func: Callable) -> Dict[str, Any]:
    """Extract detailed parameter information from a function."""
    sig = inspect.signature(func)
    params_info = {}
    
    for param_name, param in sig.parameters.items():
        if param_name in ['self', 'ctx']:
            continue
        
        info = {
            "type": "string",
            "required": param.default == param.empty,
            "default": None if param.default == param.empty else param.default
        }
        
        # Infer type from annotation
        if param.annotation != param.empty:
            if param.annotation == int:
                info["type"] = "integer"
            elif param.annotation == bool:
                info["type"] = "boolean"
            elif param.annotation == float:
                info["type"] = "number"
            elif hasattr(param.annotation, "__origin__"):
                # Handle Optional, List, etc.
                origin = param.annotation.__origin__
                if origin == list:
                    info["type"] = "array"
                elif origin == dict:
                    info["type"] = "object"
        
        # Extract description from docstring if available
        if func.__doc__:
            # Simple heuristic to find parameter descriptions
            for line in func.__doc__.split('\n'):
                if param_name in line and ':' in line:
                    desc_part = line.split(':', 1)[1].strip()
                    info["description"] = desc_part
                    break
        
        params_info[param_name] = info
    
    return params_info


def _generate_slash_command_content(
    cmd_name: str,
    slash_name: str,
    short_desc: str,
    docstring: str,
    params_info: Dict[str, Any],
    include_examples: bool = True
) -> str:
    """Generate enhanced slash command content."""
    
    # Build parameter documentation
    param_docs = []
    for param, info in params_info.items():
        param_line = f"- `{param}`: {info.get('description', param)}"
        if info.get('required'):
            param_line += " (required)"
        if info.get('default') is not None:
            param_line += f" [default: {info['default']}]"
        param_docs.append(param_line)
    
    content = f"""# {short_desc}

{docstring.strip()}

## Usage

```bash
/project:{slash_name} [arguments]
```

## Parameters

{chr(10).join(param_docs) if param_docs else "No parameters required."}
"""
    
    if include_examples:
        # Generate smart examples based on parameters
        examples = _generate_smart_examples(slash_name, params_info)
        if examples:
            content += f"""
## Examples

{chr(10).join(examples)}
"""
    
    content += """
---
*Enhanced slash command with Granger features*
"""
    
    return content


def _generate_smart_examples(slash_name: str, params_info: Dict[str, Any]) -> List[str]:
    """Generate intelligent examples based on parameter types."""
    examples = []
    
    # Basic example
    basic_params = []
    for param, info in params_info.items():
        if info.get('required'):
            if info['type'] == 'string':
                basic_params.append(f'--{param} "example"')
            elif info['type'] == 'integer':
                basic_params.append(f'--{param} 42')
            elif info['type'] == 'boolean':
                basic_params.append(f'--{param}')
    
    if basic_params:
        examples.append(f"```bash\n/project:{slash_name} {' '.join(basic_params)}\n```")
    else:
        examples.append(f"```bash\n/project:{slash_name}\n```")
    
    # Advanced example with all parameters
    if len(params_info) > len(basic_params):
        all_params = []
        for param, info in params_info.items():
            if info['type'] == 'string':
                all_params.append(f'--{param} "value"')
            elif info['type'] == 'integer':
                all_params.append(f'--{param} 100')
            elif info['type'] == 'boolean':
                all_params.append(f'--{param}')
            elif info['type'] == 'array':
                all_params.append(f'--{param} item1 --{param} item2')
        
        examples.append(f"```bash\n# With all options\n/project:{slash_name} {' '.join(all_params)}\n```")
    
    return examples


def _analyze_command_bundles(app: typer.Typer, skip_commands: Set[str]) -> Dict[str, List[str]]:
    """Analyze commands to create intelligent bundles."""
    bundles = {}
    
    # Common patterns for grouping
    patterns = {
        "crud": ["create", "read", "update", "delete", "list"],
        "data": ["import", "export", "transform", "validate"],
        "analysis": ["analyze", "report", "visualize", "summarize"],
        "management": ["start", "stop", "restart", "status", "configure"]
    }
    
    for pattern_name, keywords in patterns.items():
        matching_commands = []
        for command in app.registered_commands:
            cmd_name = command.name or command.callback.__name__
            if cmd_name in skip_commands:
                continue
            
            # Check if command matches pattern
            for keyword in keywords:
                if keyword in cmd_name.lower():
                    matching_commands.append(cmd_name)
                    break
        
        if len(matching_commands) >= 2:
            bundles[pattern_name] = matching_commands
    
    return bundles


def _generate_bundle_content(bundle_name: str, commands: List[str]) -> str:
    """Generate content for a command bundle."""
    return f"""# {bundle_name.title()} Command Bundle

This bundle groups related {bundle_name} operations for easier access.

## Commands in this bundle:

{chr(10).join(f"- `/project:{cmd}`" for cmd in commands)}

## Usage

Use these commands together for complete {bundle_name} workflows.

### Example Workflow:

```bash
# Example {bundle_name} workflow
{chr(10).join(f"/project:{cmd} [args]" for cmd in commands[:3])}
```

---
*Command bundle for organized workflows*
"""


def _build_tool_definition(func: Callable, cmd_name: str) -> Dict[str, Any]:
    """Build enhanced tool definition with metadata."""
    docstring = func.__doc__ or f"Execute {cmd_name}"
    params_info = _extract_parameter_info(func)
    
    # Build JSON schema for parameters
    properties = {}
    required = []
    
    for param_name, info in params_info.items():
        properties[param_name] = {
            "type": info["type"],
            "description": info.get("description", f"Parameter: {param_name}")
        }
        
        if info["type"] == "array":
            properties[param_name]["items"] = {"type": "string"}
        
        if info.get("default") is not None:
            properties[param_name]["default"] = info["default"]
        
        if info.get("required"):
            required.append(param_name)
    
    return {
        "description": docstring.strip().split('\n')[0],
        "longDescription": docstring.strip(),
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False
        },
        "metadata": {
            "category": _infer_tool_category(cmd_name, func),
            "async": asyncio.iscoroutinefunction(func),
            "complexity": _estimate_complexity(func)
        }
    }


def _infer_tool_category(cmd_name: str, func: Callable) -> str:
    """Infer tool category from name and function."""
    # Category keywords
    categories = {
        "data": ["import", "export", "transform", "parse", "convert"],
        "analysis": ["analyze", "report", "summarize", "visualize"],
        "communication": ["send", "receive", "broadcast", "message"],
        "management": ["create", "update", "delete", "configure", "manage"],
        "utility": ["help", "version", "info", "debug", "test"]
    }
    
    cmd_lower = cmd_name.lower()
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in cmd_lower:
                return category
    
    return "general"


def _estimate_complexity(func: Callable) -> str:
    """Estimate function complexity for metadata."""
    # Simple heuristic based on function size
    import ast
    try:
        source = inspect.getsource(func)
        tree = ast.parse(source)
        
        # Count nodes as complexity metric
        node_count = sum(1 for _ in ast.walk(tree))
        
        if node_count < 20:
            return "simple"
        elif node_count < 50:
            return "moderate"
        else:
            return "complex"
    except:
        return "unknown"


def _build_resource_definitions(app: typer.Typer) -> Dict[str, Any]:
    """Build resource definitions for the MCP config."""
    resources = {}
    
    # Add common resources
    resources["help"] = {
        "description": "CLI help documentation",
        "mimeType": "text/markdown",
        "uri": "help://commands"
    }
    
    resources["config"] = {
        "description": "Configuration examples",
        "mimeType": "application/json",
        "uri": "config://examples"
    }
    
    return resources


def _register_tools_with_fastmcp(
    app: typer.Typer,
    mcp: 'FastMCP',
    skip_commands: Set[str],
    debug: bool
) -> int:
    """Register all tools with FastMCP instance."""
    registered = 0
    
    for command in app.registered_commands:
        cmd_name = command.name or command.callback.__name__
        
        if cmd_name in skip_commands:
            continue
        
        func = command.callback
        if not func:
            continue
        
        # Create enhanced wrapper
        tool_def = _build_tool_definition(func, cmd_name)
        
        @mcp.tool(
            name=cmd_name,
            description=tool_def["description"]
        )
        async def tool_wrapper(**kwargs) -> Dict[str, Any]:
            """Enhanced tool wrapper with error handling and analytics."""
            start_time = datetime.utcnow()
            
            try:
                # Find the original function
                original_func = None
                for cmd in app.registered_commands:
                    if (cmd.name or cmd.callback.__name__) == cmd_name:
                        original_func = cmd.callback
                        break
                
                if not original_func:
                    return {
                        "error": f"Tool {cmd_name} not found",
                        "status": "error"
                    }
                
                # Handle async functions
                if asyncio.iscoroutinefunction(original_func):
                    result = await original_func(**kwargs)
                else:
                    # Run sync function in executor
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, original_func, **kwargs)
                
                # Track success
                if enable_analytics:
                    _track_tool_usage(cmd_name, "success", start_time)
                
                return {
                    "result": result,
                    "status": "success",
                    "execution_time": (datetime.utcnow() - start_time).total_seconds()
                }
                
            except Exception as e:
                # Track failure
                if enable_analytics:
                    _track_tool_usage(cmd_name, "failure", start_time)
                
                return {
                    "error": str(e),
                    "status": "error",
                    "traceback": traceback.format_exc() if debug else None,
                    "execution_time": (datetime.utcnow() - start_time).total_seconds()
                }
        
        registered += 1
        
        if debug:
            typer.echo(f"  ✅ Registered: {cmd_name}")
    
    return registered


def _register_prompts_with_fastmcp(mcp: 'FastMCP', registry: 'PromptRegistry') -> int:
    """Register all prompts with FastMCP instance."""
    registered = 0
    
    for prompt in registry.list_prompts():
        @mcp.prompt(
            name=prompt.name,
            description=prompt.description
        )
        async def prompt_handler(**kwargs) -> str:
            """Handle prompt requests."""
            try:
                # Get the prompt template
                filled_prompt = registry.get_prompt(prompt.name)
                if not filled_prompt:
                    return f"Prompt {prompt.name} not found"
                
                # Fill the template with provided parameters
                return filled_prompt.render(**kwargs)
                
            except Exception as e:
                return f"Error rendering prompt: {str(e)}"
        
        registered += 1
    
    return registered


def _setup_mcp_analytics(mcp: 'FastMCP'):
    """Setup analytics tracking for MCP server."""
    # This would integrate with actual analytics service
    pass


def _track_generation_event(event_type: str, count: int):
    """Track generation events for analytics."""
    # This would send to actual analytics service
    pass


def _track_tool_usage(tool_name: str, status: str, start_time: datetime):
    """Track tool usage for analytics."""
    # This would send to actual analytics service
    pass


def slash_mcp_cli(name: Optional[str] = None, **kwargs):
    """
    Decorator to automatically add slash/MCP commands to a Typer app.
    
    Usage:
        @slash_mcp_cli(name="my-app")
        app = typer.Typer()
        
        @app.command()
        def hello(name: str):
            print(f"Hello {name}")
    """
    def decorator(app: typer.Typer) -> typer.Typer:
        if name:
            app.info.name = name
        return add_slash_mcp_commands(app, **kwargs)
    
    return decorator


if __name__ == "__main__":
    # Validation with real data
    print(f"Validating {__file__}...")
    
    # Test the mixin with a sample app
    test_app = typer.Typer()
    
    @test_app.command()
    def test_command(name: str = "world"):
        """Test command for validation."""
        print(f"Hello, {name}!")
    
    # Add mixin
    enhanced_app = add_slash_mcp_commands(test_app)
    
    # Verify commands were added
    added_commands = [cmd.name for cmd in enhanced_app.registered_commands]
    expected = ["test_command", "generate-claude", "generate-mcp-config", "serve-mcp-fastmcp"]
    
    for cmd in expected:
        assert cmd in added_commands, f"Expected command {cmd} not found"
    
    print("✅ Validation passed")