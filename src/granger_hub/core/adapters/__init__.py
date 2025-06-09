"""
Protocol Adapters for Granger Hub.
Module: __init__.py
Description: Package initialization and exports

This module provides adapters for different communication protocols,
enabling seamless integration with services using MCP, REST, CLI, etc.
"""

from .base_adapter import ProtocolAdapter, AdapterConfig
from .cli_adapter import CLIAdapter
from .rest_adapter import RESTAdapter
from .mcp_adapter import MCPAdapter
from .marker_adapter import MarkerAdapter
from .adapter_registry import AdapterRegistry, AdapterFactory, AdapterInfo
from .hardware_adapter import HardwareAdapter, HardwareConfig, StreamMetadata
from .jtag_adapter import JTAGAdapter, JTAGConfig
from .scpi_adapter import SCPIAdapter, SCPIConfig

__all__ = [
    "ProtocolAdapter",
    "AdapterConfig",
    "CLIAdapter",
    "RESTAdapter",
    "MCPAdapter",
    "MarkerAdapter",
    "AdapterRegistry",
    "AdapterFactory",
    "AdapterInfo",
    "HardwareAdapter",
    "HardwareConfig",
    "StreamMetadata",
    "JTAGAdapter",
    "JTAGConfig",
    "SCPIAdapter",
    "SCPIConfig"
]