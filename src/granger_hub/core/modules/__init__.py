"""
Module core functionality.
Module: __init__.py
Description: Package initialization and exports

This module provides the base classes and registry for Claude modules.
"""

from .base_module import BaseModule
from .module_registry import ModuleRegistry, ModuleInfo
from .claude_code_communicator import ClaudeCodeCommunicator

# Import example modules if they exist
try:
    from .example_modules import DataProducerModule, DataProcessorModule, DataAnalyzerModule, OrchestratorModule
    __all__ = [
        "BaseModule",
        "ModuleRegistry",
        "ModuleInfo",
        "ClaudeCodeCommunicator",
        "DataProducerModule",
        "DataProcessorModule",
        "DataAnalyzerModule",
        "OrchestratorModule"
    ]
except ImportError:
    __all__ = [
        "BaseModule",
        "ModuleRegistry",
        "ModuleInfo",
        "ClaudeCodeCommunicator"
    ]