"""
Conversation core functionality.
Module: __init__.py
Description: Package initialization and exports

This module provides the core components for multi-turn conversations between modules.
"""

from .conversation_message import ConversationMessage, ConversationState
from .conversation_module import ConversationModule
from .conversation_manager import ConversationManager
from .conversation_protocol import (
    ConversationProtocol,
    ConversationIntent,
    ConversationPhase,
    ConversationHandshake,
    ConversationResponse,
    ConversationCapable,
    SchemaProposal
)

__all__ = [
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