"""
Claude Module Communicator - Dynamic inter-module communication framework.

This package provides a framework for modules to dynamically discover and 
communicate with each other using Claude Code as an intelligent message broker.

Following the 3-layer architecture:
- core/: Business logic and core functionality
- cli/: Command-line interface
- mcp/: MCP integration
"""

# Import core functionality from the proper location
from .core.modules import (
    BaseModule,
    ModuleRegistry,
    ModuleInfo,
    DataProducerModule,
    DataProcessorModule,
    DataAnalyzerModule,
    OrchestratorModule
)

from .core.conversation import (
    ConversationMessage,
    ConversationState,
    ConversationModule,
    ConversationManager,
    ConversationProtocol,
    ConversationIntent,
    ConversationPhase,
    ConversationHandshake,
    ConversationResponse,
    ConversationCapable,
    SchemaProposal
)

__all__ = [
    # Core module classes
    "BaseModule",
    "ModuleRegistry",
    "ModuleInfo",
    
    # Example modules
    "DataProducerModule",
    "DataProcessorModule",
    "DataAnalyzerModule",
    "OrchestratorModule",
    
    # Conversation support
    "ConversationMessage",
    "ConversationState",
    "ConversationModule",
    "ConversationManager",
    "ConversationProtocol",
    "ConversationIntent",
    "ConversationPhase",
    "ConversationHandshake",
    "ConversationResponse",
    "ConversationCapable",
    "SchemaProposal"
]

__version__ = "0.1.0"