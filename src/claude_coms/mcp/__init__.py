"""
MCP (Model Context Protocol) Integration via CLI Slash Commands.

This module provides MCP integration through the CLI layer using slash commands,
rather than a separate server. The slash_mcp_mixin in the CLI layer generates
MCP-compatible interfaces directly from Typer commands.

The integration approach:
1. CLI commands are defined in claude_coms.cli
2. slash_mcp_mixin.py adds MCP generation capabilities
3. Generated slash commands can be used by Claude Desktop

This is a more lightweight approach than running a separate MCP server.

ARCHITECTURE NOTE:
The files in this directory (server.py, handlers.py, tools.py) were originally
designed for a FastAPI-based MCP server. However, the actual implementation uses
CLI slash commands via src/claude_coms/cli/slash_mcp_mixin.py.

These files are kept for reference but are NOT USED in the current architecture.
The actual MCP functionality is provided through:
- src/claude_coms/cli/slash_mcp_mixin.py - Generates MCP commands from Typer CLI
- src/claude_coms/cli/commands.py - Contains the actual CLI commands
"""

# MCP functionality is provided through CLI slash commands
# See claude_coms.cli.slash_mcp_mixin for implementation

__all__ = []