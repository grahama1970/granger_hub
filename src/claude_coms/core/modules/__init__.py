"""
Module core functionality.

This module provides the base classes and registry for Claude modules.
"""

from .base_module import BaseModule, Message
from .module_registry import ModuleRegistry, ModuleInfo
from .example_modules import DataProducerModule, DataProcessorModule, DataAnalyzerModule, OrchestratorModule

__all__ = [
    "BaseModule",
    "Message",
    "ModuleRegistry",
    "ModuleInfo",
    "DataProducerModule",
    "DataProcessorModule",
    "DataAnalyzerModule",
    "OrchestratorModule"
]