"""
CLI Module for Granger Hub.
Module: __init__.py
Description: Package initialization and exports

This module provides the command-line interface using Typer
with support for MCP generation via slash commands.
"""

from .claude_comm import app as main_app
from .communication_commands import app as comm_app
from .conversation_commands import app as conversation_app
from .slash_mcp_mixin import add_slash_mcp_commands

# Add sub-applications
main_app.add_typer(comm_app, name="comm")
main_app.add_typer(conversation_app, name="conversation")

__all__ = [
    "main_app",
    "comm_app", 
    "conversation_app",
    "add_slash_mcp_commands"
]