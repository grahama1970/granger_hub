"""
Enhanced Message class with conversation support.

Purpose: Extends the basic Message class to support multi-turn conversations
with context preservation and conversation tracking.

This implements Task #003 from the multi-turn conversation implementation.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


@dataclass
class ConversationMessage:
    """Message format for multi-turn conversations."""
    id: str
    source: str
    target: str
    type: str
    content: Any
    timestamp: str
    conversation_id: str  # Links messages in same conversation
    turn_number: int  # Sequential turn counter
    context: Dict[str, Any] = field(default_factory=dict)  # Conversation state
    metadata: Optional[Dict[str, Any]] = None
    in_reply_to: Optional[str] = None  # ID of message being replied to
    
    @classmethod
    def create(cls, 
               source: str, 
               target: str, 
               msg_type: str, 
               content: Any,
               conversation_id: Optional[str] = None,
               turn_number: int = 1,
               context: Optional[Dict[str, Any]] = None,
               in_reply_to: Optional[str] = None) -> 'ConversationMessage':
        """Create a new conversation message with auto-generated fields."""
        return cls(
            id=str(uuid.uuid4()),
            source=source,
            target=target,
            type=msg_type,
            content=content,
            timestamp=datetime.now().isoformat(),
            conversation_id=conversation_id or str(uuid.uuid4()),
            turn_number=turn_number,
            context=context or {},
            metadata={},
            in_reply_to=in_reply_to
        )
    
    @classmethod
    def from_message(cls, message: Dict[str, Any]) -> 'ConversationMessage':
        """Create from a regular message dict, handling missing conversation fields."""
        # Ensure required conversation fields
        if 'conversation_id' not in message:
            message['conversation_id'] = str(uuid.uuid4())
        if 'turn_number' not in message:
            message['turn_number'] = 1
        if 'context' not in message:
            message['context'] = {}
        
        return cls(**message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "content": self.content,
            "timestamp": self.timestamp,
            "conversation_id": self.conversation_id,
            "turn_number": self.turn_number,
            "context": self.context,
            "metadata": self.metadata or {},
            "in_reply_to": self.in_reply_to
        }
    
    def create_reply(self, source: str, content: Any, msg_type: Optional[str] = None) -> 'ConversationMessage':
        """Create a reply message in the same conversation."""
        return ConversationMessage.create(
            source=source,
            target=self.source,  # Reply to sender
            msg_type=msg_type or self.type,
            content=content,
            conversation_id=self.conversation_id,
            turn_number=self.turn_number + 1,
            context=self.context.copy(),  # Preserve context
            in_reply_to=self.id
        )
    
    def update_context(self, updates: Dict[str, Any]) -> None:
        """Update conversation context with new information."""
        self.context.update(updates)


@dataclass 
class ConversationState:
    """Tracks the state of an ongoing conversation."""
    conversation_id: str
    participants: List[str]
    turn_count: int = 0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    message_history: List[str] = field(default_factory=list)  # Message IDs
    status: str = "active"  # active, paused, completed
    
    def add_message(self, message_id: str) -> None:
        """Add a message to the conversation history."""
        self.message_history.append(message_id)
        self.turn_count += 1
        self.last_activity = datetime.now().isoformat()
    
    def complete(self) -> None:
        """Mark conversation as completed."""
        self.status = "completed"
        self.last_activity = datetime.now().isoformat()
    
    def is_active(self) -> bool:
        """Check if conversation is still active."""
        return self.status == "active"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "conversation_id": self.conversation_id,
            "participants": self.participants,
            "turn_count": self.turn_count,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "context": self.context,
            "message_history": self.message_history,
            "status": self.status
        }