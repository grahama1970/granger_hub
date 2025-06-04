"""
Module-to-Module Conversation Protocol.

Purpose: Defines the protocol for multi-turn conversations between modules,
including message formats, handshake procedures, and conversation lifecycle.

This implements Task #004 from the multi-turn conversation implementation.
"""

from typing import Dict, Any, List, Optional, Protocol, runtime_checkable
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum

try:
    from .conversation_message import ConversationMessage, ConversationState
except ImportError:
    # For standalone testing
    from conversation_message import ConversationMessage, ConversationState


class ConversationIntent(Enum):
    """Intent types for starting conversations."""
    QUERY = "query"  # Simple question/answer
    NEGOTIATE = "negotiate"  # Multi-turn negotiation
    COLLABORATE = "collaborate"  # Joint task execution
    TRANSFER = "transfer"  # Hand off task to another module
    INFORM = "inform"  # One-way information sharing


class ConversationPhase(Enum):
    """Phases of a module conversation."""
    HANDSHAKE = "handshake"  # Initial connection
    NEGOTIATION = "negotiation"  # Agreeing on parameters
    EXECUTION = "execution"  # Main conversation
    CONFIRMATION = "confirmation"  # Confirming results
    TERMINATION = "termination"  # Closing conversation


@dataclass
class ConversationHandshake:
    """Initial handshake for starting a conversation."""
    intent: ConversationIntent
    proposed_schema: Dict[str, Any]  # Expected message format
    capabilities_required: List[str]  # What the initiator needs
    capabilities_offered: List[str]  # What the initiator provides
    timeout_seconds: int = 300
    max_turns: int = 20
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationResponse:
    """Response to conversation messages."""
    accepts: bool  # Whether module accepts the conversation
    counter_proposal: Optional[Dict[str, Any]] = None  # Alternative proposal
    reason: Optional[str] = None  # Reason for rejection
    next_phase: Optional[ConversationPhase] = None
    content: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ConversationCapable(Protocol):
    """Protocol for modules that support conversations."""
    
    @abstractmethod
    async def handle_handshake(self, handshake: ConversationHandshake) -> ConversationResponse:
        """Handle initial conversation handshake."""
        ...
    
    @abstractmethod
    async def negotiate_schema(self, 
                               proposed: Dict[str, Any], 
                               conversation_id: str) -> ConversationResponse:
        """Negotiate message schema for the conversation."""
        ...
    
    @abstractmethod
    async def process_conversation_turn(self, 
                                        message: ConversationMessage) -> Dict[str, Any]:
        """Process a turn in the conversation."""
        ...
    
    @abstractmethod
    def get_conversation_capabilities(self) -> List[str]:
        """Get conversation-specific capabilities."""
        ...


class ConversationProtocol:
    """
    Manages the protocol for module-to-module conversations.
    
    This class defines the standard flow for conversations:
    1. Handshake - Modules agree to converse
    2. Schema Negotiation - Agree on message format
    3. Execution - Exchange messages
    4. Termination - Clean close
    """
    
    @staticmethod
    def create_handshake_message(
        source: str,
        target: str,
        intent: ConversationIntent,
        requirements: Dict[str, Any]
    ) -> ConversationMessage:
        """Create initial handshake message."""
        handshake = ConversationHandshake(
            intent=intent,
            proposed_schema=requirements.get("schema", {}),
            capabilities_required=requirements.get("capabilities", []),
            capabilities_offered=requirements.get("offers", []),
            timeout_seconds=requirements.get("timeout", 300),
            metadata=requirements.get("metadata", {})
        )
        
        # Convert handshake to dict with proper enum serialization
        handshake_dict = handshake.__dict__.copy()
        handshake_dict["intent"] = handshake.intent.value
        
        return ConversationMessage.create(
            source=source,
            target=target,
            msg_type="conversation_handshake",
            content={
                "handshake": handshake_dict,
                "phase": ConversationPhase.HANDSHAKE.value
            }
        )
    
    @staticmethod
    def create_negotiation_message(
        source: str,
        target: str,
        conversation_id: str,
        turn_number: int,
        proposal: Dict[str, Any]
    ) -> ConversationMessage:
        """Create schema negotiation message."""
        return ConversationMessage.create(
            source=source,
            target=target,
            msg_type="schema_negotiation",
            content={
                "proposal": proposal,
                "phase": ConversationPhase.NEGOTIATION.value
            },
            conversation_id=conversation_id,
            turn_number=turn_number
        )
    
    @staticmethod
    def create_execution_message(
        source: str,
        target: str,
        conversation_id: str,
        turn_number: int,
        content: Dict[str, Any],
        in_reply_to: Optional[str] = None
    ) -> ConversationMessage:
        """Create execution phase message."""
        return ConversationMessage.create(
            source=source,
            target=target,
            msg_type="execution",
            content={
                "data": content,
                "phase": ConversationPhase.EXECUTION.value
            },
            conversation_id=conversation_id,
            turn_number=turn_number,
            in_reply_to=in_reply_to
        )
    
    @staticmethod
    def create_termination_message(
        source: str,
        target: str,
        conversation_id: str,
        turn_number: int,
        reason: str = "completed",
        summary: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """Create conversation termination message."""
        return ConversationMessage.create(
            source=source,
            target=target,
            msg_type="termination",
            content={
                "reason": reason,
                "summary": summary or {},
                "phase": ConversationPhase.TERMINATION.value
            },
            conversation_id=conversation_id,
            turn_number=turn_number
        )
    
    @staticmethod
    def validate_conversation_flow(messages: List[ConversationMessage]) -> bool:
        """Validate that a conversation follows proper protocol."""
        if not messages:
            return False
        
        # First message should be handshake
        if messages[0].type != "conversation_handshake":
            return False
        
        # Check for proper phase transitions
        phases_seen = []
        for msg in messages:
            if "phase" in msg.content:
                phase = msg.content["phase"]
                if phase not in phases_seen:
                    phases_seen.append(phase)
        
        # Validate phase order
        expected_order = [
            ConversationPhase.HANDSHAKE.value,
            ConversationPhase.NEGOTIATION.value,  # Optional
            ConversationPhase.EXECUTION.value,
            ConversationPhase.TERMINATION.value  # Optional
        ]
        
        # Check phases appear in correct order
        last_idx = -1
        for phase in phases_seen:
            if phase in expected_order:
                idx = expected_order.index(phase)
                if idx <= last_idx and phase != ConversationPhase.EXECUTION.value:
                    return False  # Out of order (execution can repeat)
                last_idx = max(last_idx, idx)
        
        return True


# Example usage for schema negotiation
class SchemaProposal:
    """Helper for schema negotiation."""
    
    @staticmethod
    def create_data_schema(
        fields: Dict[str, str],
        required: List[str],
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a data schema proposal."""
        return {
            "type": "object",
            "properties": {
                name: {"type": type_str} for name, type_str in fields.items()
            },
            "required": required,
            "additionalProperties": False,
            "constraints": constraints or {}
        }
    
    @staticmethod
    def merge_schemas(
        schema1: Dict[str, Any],
        schema2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two schemas, finding common ground."""
        merged = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Find common properties
        props1 = schema1.get("properties", {})
        props2 = schema2.get("properties", {})
        
        for prop in props1:
            if prop in props2:
                # Use more specific type if they differ
                merged["properties"][prop] = props1[prop]
        
        # Required fields must be in both
        req1 = set(schema1.get("required", []))
        req2 = set(schema2.get("required", []))
        merged["required"] = list(req1.intersection(req2))
        
        return merged