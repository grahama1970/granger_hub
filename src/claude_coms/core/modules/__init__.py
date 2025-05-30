"""
Module core functionality.

This module provides the base classes and registry for Claude modules.
"""

from .base_module import BaseModule, Message
from .module_registry import ModuleRegistry, ModuleInfo
from .example_modules import DataProducerModule, DataProcessorModule, DataAnalyzerModule, OrchestratorModule
from .screenshot_module import ScreenshotModule
from .browser_automation_module import BrowserAutomationModule
from .browser_test_module import BrowserTestModule
from .pdf_navigator_module import PDFNavigatorModule

__all__ = [
    "BaseModule",
    "Message",
    "ModuleRegistry",
    "ModuleInfo",
    "DataProducerModule",
    "DataProcessorModule",
    "DataAnalyzerModule",
    "OrchestratorModule",
    "ScreenshotModule",
    "BrowserAutomationModule",
    "BrowserTestModule",
    "PDFNavigatorModule"
]