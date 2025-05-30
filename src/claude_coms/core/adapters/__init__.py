"""
Protocol Adapters for Claude Module Communicator.

This module provides adapters for different communication protocols,
enabling seamless integration with services using MCP, REST, CLI, etc.
"""

from .base_adapter import ProtocolAdapter, AdapterConfig
from .cli_adapter import CLIAdapter
from .rest_adapter import RESTAdapter
from .mcp_adapter import MCPAdapter
from .marker_adapter import MarkerAdapter

__all__ = [
    "ProtocolAdapter",
    "AdapterConfig",
    "CLIAdapter",
    "RESTAdapter",
    "MCPAdapter",
    "MarkerAdapter"
]