"""
Enhanced Module Communicator with Graph Database and External Knowledge Integration.
Combines SQLite for local caching with ArangoDB for relationship tracking.
"""

from typing import Dict, List, Any, Optional
import json
from datetime import datetime
import asyncio
import litellm
from pathlib import Path

from . import ModuleCommunicator
from .graph_backend import GraphBackend


class GraphModuleCommunicator(ModuleCommunicator):
    """Enhanced communicator with graph database and external knowledge."""
    
    def __init__(self, module_name: str, 
                 arango_config: Optional[Dict[str, Any]] = None,
                 db_path: str = "~/.sparta/module_comm.db",
                 capabilities: Optional[List[str]] = None,
                 description: str = ""):
        """Initialize with both SQLite and ArangoDB backends."""
        # Initialize base SQLite communicator
        super().__init__(module_name, db_path)
        
        # Initialize graph backend if config provided
        self.graph_backend = None
        if arango_config:
            self.graph_backend = GraphBackend(arango_config)
            # Register this module
            self.graph_backend.register_module(
                module_name, 
                capabilities or [],
                description
            )
            
        # Perplexity API key (if available)
        self.perplexity_api_key = None
        
    def set_perplexity_key(self, api_key: str):
        """Set Perplexity API key for external knowledge queries."""
        self.perplexity_api_key = api_key
        litellm.api_key = api_key
        
    def send_message(self, source: str, target: str, data: Dict[str, Any]) -> str:
        """Send message with both SQLite and graph storage."""
        # Store in SQLite
        msg_id = super().send_message(source, target, data)
        
        # Also store in graph if available
        if self.graph_backend:
            graph_id, graph_key = self.graph_backend.store_message(data, source, target)
            # Add graph ID to the message data for reference
            data["_graph_id"] = graph_id
            
        return msg_id
        
    def find_modules_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Find modules with specific capabilities."""
        if not self.graph_backend:
            return []
            
        return self.graph_backend.find_modules_by_capability(capability)
        
    def find_compatible_modules(self, direction: str = "downstream") -> List[Dict[str, Any]]:
        """Find modules compatible with this module."""
        if not self.graph_backend:
            return []
            
        return self.graph_backend.find_compatible_modules(self.module_name, direction)
        
    def get_conversation_with(self, other_module: str) -> List[Dict[str, Any]]:
        """Get all messages exchanged with another module."""
        if not self.graph_backend:
            # Fall back to SQLite
            messages = []
            for msg in self.get_messages(self.module_name):
                if msg["source"] == other_module:
                    messages.append(msg)
            for msg in self.get_messages(other_module):
                if msg["source"] == self.module_name:
                    messages.append(msg)
            return sorted(messages, key=lambda x: x["timestamp"])
            
        return self.graph_backend.get_module_conversation(self.module_name, other_module)
        
    def get_knowledge_graph(self, topic: str) -> Dict[str, Any]:
        """Get knowledge graph for a topic, enhanced with external knowledge."""
        knowledge = {"topic": topic, "local": {}, "external": {}}
        
        # Get local knowledge from graph
        if self.graph_backend:
            knowledge["local"] = self.graph_backend.get_knowledge_graph(topic)
            
        # Enhance with external knowledge if Perplexity is available
        if self.perplexity_api_key and self._should_query_external(topic, knowledge["local"]):
            knowledge["external"] = self._query_perplexity(topic, knowledge["local"])
            
        return knowledge
        
    def _should_query_external(self, topic: str, local_knowledge: Dict[str, Any]) -> bool:
        """Determine if we should query external sources."""
        # Query if we have few local resources or the topic seems important
        if local_knowledge.get("total_resources", 0) < 3:
            return True
            
        # Check if topic contains keywords that benefit from external search
        external_keywords = ["latest", "recent", "2024", "2025", "current", "state-of-the-art"]
        return any(keyword in topic.lower() for keyword in external_keywords)
        
    def _query_perplexity(self, topic: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Query Perplexity for external knowledge."""
        try:
            # Build context-aware query
            query = self._build_perplexity_query(topic, context)
            
            response = litellm.completion(
                model="perplexity/llama-3.1-sonar-large-32k-online",
                messages=[{
                    "role": "system",
                    "content": "You are helping modules collaborate on cybersecurity research. Provide relevant, current information."
                },
                {
                    "role": "user",
                    "content": query
                }]
            )
            
            return {
                "query": query,
                "response": response.choices[0].message.content,
                "timestamp": datetime.now().isoformat(),
                "model": "perplexity/llama-3.1-sonar-large-32k-online"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    def _build_perplexity_query(self, topic: str, context: Dict[str, Any]) -> str:
        """Build a context-aware query for Perplexity."""
        query_parts = [f"Current information about {topic}"]
        
        # Add context from local knowledge
        if context.get("total_resources", 0) > 0:
            query_parts.append(f"Related to these areas: {', '.join([r.get('title', '') for r in context.get('resources', [])[:3]])}")
            
        # Add module context
        if context.get("modules"):
            module_names = [m.get("name", "") for m in context.get("modules", [])]
            query_parts.append(f"Relevant for these systems: {', '.join(module_names)}")
            
        return ". ".join(query_parts)
        
    def create_collaborative_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """Create a collaborative task between modules."""
        if not self.graph_backend:
            return None
            
        return self.graph_backend.create_collaborative_task(task_data)
        
    async def send_async_with_discovery(self, target_capability: str, 
                                       message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Send message to all modules with a specific capability."""
        # Find capable modules
        capable_modules = self.find_modules_by_capability(target_capability)
        
        if not capable_modules:
            # Try to discover via Perplexity
            if self.perplexity_api_key:
                discovery_query = f"What tools or systems can {target_capability}?"
                external_suggestion = self._query_perplexity(discovery_query, {})
                return [{
                    "status": "no_modules_found",
                    "capability": target_capability,
                    "suggestion": external_suggestion
                }]
            else:
                return [{
                    "status": "no_modules_found",
                    "capability": target_capability
                }]
                
        # Send to all capable modules
        results = []
        for module in capable_modules:
            result = await self.send_async(module["name"], message)
            results.append({
                "module": module["name"],
                "result": result
            })
            
        return results
        
    def get_module_stats(self) -> Dict[str, Any]:
        """Get statistics about this module's activity."""
        stats = {
            "module": self.module_name,
            "messages_sent": 0,
            "messages_received": 0,
            "collaborations": 0,
            "connected_modules": set()
        }
        
        if self.graph_backend:
            # Query graph for stats
            query = """
            LET sent = (
                FOR m IN modules FILTER m._key == @module
                FOR msg IN OUTBOUND m sends
                RETURN msg
            )
            LET received = (
                FOR m IN modules FILTER m._key == @module
                FOR msg IN INBOUND m receives
                RETURN msg
            )
            LET collaborations = (
                FOR m IN modules FILTER m._key == @module
                FOR task IN OUTBOUND m collaborates_on
                RETURN task
            )
            
            RETURN {
                sent: LENGTH(sent),
                received: LENGTH(received),
                collaborations: LENGTH(collaborations)
            }
            """
            
            # Execute query (would need to add this method to GraphBackend)
            # For now, use approximation from SQLite
            pass
            
        # Fall back to SQLite stats
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Sent messages
        cursor.execute("SELECT COUNT(*) FROM messages WHERE source = ?", (self.module_name,))
        stats["messages_sent"] = cursor.fetchone()[0]
        
        # Received messages  
        cursor.execute("SELECT COUNT(*) FROM messages WHERE target = ?", (self.module_name,))
        stats["messages_received"] = cursor.fetchone()[0]
        
        # Connected modules
        cursor.execute("""
            SELECT DISTINCT source FROM messages WHERE target = ?
            UNION
            SELECT DISTINCT target FROM messages WHERE source = ?
        """, (self.module_name, self.module_name))
        
        stats["connected_modules"] = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return stats