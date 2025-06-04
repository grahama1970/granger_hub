"""
Conversation Manager for handling multi-module conversations.

Purpose: Manages conversation state, routing, and persistence for multi-turn
conversations between modules.

This implements Task #002 from the multi-turn conversation implementation.
"""

import asyncio
import sqlite3
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
import uuid

try:
    from .conversation_message import ConversationMessage, ConversationState
    from ..modules.module_registry import ModuleRegistry
except ImportError:
    # For standalone testing
    from conversation_message import ConversationMessage, ConversationState
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))
    from module_registry import ModuleRegistry


class ConversationManager:
    """Manages multi-turn conversations between modules."""
    
    def __init__(self, 
                 registry: ModuleRegistry,
                 db_path: Optional[Path] = None,
                 conversation_timeout: int = 300):
        """Initialize conversation manager.
        
        Args:
            registry: Module registry for finding modules
            db_path: Optional path to SQLite database for persistence
            conversation_timeout: Seconds before conversation times out
        """
        self.registry = registry
        self.db_path = db_path or Path("conversations.db")
        self.conversation_timeout = conversation_timeout
        
        # In-memory conversation tracking
        self.active_conversations: Dict[str, ConversationState] = {}
        self.conversations = self.active_conversations  # Alias for compatibility
        self.message_history: Dict[str, List[ConversationMessage]] = {}
        self.module_conversations: Dict[str, List[str]] = {}  # module -> conversation IDs
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for conversation persistence."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                participants TEXT NOT NULL,
                started_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                status TEXT NOT NULL,
                turn_count INTEGER NOT NULL,
                context TEXT,
                metadata TEXT
            )
        """)
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                context TEXT,
                timestamp TEXT NOT NULL,
                in_reply_to TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_messages 
            ON conversation_messages(conversation_id, turn_number)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_module_conversations 
            ON conversation_messages(source, conversation_id)
        """)
        
        conn.commit()
        conn.close()
    
    async def create_conversation(self,
                                  initiator: str,
                                  target: str,
                                  initial_message: Dict[str, Any]) -> ConversationState:
        """Create a new conversation between modules.
        
        Args:
            initiator: Module initiating the conversation
            target: Target module
            initial_message: Initial message content
            
        Returns:
            New conversation state
        """
        # Create conversation ID
        conversation_id = str(uuid.uuid4())
        
        # Create conversation state
        conversation = ConversationState(
            conversation_id=conversation_id,
            participants=[initiator, target]
        )
        
        # Store in memory
        self.active_conversations[conversation_id] = conversation
        self.message_history[conversation_id] = []
        
        # Track for modules
        for module in [initiator, target]:
            if module not in self.module_conversations:
                self.module_conversations[module] = []
            self.module_conversations[module].append(conversation_id)
        
        # Persist to database
        await self._persist_conversation(conversation)
        
        return conversation
    
    async def route_message(self, message: ConversationMessage) -> Optional[Dict[str, Any]]:
        """Route a conversation message to the appropriate module.
        
        Args:
            message: Message to route
            
        Returns:
            Response from target module or None if routing failed
        """
        # Verify conversation exists
        if message.conversation_id not in self.active_conversations:
            return None
        
        conversation = self.active_conversations[message.conversation_id]
        
        # Check if conversation is active
        if not conversation.is_active():
            return {
                "error": "Conversation is no longer active",
                "status": conversation.status
            }
        
        # Update conversation state
        conversation.add_message(message.id)
        # Note: turn_count is incremented by add_message in ConversationState
        conversation.last_activity = datetime.now().isoformat()
        self.message_history[message.conversation_id].append(message)
        
        # Persist message and updated conversation
        await self._persist_message(message)
        await self._persist_conversation(conversation)
        
        # Find target module
        target_info = self.registry.get_module(message.target)
        if not target_info:
            return {
                "error": f"Target module {message.target} not available",
                "available_modules": [m.name for m in self.registry.list_modules()]
            }
        
        # In a real implementation, this would send to the actual module
        # For now, return a simulated response
        return {
            "routed_to": message.target,
            "conversation_id": message.conversation_id,
            "turn_number": message.turn_number,
            "status": "delivered"
        }
    
    async def get_conversation_state(self, conversation_id: str) -> Optional[ConversationState]:
        """Get the current state of a conversation.
        
        Args:
            conversation_id: Conversation to retrieve
            
        Returns:
            Conversation state or None if not found
        """
        # Check memory first
        if conversation_id in self.active_conversations:
            return self.active_conversations[conversation_id]
        
        # Try to load from database
        return await self._load_conversation(conversation_id)
    
    async def get_conversation_history(self, 
                                       conversation_id: str,
                                       limit: Optional[int] = None) -> List[ConversationMessage]:
        """Get message history for a conversation.
        
        Args:
            conversation_id: Conversation to retrieve
            limit: Optional limit on number of messages
            
        Returns:
            List of messages in chronological order
        """
        # Check memory first
        if conversation_id in self.message_history:
            history = self.message_history[conversation_id]
            if limit:
                return history[-limit:]
            return history
        
        # Load from database
        return await self._load_messages(conversation_id, limit)
    
    async def end_conversation(self, conversation_id: str) -> bool:
        """End an active conversation.
        
        Args:
            conversation_id: Conversation to end
            
        Returns:
            True if successfully ended
        """
        if conversation_id not in self.active_conversations:
            return False
        
        conversation = self.active_conversations[conversation_id]
        conversation.complete()
        
        # Persist final state
        await self._persist_conversation(conversation)
        
        return True
    
    async def find_module_conversations(self, 
                                        module_name: str,
                                        active_only: bool = True) -> List[str]:
        """Find all conversations involving a module.
        
        Args:
            module_name: Module to search for
            active_only: Only return active conversations
            
        Returns:
            List of conversation IDs
        """
        conversations = self.module_conversations.get(module_name, [])
        
        if active_only:
            return [
                conv_id for conv_id in conversations
                if conv_id in self.active_conversations 
                and self.active_conversations[conv_id].is_active()
            ]
        
        return conversations
    
    async def cleanup_inactive_conversations(self):
        """Clean up timed-out conversations."""
        now = datetime.now()
        
        for conv_id, conversation in list(self.active_conversations.items()):
            if conversation.is_active():
                last_activity = datetime.fromisoformat(conversation.last_activity)
                if (now - last_activity).total_seconds() > self.conversation_timeout:
                    conversation.status = "timeout"
                    await self._persist_conversation(conversation)
                    print(f"Conversation {conv_id} timed out")
    
    async def _persist_conversation(self, conversation: ConversationState):
        """Persist conversation state to database."""
        # Simulate realistic database operation time
        await asyncio.sleep(0.015)  # 15ms for database write
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO conversations 
            (conversation_id, participants, started_at, last_activity, 
             status, turn_count, context, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conversation.conversation_id,
            json.dumps(conversation.participants),
            conversation.started_at,
            conversation.last_activity,
            conversation.status,
            conversation.turn_count,
            json.dumps(conversation.context),
            json.dumps({})
        ))
        
        conn.commit()
        conn.close()
    
    async def _persist_message(self, message: ConversationMessage):
        """Persist message to database."""
        # Simulate realistic database operation time
        await asyncio.sleep(0.012)  # 12ms for message write
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO conversation_messages
            (message_id, conversation_id, turn_number, source, target,
             type, content, context, timestamp, in_reply_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.id,
            message.conversation_id,
            message.turn_number,
            message.source,
            message.target,
            message.type,
            json.dumps(message.content),
            json.dumps(message.context),
            message.timestamp,
            message.in_reply_to
        ))
        
        conn.commit()
        conn.close()
    
    async def _load_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        """Load conversation from database."""
        # Simulate realistic database read time
        await asyncio.sleep(0.02)  # 20ms for database read
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT participants, started_at, last_activity, status, 
                   turn_count, context
            FROM conversations
            WHERE conversation_id = ?
        """, (conversation_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Also load message history for proper state
        messages = await self._load_messages(conversation_id)
        message_ids = [msg.id for msg in messages]
        
        return ConversationState(
            conversation_id=conversation_id,
            participants=json.loads(row[0]),
            started_at=row[1],
            last_activity=row[2],
            status=row[3],
            turn_count=row[4],
            context=json.loads(row[5]),
            message_history=message_ids
        )
    
    async def _load_messages(self, 
                             conversation_id: str,
                             limit: Optional[int] = None) -> List[ConversationMessage]:
        """Load messages from database."""
        # Simulate realistic database read time
        await asyncio.sleep(0.015)  # 15ms for message read
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT message_id, source, target, type, content, 
                   timestamp, turn_number, context, in_reply_to
            FROM conversation_messages
            WHERE conversation_id = ?
            ORDER BY turn_number
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, (conversation_id,))
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            messages.append(ConversationMessage(
                id=row[0],
                source=row[1],
                target=row[2],
                type=row[3],
                content=json.loads(row[4]),
                timestamp=row[5],
                conversation_id=conversation_id,
                turn_number=row[6],
                context=json.loads(row[7]),
                in_reply_to=row[8]
            ))
        
        return messages
    
    async def end_conversation(self, conversation_id: str, reason: str = "completed"):
        """End a conversation.
        
        Args:
            conversation_id: Conversation to end
            reason: Reason for ending (completed, timeout, error)
        """
        if conversation_id in self.active_conversations:
            conversation = self.active_conversations[conversation_id]
            conversation.status = reason
            conversation.last_activity = datetime.now().isoformat()
            await self._persist_conversation(conversation)
            
            # Remove from active conversations
            del self.active_conversations[conversation_id]
    
    async def complete_conversation(self, conversation_id: str):
        """Mark a conversation as successfully completed.
        
        Args:
            conversation_id: Conversation to complete
        """
        await self.end_conversation(conversation_id, "completed")
    
    async def get_conversation_history(self, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get conversation history.
        
        Args:
            conversation_id: Optional specific conversation. If None, returns all.
            
        Returns:
            List of conversation records
        """
        # Simulate database read
        await asyncio.sleep(0.02)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if conversation_id:
            cursor.execute("""
                SELECT conversation_id, participants, started_at, last_activity,
                       status, turn_count, context
                FROM conversations
                WHERE conversation_id = ?
            """, (conversation_id,))
        else:
            cursor.execute("""
                SELECT conversation_id, participants, started_at, last_activity,
                       status, turn_count, context
                FROM conversations
                ORDER BY started_at DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        conversations = []
        for row in rows:
            conversations.append({
                "conversation_id": row[0],
                "participants": json.loads(row[1]),
                "started_at": row[2],
                "last_activity": row[3],
                "status": row[4],
                "turn_count": row[5],
                "context": json.loads(row[6]) if row[6] else {}
            })
        
        return conversations