"""
Claude Module Communicator Core.

This package provides the core functionality for multi-module communication
with conversation support, following the 3-layer architecture.
"""

# Import from submodules
from .modules import BaseModule, ModuleRegistry, ModuleInfo

# Import example modules if available
try:
    from .modules import DataProducerModule, DataProcessorModule, DataAnalyzerModule, OrchestratorModule
    HAS_EXAMPLE_MODULES = True
except ImportError:
    HAS_EXAMPLE_MODULES = False

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
    "ModuleRegistry",
    "ModuleInfo",
    
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

# Add example modules if available
if HAS_EXAMPLE_MODULES:
    __all__.extend([
        "DataProducerModule",
        "DataProcessorModule",
        "DataAnalyzerModule",
        "OrchestratorModule"
    ])