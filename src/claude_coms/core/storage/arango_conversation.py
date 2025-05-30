"""
ArangoDB Conversation Storage for Module Communications.

Purpose: Stores and retrieves complete conversation histories between modules,
enabling context-aware communication and conversation analysis.

Third-party packages:
- python-arango: https://docs.python-arango.com/

Sample Input:
- Conversation: {"participants": ["ModuleA", "ModuleB"], "messages": [...]}
- Query: {"action": "get_context", "modules": ["ModuleA", "ModuleB"], "limit": 10}

Expected Output:
- Stored conversations with full context
- Conversation summaries and analytics
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
import json
import hashlib

from arango import ArangoClient
from arango.database import StandardDatabase

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation."""
    id: str
    conversation_id: str
    sender: str
    receiver: str
    action: str
    content: Dict[str, Any]
    timestamp: str
    sequence: int
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Conversation:
    """Represents a conversation between modules."""
    _key: str  # Unique conversation ID
    participants: List[str]
    topic: Optional[str]
    started_at: str
    last_message_at: str
    message_count: int = 0
    status: str = "active"  # active, completed, archived
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class ArangoConversationStore:
    """Stores and manages conversations in ArangoDB."""
    
    def __init__(self,
                 host: str = "localhost",
                 port: int = 8529,
                 username: str = "root",
                 password: str = "",
                 database: str = "claude_modules"):
        """Initialize conversation store.
        
        Args:
            host: ArangoDB host
            port: ArangoDB port
            username: Database username
            password: Database password
            database: Database name
        """
        self.client = ArangoClient(hosts=f"http://{host}:{port}")
        self.database_name = database
        self.username = username
        self.password = password
        self.db: Optional[StandardDatabase] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database collections and indexes."""
        if self._initialized:
            return
        
        try:
            # Connect to database
            self.db = self.client.db(self.database_name, username=self.username, password=self.password)
            
            # Create collections
            if not self.db.has_collection("conversations"):
                self.db.create_collection("conversations")
                logger.info("Created 'conversations' collection")
            
            if not self.db.has_collection("messages"):
                self.db.create_collection("messages")
                logger.info("Created 'messages' collection")
            
            if not self.db.has_collection("conversation_contexts"):
                self.db.create_collection("conversation_contexts")
                logger.info("Created 'conversation_contexts' collection")
            
            # Create indexes
            await self._create_indexes()
            
            self._initialized = True
            logger.info("Conversation store initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize conversation store: {e}")
            raise
    
    async def _create_indexes(self):
        """Create indexes for efficient querying."""
        # Messages indexes
        messages = self.db.collection("messages")
        messages.add_persistent_index(fields=["conversation_id"], unique=False)
        messages.add_persistent_index(fields=["sender"], unique=False)
        messages.add_persistent_index(fields=["receiver"], unique=False)
        messages.add_persistent_index(fields=["timestamp"], unique=False)
        messages.add_persistent_index(fields=["conversation_id", "sequence"], unique=True)
        
        # Conversations indexes
        conversations = self.db.collection("conversations")
        conversations.add_persistent_index(fields=["participants[*]"], unique=False)
        conversations.add_persistent_index(fields=["status"], unique=False)
        conversations.add_persistent_index(fields=["last_message_at"], unique=False)
        conversations.add_persistent_index(fields=["tags[*]"], unique=False)
    
    def _generate_conversation_id(self, participants: List[str]) -> str:
        """Generate unique conversation ID from participants.
        
        Args:
            participants: List of participant module names
            
        Returns:
            Unique conversation ID
        """
        # Sort participants for consistent ID
        sorted_participants = sorted(participants)
        participant_string = "|".join(sorted_participants)
        
        # Generate hash
        hash_obj = hashlib.md5(participant_string.encode())
        return f"conv_{hash_obj.hexdigest()[:16]}"
    
    async def start_conversation(self,
                               participants: List[str],
                               topic: Optional[str] = None,
                               context: Optional[Dict[str, Any]] = None) -> str:
        """Start a new conversation.
        
        Args:
            participants: List of participating modules
            topic: Optional conversation topic
            context: Optional initial context
            
        Returns:
            Conversation ID
        """
        conv_id = self._generate_conversation_id(participants)
        
        # Check if conversation exists
        try:
            existing = self.db.collection("conversations").get(conv_id)
            if existing and existing["status"] == "active":
                # Reuse existing active conversation
                return conv_id
        except:
            pass
        
        # Create new conversation
        conversation = Conversation(
            _key=conv_id,
            participants=participants,
            topic=topic,
            started_at=datetime.now().isoformat(),
            last_message_at=datetime.now().isoformat(),
            context=context or {}
        )
        
        self.db.collection("conversations").insert(conversation.to_dict())
        logger.info(f"Started conversation {conv_id} between {participants}")
        
        return conv_id
    
    async def add_message(self,
                         conversation_id: str,
                         sender: str,
                         receiver: str,
                         action: str,
                         content: Dict[str, Any],
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            sender: Sender module
            receiver: Receiver module
            action: Action performed
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Message ID
        """
        # Get current sequence number
        messages = self.db.collection("messages")
        cursor = messages.find(
            {"conversation_id": conversation_id},
            sort="sequence DESC",
            limit=1
        )
        
        last_message = None
        for msg in cursor:
            last_message = msg
            break
        
        sequence = (last_message["sequence"] + 1) if last_message else 1
        
        # Create message
        message_id = f"{conversation_id}_msg_{sequence}"
        message = ConversationMessage(
            id=message_id,
            conversation_id=conversation_id,
            sender=sender,
            receiver=receiver,
            action=action,
            content=content,
            timestamp=datetime.now().isoformat(),
            sequence=sequence,
            metadata=metadata
        )
        
        # Store message
        messages.insert(message.to_dict())
        
        # Update conversation
        conversations = self.db.collection("conversations")
        conversations.update_match(
            {"_key": conversation_id},
            {
                "last_message_at": message.timestamp,
                "message_count": sequence
            }
        )
        
        logger.debug(f"Added message {message_id} to conversation {conversation_id}")
        
        return message_id
    
    async def get_conversation_messages(self,
                                      conversation_id: str,
                                      limit: Optional[int] = None,
                                      offset: int = 0) -> List[Dict[str, Any]]:
        """Get messages from a conversation.
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages
            offset: Number of messages to skip
            
        Returns:
            List of messages
        """
        query = """
        FOR msg IN messages
            FILTER msg.conversation_id == @conv_id
            SORT msg.sequence ASC
            LIMIT @offset, @limit
            RETURN msg
        """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "conv_id": conversation_id,
                "offset": offset,
                "limit": limit or 1000
            }
        )
        
        return list(cursor)
    
    async def get_conversation_context(self,
                                     participants: List[str],
                                     limit: int = 10) -> Dict[str, Any]:
        """Get conversation context for participants.
        
        Args:
            participants: List of participant modules
            limit: Number of recent messages to include
            
        Returns:
            Conversation context
        """
        conv_id = self._generate_conversation_id(participants)
        
        # Get conversation
        try:
            conversation = self.db.collection("conversations").get(conv_id)
        except:
            return {"exists": False, "participants": participants}
        
        # Get recent messages
        messages = await self.get_conversation_messages(conv_id, limit=limit)
        
        # Build context
        context = {
            "exists": True,
            "conversation_id": conv_id,
            "participants": conversation["participants"],
            "topic": conversation.get("topic"),
            "started_at": conversation["started_at"],
            "last_message_at": conversation["last_message_at"],
            "message_count": conversation["message_count"],
            "recent_messages": messages,
            "stored_context": conversation.get("context", {})
        }
        
        # Add summary if available
        if conversation.get("summary"):
            context["summary"] = conversation["summary"]
        
        return context
    
    async def search_conversations(self,
                                 participant: Optional[str] = None,
                                 topic: Optional[str] = None,
                                 tags: Optional[List[str]] = None,
                                 status: Optional[str] = None,
                                 limit: int = 20) -> List[Dict[str, Any]]:
        """Search for conversations.
        
        Args:
            participant: Filter by participant
            topic: Filter by topic (partial match)
            tags: Filter by tags
            status: Filter by status
            limit: Maximum results
            
        Returns:
            List of matching conversations
        """
        filters = []
        bind_vars = {"limit": limit}
        
        if participant:
            filters.append("@participant IN conv.participants")
            bind_vars["participant"] = participant
        
        if topic:
            filters.append("CONTAINS(LOWER(conv.topic), LOWER(@topic))")
            bind_vars["topic"] = topic
        
        if tags:
            filters.append("LENGTH(INTERSECTION(conv.tags, @tags)) > 0")
            bind_vars["tags"] = tags
        
        if status:
            filters.append("conv.status == @status")
            bind_vars["status"] = status
        
        filter_clause = f"FILTER {' AND '.join(filters)}" if filters else ""
        
        query = f"""
        FOR conv IN conversations
            {filter_clause}
            SORT conv.last_message_at DESC
            LIMIT @limit
            RETURN conv
        """
        
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        return list(cursor)
    
    async def analyze_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Analyze a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation analysis
        """
        # Get all messages
        messages = await self.get_conversation_messages(conversation_id)
        
        if not messages:
            return {"error": "No messages found"}
        
        # Basic analysis
        analysis = {
            "conversation_id": conversation_id,
            "total_messages": len(messages),
            "participants": list(set(msg["sender"] for msg in messages) | 
                               set(msg["receiver"] for msg in messages)),
            "duration": {
                "start": messages[0]["timestamp"],
                "end": messages[-1]["timestamp"]
            },
            "actions": {},
            "message_flow": []
        }
        
        # Action frequency
        for msg in messages:
            action = msg["action"]
            analysis["actions"][action] = analysis["actions"].get(action, 0) + 1
        
        # Message flow pattern
        for i in range(min(len(messages), 10)):  # Last 10 messages
            analysis["message_flow"].append({
                "from": messages[i]["sender"],
                "to": messages[i]["receiver"],
                "action": messages[i]["action"]
            })
        
        # Calculate average response time
        response_times = []
        for i in range(1, len(messages)):
            if messages[i]["sender"] == messages[i-1]["receiver"]:
                # This is a response
                time1 = datetime.fromisoformat(messages[i-1]["timestamp"])
                time2 = datetime.fromisoformat(messages[i]["timestamp"])
                response_times.append((time2 - time1).total_seconds())
        
        if response_times:
            analysis["avg_response_time_seconds"] = sum(response_times) / len(response_times)
        
        return analysis
    
    async def summarize_conversation(self,
                                   conversation_id: str,
                                   summary: str,
                                   tags: Optional[List[str]] = None) -> bool:
        """Add summary and tags to a conversation.
        
        Args:
            conversation_id: Conversation ID
            summary: Conversation summary
            tags: Optional tags
            
        Returns:
            True if successful
        """
        update_data = {"summary": summary}
        if tags:
            update_data["tags"] = tags
        
        try:
            self.db.collection("conversations").update_match(
                {"_key": conversation_id},
                update_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to summarize conversation: {e}")
            return False
    
    async def archive_conversation(self, conversation_id: str) -> bool:
        """Archive a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if successful
        """
        try:
            self.db.collection("conversations").update_match(
                {"_key": conversation_id},
                {"status": "archived", "archived_at": datetime.now().isoformat()}
            )
            logger.info(f"Archived conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to archive conversation: {e}")
            return False
    
    async def get_module_conversation_stats(self, module_name: str) -> Dict[str, Any]:
        """Get conversation statistics for a module.
        
        Args:
            module_name: Module name
            
        Returns:
            Conversation statistics
        """
        query = """
        LET conversations = (
            FOR conv IN conversations
                FILTER @module IN conv.participants
                RETURN conv
        )
        
        LET messages_sent = (
            FOR msg IN messages
                FILTER msg.sender == @module
                RETURN msg
        )
        
        LET messages_received = (
            FOR msg IN messages
                FILTER msg.receiver == @module
                RETURN msg
        )
        
        RETURN {
            total_conversations: LENGTH(conversations),
            active_conversations: LENGTH(
                FOR c IN conversations
                    FILTER c.status == "active"
                    RETURN c
            ),
            messages_sent: LENGTH(messages_sent),
            messages_received: LENGTH(messages_received),
            unique_partners: LENGTH(
                UNIQUE(
                    FLATTEN(
                        FOR c IN conversations
                            RETURN REMOVE_VALUE(c.participants, @module)
                    )
                )
            )
        }
        """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={"module": module_name}
        )
        
        return next(cursor)
    
    async def cleanup_old_conversations(self, days: int = 30) -> int:
        """Archive old conversations.
        
        Args:
            days: Archive conversations older than this many days
            
        Returns:
            Number of archived conversations
        """
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        query = """
        FOR conv IN conversations
            FILTER conv.status == "active"
            FILTER conv.last_message_at < @cutoff
            UPDATE conv WITH {status: "archived", archived_at: @now} IN conversations
            RETURN conv._key
        """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "cutoff": cutoff_str,
                "now": datetime.now().isoformat()
            }
        )
        
        archived = list(cursor)
        logger.info(f"Archived {len(archived)} old conversations")
        return len(archived)
    
    async def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()


if __name__ == "__main__":
    # Test conversation storage with real data
    async def test_conversation_store():
        store = ArangoConversationStore()
        await store.initialize()
        
        # Start conversation
        conv_id = await store.start_conversation(
            participants=["data_producer", "data_processor"],
            topic="Data processing pipeline",
            context={"pipeline_type": "streaming"}
        )
        print(f"Started conversation: {conv_id}")
        
        # Add messages
        await store.add_message(
            conv_id,
            sender="data_producer",
            receiver="data_processor",
            action="send_data",
            content={"data_batch": [1, 2, 3, 4, 5], "batch_id": "001"}
        )
        
        await store.add_message(
            conv_id,
            sender="data_processor",
            receiver="data_producer",
            action="acknowledge",
            content={"status": "received", "batch_id": "001"}
        )
        
        # Get context
        context = await store.get_conversation_context(
            ["data_producer", "data_processor"],
            limit=5
        )
        print(f"Conversation context: {json.dumps(context, indent=2)}")
        
        # Analyze conversation
        analysis = await store.analyze_conversation(conv_id)
        print(f"Conversation analysis: {json.dumps(analysis, indent=2)}")
        
        # Get stats
        stats = await store.get_module_conversation_stats("data_producer")
        print(f"Module stats: {json.dumps(stats, indent=2)}")
        
        await store.close()
    
    asyncio.run(test_conversation_store())