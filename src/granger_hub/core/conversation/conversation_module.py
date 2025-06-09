"""
Enhanced BaseModule with conversation support.

Purpose: Extends BaseModule to support multi-turn conversations with context
preservation and conversation state management.

This implements Task #001 from the multi-turn conversation implementation.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import asyncio

from ..modules.base_module import BaseModule
from .conversation_message import ConversationMessage, ConversationState
from ..modules.module_registry import ModuleRegistry


class ConversationModule(BaseModule):
    """Base module with multi-turn conversation support."""
    
    def __init__(self, 
                 name: str,
                 system_prompt: str,
                 capabilities: List[str],
                 registry: Optional[ModuleRegistry] = None,
                 auto_register: bool = True,
                 conversation_timeout: int = 300):  # 5 minutes default
        """Initialize conversation-aware module.
        
        Args:
            name: Unique module name
            system_prompt: System prompt describing module's purpose'
            capabilities: List of module capabilities
            registry: Optional module registry for dynamic discovery
            auto_register: Whether to auto-register with the registry
            conversation_timeout: Seconds before conversation times out
        """
        super().__init__(name, system_prompt, capabilities, registry)
        
        # Conversation state management
        self.conversations: Dict[str, ConversationState] = {}
        self.conversation_history: Dict[str, List[ConversationMessage]] = {}
        self.is_running = False
        self.conversation_timeout = conversation_timeout
        
        # Add conversation capabilities
        if "conversation" not in self.capabilities:
            self.capabilities.append("conversation")
        
        # Register conversation handlers
        self._register_conversation_handlers()
    
    def _register_conversation_handlers(self):
        """Register conversation-specific message handlers."""
        self.register_handler("start_conversation", self._handle_start_conversation)
        self.register_handler("continue_conversation", self._handle_continue_conversation)
        self.register_handler("end_conversation", self._handle_end_conversation)
        self.register_handler("get_conversation_state", self._handle_get_conversation_state)
    
    async def _handle_start_conversation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle conversation initiation."""
        conv_msg = ConversationMessage.from_dict(data)
        
        # Create new conversation state
        conversation = ConversationState(
            conversation_id=conv_msg.conversation_id,
            participants=[conv_msg.source, self.name]
        )
        
        # Store conversation
        self.conversations[conv_msg.conversation_id] = conversation
        self.conversation_history[conv_msg.conversation_id] = [conv_msg]
        
        # Process initial message
        response_content = await self.process_conversation_turn(conv_msg)
        
        # Create response message
        response = conv_msg.create_reply(
            source=self.name,
            content=response_content,
            msg_type="conversation_response"
        )
        
        # Update conversation state
        conversation.add_message(conv_msg.id)
        conversation.add_message(response.id)
        self.conversation_history[conv_msg.conversation_id].append(response)
        
        return response.to_dict()
    
    async def _handle_continue_conversation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle continuing an existing conversation."""
        conv_msg = ConversationMessage.from_message(data)
        
        # Check if conversation exists
        if conv_msg.conversation_id not in self.conversations:
            return {
                "error": "Conversation not found",
                "conversation_id": conv_msg.conversation_id
            }
        
        conversation = self.conversations[conv_msg.conversation_id]
        
        # Check if conversation is active
        if not conversation.is_active():
            return {
                "error": "Conversation is no longer active",
                "conversation_id": conv_msg.conversation_id,
                "status": conversation.status
            }
        
        # Add to history
        self.conversation_history[conv_msg.conversation_id].append(conv_msg)
        conversation.add_message(conv_msg.id)
        
        # Process with conversation context
        response_content = await self.process_conversation_turn(conv_msg)
        
        # Create response
        response = conv_msg.create_reply(
            source=self.name,
            content=response_content
        )
        
        # Update state
        conversation.add_message(response.id)
        self.conversation_history[conv_msg.conversation_id].append(response)
        
        return response.to_dict()
    
    async def _handle_end_conversation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle conversation termination."""
        conversation_id = data.get("conversation_id") if isinstance(data, dict) else None
        
        if not conversation_id or conversation_id not in self.conversations:
            return {"error": "Conversation not found"}
        
        conversation = self.conversations[conversation_id]
        conversation.complete()
        
        return {
            "conversation_id": conversation_id,
            "status": "completed",
            "turn_count": conversation.turn_count,
            "duration": (datetime.fromisoformat(conversation.last_activity) - 
                        datetime.fromisoformat(conversation.started_at)).total_seconds()
        }
    
    async def _handle_get_conversation_state(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request for conversation state."""
        conversation_id = data.get("conversation_id") if isinstance(data, dict) else None
        
        if not conversation_id or conversation_id not in self.conversations:
            return {"error": "Conversation not found"}
        
        conversation = self.conversations[conversation_id]
        history = self.conversation_history.get(conversation_id, [])
        
        return {
            "state": conversation.to_dict(),
            "message_count": len(history),
            "last_turn": history[-1].turn_number if history else 0
        }
    
    async def process_conversation_turn(self, message: ConversationMessage) -> Dict[str, Any]:
        """Process a conversation turn with context awareness.
        
        This method should be overridden by subclasses to implement
        conversation-aware processing.
        
        Args:
            message: Conversation message with context
            
        Returns:
            Response content
        """
        # Get conversation history for context
        history = self.conversation_history.get(message.conversation_id, [])
        
        # Build context from history
        context = {
            "conversation_id": message.conversation_id,
            "turn_number": message.turn_number,
            "previous_messages": len(history),
            "conversation_context": message.context
        }
        
        # Call the regular process method with enhanced context
        return await self.process({
            "content": message.content,
            "context": context,
            "conversation_history": [
                {
                    "turn": msg.turn_number,
                    "source": msg.source,
                    "content": msg.content
                }
                for msg in history[-5:]  # Last 5 messages for context
            ]
        })
    
    async def handle_message(self, message: Union[Dict[str, Any], Any]) -> Any:
        """Enhanced message handler with conversation support."""
        # Check if this is a conversation message
        if isinstance(message, dict):
            if "conversation_id" in message and "turn_number" in message:
                # Convert to ConversationMessage
                conv_msg = ConversationMessage.from_message(message)
                
                # Route to appropriate conversation handler
                if conv_msg.turn_number == 1:
                    return await self._handle_start_conversation(conv_msg)
                else:
                    return await self._handle_continue_conversation(conv_msg)
        
        # Fall back to regular message handling
        return await super().handle_message(message)
    
    def get_conversation_history(self, conversation_id: str) -> List[ConversationMessage]:
        """Get the message history for a conversation."""
        return self.conversation_history.get(conversation_id, [])
    
    def get_active_conversations(self) -> List[str]:
        """Get list of active conversation IDs."""
        return [
            conv_id 
            for conv_id, conv in self.conversations.items() 
            if conv.is_active()
        ]
    
    async def cleanup_inactive_conversations(self):
        """Clean up timed-out conversations."""
        now = datetime.now()
        
        for conv_id, conversation in list(self.conversations.items()):
            if conversation.is_active():
                last_activity = datetime.fromisoformat(conversation.last_activity)
                if (now - last_activity).total_seconds() > self.conversation_timeout:
                    conversation.status = "timeout"
                    print(f"Conversation {conv_id} timed out")
    
    async def start(self):
        """Start the module with conversation cleanup task."""
        self.is_running = True
        
        # Start conversation cleanup task
        asyncio.create_task(self._conversation_cleanup_loop())
    
    async def _conversation_cleanup_loop(self):
        """Periodic cleanup of inactive conversations."""
        while self.is_running:
            await self.cleanup_inactive_conversations()
            await asyncio.sleep(60)  # Check every minute
    
    async def stop(self):
        """Stop the module."""
        self.is_running = False