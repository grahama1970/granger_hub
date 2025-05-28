"""
Claude Module Communicator - Dynamic inter-module communication framework.

This package provides a framework for modules to dynamically discover and 
communicate with each other using Claude Code as an intelligent message broker.
"""

from .base_module import BaseModule, Message
from .claude_code_communicator import ClaudeCodeCommunicator, CommunicationResult
from .module_registry import ModuleRegistry, ModuleInfo
from .example_modules import (
    DataProducerModule,
    DataProcessorModule,
    DataAnalyzerModule,
    OrchestratorModule
)

__all__ = [
    # Core classes
    "BaseModule",
    "Message",
    "ClaudeCodeCommunicator",
    "CommunicationResult",
    "ModuleRegistry",
    "ModuleInfo",
    
    # Example modules
    "DataProducerModule",
    "DataProcessorModule", 
    "DataAnalyzerModule",
    "OrchestratorModule"
]

__version__ = "0.1.0"