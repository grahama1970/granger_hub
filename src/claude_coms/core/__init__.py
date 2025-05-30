"""
Claude Module Communicator Core.

This package provides the core functionality for multi-module communication
with conversation support, following the 3-layer architecture.
"""

# Import from submodules
from .modules import (
    BaseModule,
    Message,
    ModuleRegistry,
    ModuleInfo,
    DataProducerModule,
    DataProcessorModule,
    DataAnalyzerModule,
    OrchestratorModule
)

from .conversation import (
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

from .module_communicator import ModuleCommunicator

__version__ = "0.1.0"

__all__ = [
    # Module core
    "BaseModule",
    "Message",
    "ModuleRegistry",
    "ModuleInfo",
    "DataProducerModule",
    "DataProcessorModule",
    "DataAnalyzerModule",
    "OrchestratorModule",
    
    # Conversation core
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
    "SchemaProposal",
    
    # High-level orchestrator
    "ModuleCommunicator"
]